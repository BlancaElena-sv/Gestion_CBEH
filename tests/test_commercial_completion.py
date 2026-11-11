"""Cierre comercial: contratos Firebase, permisos y procesos con datos ficticios."""
from copy import deepcopy
from datetime import datetime
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from config import CICLO_LECTIVO, TZ_SV
from auth import generar_hash, verificar_password
from authorization import AccessDenied, authorize
from finance_service import record_movement
from integrity_service import IntegrityError
from profile_service import save_profile, photo_url_allowed
from test_integrity_transactions import MemoryDB, simulated_transactional, session
from views.configuracion_dashboard import _write_dashboard


class CommercialTests(unittest.TestCase):
    def setUp(self):
        self.db = MemoryDB()
        self.db.data.update(finanzas={}, configuracion={}, agenda={}, maestros_perfil={
            't1': dict(nombre='Docente', activo=True), 't2': dict(nombre='Otro', activo=True)},
            carga_academica={'c1': dict(id_docente='t1', grado='Primer Grado', materias=['Comunicación'], ciclo_lectivo=CICLO_LECTIVO)})
        self.db.data['usuarios']['teacher']['password_hash'] = generar_hash('actual-123')
        self.teacher = session('teacher', 'docente')
        self.now = datetime.now(TZ_SV)
        self.photo = 'https://firebasestorage.googleapis.com/v0/b/edumanager-demo.firebasestorage.app/o/perfiles%2Fteacher%2Ffoto.png?alt=media'
        for name, kwargs in [
            ('integrity_service.firestore.transactional', dict(side_effect=simulated_transactional)),
            ('socket.socket.connect', dict(side_effect=AssertionError('Red prohibida'))),
        ]:
            p = patch(name, **kwargs);p.start();self.addCleanup(p.stop)

    def income(self, **extra):
        data = dict(tipo='ingreso', descripcion='Mensualidad - Febrero', monto=25.5,
                    alumno_nie='1', nombre_persona='Ficticio', ciclo_lectivo=CICLO_LECTIVO,
                    fecha_legible=self.now.strftime('%d/%m/%Y %H:%M'), fecha=self.now, id_short='123456')
        data.update(extra)
        return record_movement(self.db, data, session=session())

    def expense(self, **extra):
        data = dict(tipo='egreso', descripcion='Salario - Febrero', monto=200., docente_id='t1',
                    nombre_persona='Docente', ciclo_lectivo=CICLO_LECTIVO, fecha=self.now,
                    fecha_legible=self.now.strftime('%d/%m/%Y %H:%M'))
        data.update(extra)
        return record_movement(self.db, data, session=session())

    def test_income_single_write_amount_cycle_and_grade_snapshot(self):
        values = self.income(ciclo_lectivo=CICLO_LECTIVO-1)
        self.assertEqual(values['monto'], 25.5)
        self.assertEqual(values['ciclo_lectivo'], CICLO_LECTIVO-1)
        self.assertEqual(values['grado_alumno'], 'Primer Grado')
        self.assertEqual(len(self.db.data['finanzas']), 1)

    def test_duplicate_income_same_person_concept_day_blocked(self):
        self.income()
        with self.assertRaises(IntegrityError):self.income(ciclo_lectivo=CICLO_LECTIVO+1)
        self.assertEqual(len(self.db.data['finanzas']), 1)

    def test_concurrent_duplicate_income_has_one_commit(self):
        self.db.hook = lambda: self.db.external_update('_integrity','finanzas', {'revision': 1})
        self.db.data['_integrity'] = {'finanzas': {'revision': 0}}
        self.income()
        self.assertEqual(self.db.retries, 1)
        self.assertEqual(len(self.db.data['finanzas']), 1)

    def test_salary_duplicates_and_other_expenses_rule(self):
        self.expense()
        with self.assertRaises(IntegrityError): self.expense(descripcion='Salario - Otro detalle')
        for _ in range(2):
            self.expense(descripcion='Servicios - Energía', docente_id=None)
        self.assertEqual(len(self.db.data['finanzas']), 3)
        self.assertEqual(sum(x['monto'] for x in self.db.data['finanzas'].values()), 600.)

    def test_money_validation_and_inactive_student(self):
        for amount in [0, -1, float('inf'), float('nan')]:
            with self.assertRaises(IntegrityError): self.income(monto=amount)
        self.db.data['alumnos']['s']['estado']='Baja'
        with self.assertRaises(IntegrityError): self.income()
        self.assertFalse(self.db.writes)

    def test_teacher_cannot_write_finances(self):
        with self.assertRaises(AccessDenied):
            record_movement(self.db, dict(tipo='ingreso', monto=1, descripcion='Detalle'), session=self.teacher)
        self.assertFalse(self.db.writes)

    def test_financial_failure_has_no_partial_write(self):
        before=deepcopy(self.db.data);self.db.fail=True
        with self.assertRaises(RuntimeError):self.income()
        self.assertEqual(self.db.data,before)

    def test_profile_cannot_edit_roles_or_other_accounts(self):
        with self.assertRaises(IntegrityError):
            save_profile(self.db,'personal',dict(nombre='Docente',rol='admin'),session=self.teacher)
        save_profile(self.db,'personal',dict(nombre='Nombre nuevo',email='ficticio@example.invalid'),session=self.teacher)
        self.assertEqual(self.db.data['usuarios']['teacher']['rol'],'docente')
        self.assertEqual(self.db.data['usuarios']['a']['nombre'],'A')
        self.assertEqual(self.db.data['usuarios']['teacher']['id_docente'],'t1')
        self.assertEqual(authorize(self.db,'Cargar Notas',self.teacher).teacher_id,'t1')

    def test_profile_photo_updates_only_verified_teacher_atomically(self):
        self.assertTrue(photo_url_allowed(self.photo,'teacher'))
        save_profile(self.db,'personal',dict(nombre='Docente',foto_url=self.photo),session=self.teacher)
        self.assertEqual(self.db.data['maestros_perfil']['t1']['foto_url'],self.photo)
        self.assertNotIn('foto_url',self.db.data['maestros_perfil']['t2'])
        before=deepcopy(self.db.data);self.db.fail=True
        with self.assertRaises(RuntimeError):
            save_profile(self.db,'personal',dict(nombre='Otro nombre'),session=self.teacher)
        self.assertEqual(self.db.data,before)

    def test_foreign_photo_and_ambiguous_teacher_blocked(self):
        for url in ['https://example.invalid/foto.png', self.photo.replace('teacher','other')]:
            self.assertFalse(photo_url_allowed(url,'teacher'))
            with self.assertRaises(IntegrityError):
                save_profile(self.db,'personal',dict(nombre='Docente',foto_url=url),session=self.teacher)
        self.db.data['maestros_perfil']['t2']['nombre']='Docente'
        with self.assertRaises(AccessDenied):
            save_profile(self.db,'personal',dict(nombre='Docente'),session=self.teacher)

    def test_password_requires_current_bcrypt_and_preserves_fields(self):
        before=deepcopy(self.db.data)
        with self.assertRaises(IntegrityError):
            save_profile(self.db,'password',current_password='incorrecta',new_password='nueva-123',session=self.teacher)
        self.assertEqual(self.db.data,before)
        save_profile(self.db,'password',current_password='actual-123',new_password='nueva-123',session=self.teacher)
        self.assertTrue(verificar_password('nueva-123',self.db.data['usuarios']['teacher']['password_hash']))
        self.assertFalse(verificar_password('actual-123',self.db.data['usuarios']['teacher']['password_hash']))

    def test_preferences_and_revoked_profile(self):
        save_profile(self.db,'preferences',dict(tema='oscuro',notificaciones_email=False),session=self.teacher)
        self.assertEqual(self.db.data['usuarios']['teacher']['tema'],'oscuro')
        self.db.hook=lambda:self.db.external_update('usuarios','teacher',{'activo':False})
        with self.assertRaises(AccessDenied):
            save_profile(self.db,'personal',dict(nombre='Docente'),session=self.teacher)

    def test_missing_session_and_remote_project_denied(self):
        with self.assertRaises(AccessDenied):
            save_profile(self.db,'personal',dict(nombre='Ficticio'),session={})
        self.db.project='production'
        with self.assertRaises(AccessDenied):self.income()

    def test_dashboard_config_agenda_toggle_and_delete(self):
        with patch('integrity_service.st.session_state',session()):
            _write_dashboard(self.db,'config',data={'titulo_admin':'Demostración','aviso_activo':True})
            _write_dashboard(self.db,'add','evento',{'titulo':'Reunión ficticia','activo':True,'audiencia':'Todos'})
            _write_dashboard(self.db,'toggle','evento')
            self.assertFalse(self.db.data['agenda']['evento']['activo'])
            _write_dashboard(self.db,'delete','evento')
        self.assertNotIn('evento',self.db.data['agenda'])
        self.assertEqual(self.db.data['configuracion']['dashboard']['titulo_admin'],'Demostración')

    def test_dashboard_denies_teacher_and_failure_has_no_effect(self):
        with patch('integrity_service.st.session_state',self.teacher):
            with self.assertRaises(AccessDenied):_write_dashboard(self.db,'config',data={})
        with patch('integrity_service.st.session_state',session()):
            self.db.fail=True
            with self.assertRaises(RuntimeError):_write_dashboard(self.db,'add','evento',{'titulo':'Prueba'})
        self.assertFalse(self.db.data['agenda'])

    def test_lost_confirmation_retries_same_expense_without_duplicate(self):
        from views.finanzas import _record_form_movement
        data = dict(tipo='egreso', descripcion='Servicios - Energía', monto=30.,
                    nombre_persona='Proveedor ficticio', fecha=self.now,
                    fecha_legible=self.now.strftime('%d/%m/%Y %H:%M'), ciclo_lectivo=CICLO_LECTIVO)
        state = session()
        with patch('views.finanzas.st.session_state', state):
            self.db.lost_ack = True
            with self.assertRaises(RuntimeError): _record_form_movement(self.db, data)
            self.assertIn('_financial_pending', state)
            self.assertEqual(len(self.db.data['finanzas']), 1)
            _record_form_movement(self.db, data)
            self.assertNotIn('_financial_pending', state)
            self.assertEqual(len(self.db.data['finanzas']), 1)
            # Una segunda acción confirmada sigue siendo un gasto ordinario legítimo.
            _record_form_movement(self.db, data)
            self.assertEqual(len(self.db.data['finanzas']), 2)

    def test_operation_id_cannot_overwrite_a_different_payment(self):
        data = dict(tipo='egreso', descripcion='Servicios - Prueba', monto=30.,
                    nombre_persona='Proveedor ficticio', fecha=self.now,
                    fecha_legible=self.now.strftime('%d/%m/%Y %H:%M'), ciclo_lectivo=CICLO_LECTIVO)
        key = 'a' * 32
        record_movement(self.db, data, session=session(), operation_id=key)
        with self.assertRaises(IntegrityError):
            record_movement(self.db, dict(data,monto=40.), session=session(), operation_id=key)
        self.assertEqual(len(self.db.data['finanzas']), 1)
        self.assertEqual(self.db.data['finanzas'][key]['monto'], 30.)


class CommercialViewTests(unittest.TestCase):
    def setUp(self):
        CommercialTests.setUp(self)
        p=patch('views.finanzas.firestore.SERVER_TIMESTAMP',self.now)
        p.start();self.addCleanup(p.stop)

    def app(self,module,teacher=False):
        from streamlit.testing.v1 import AppTest
        code='''
import streamlit as st
from datetime import datetime
from config import TZ_SV
from views.finanzas import mostrar_finanzas
from views.perfil import mostrar_perfil
from views.configuracion_dashboard import mostrar_configuracion_dashboard
now=datetime.now(TZ_SV)
if st.session_state['module']=='finance':
    mostrar_finanzas(st.session_state['db'], ['Primer Grado','Segundo Grado'], lambda:now.date(),lambda:now.strftime('%d/%m/%Y %H:%M'),lambda *a:False,lambda *a:False,lambda *a:'')
elif st.session_state['module']=='dashboard':
    mostrar_configuracion_dashboard(st.session_state['db'])
else:
    mostrar_perfil(st.session_state['db'],lambda *a:None,lambda:now.date())
'''
        app=AppTest.from_string(code)
        for k,v in dict(self.teacher if teacher else session(),db=self.db,module=module).items():app.session_state[k]=v
        return app.run(timeout=15)

    def test_financial_charge_receipt_report_and_duplicate_error(self):
        app=self.app('finance')
        next(e for e in app.text_input if e.label=='Ingrese NIE:').set_value('1')
        next(e for e in app.button if e.label=='Buscar por NIE').click().run()
        next(e for e in app.text_input if e.label=='Detalle (Ej: Mes de Marzo)').set_value('Febrero')
        next(e for e in app.number_input if e.label=='Monto ($)').set_value(25.5)
        next(e for e in app.button if e.label=='✅ Registrar Ingreso').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(self.db.data['finanzas']),1)
        html=' '.join(e.proto.srcdoc for e in app.get('iframe'))
        self.assertIn('COMPROBANTE DE INGRESO',html)
        self.assertIn('25.50',html)
        self.assertTrue(any(e.value=='$25.50' for e in app.metric))
        next(e for e in app.text_input if e.label=='Ingrese NIE:').set_value('1')
        next(e for e in app.button if e.label=='Buscar por NIE').click().run()
        next(e for e in app.text_input if e.label=='Detalle (Ej: Mes de Marzo)').set_value('Febrero')
        next(e for e in app.number_input if e.label=='Monto ($)').set_value(25.5)
        next(e for e in app.button if e.label=='✅ Registrar Ingreso').click().run()
        self.assertEqual(len(self.db.data['finanzas']),1)
        self.assertTrue(any('duplicada' in e.value for e in app.error))

    def test_expense_and_report_print_no_private_html(self):
        app=self.app('finance')
        next(e for e in app.text_input if e.label=='Detalle').set_value('Febrero <script>prueba()</script>')
        next(e for e in app.number_input if e.label=='Monto').set_value(50.)
        next(e for e in app.button if e.label=='Registrar').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(self.db.data['finanzas']),1)
        self.assertTrue(any('50.50' not in e.value and e.value=='$50.00' for e in app.metric))
        self.assertIn('COMPROBANTE', ' '.join(e.proto.srcdoc for e in app.get('iframe')))
        next(e for e in app.button if e.key=='fin_imprimir_reporte').click().run()
        self.assertFalse(app.exception)
        report=' '.join(e.proto.srcdoc for e in app.get('iframe'))
        self.assertIn('window.print()', report)
        self.assertIn('&lt;script&gt;', report)
        self.assertNotIn('<script>prueba()', report)

    def test_profile_personal_preferences_and_password_form(self):
        app=self.app('profile',teacher=True)
        self.assertFalse(app.exception)
        next(e for e in app.text_input if e.label=='Nombre completo').set_value('Docente Renombrado')
        next(e for e in app.button if e.label=='💾 Guardar cambios').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.db.data['usuarios']['teacher']['id_docente'],'t1')
        next(e for e in app.selectbox if e.label=='Tema').set_value('oscuro')
        next(e for e in app.button if e.label=='💾 Guardar preferencias').click().run()
        self.assertEqual(self.db.data['usuarios']['teacher']['tema'],'oscuro')
        for label,value in [('Contraseña actual','actual-123'),('Nueva contraseña','nueva-123'),('Confirmar nueva contraseña','nueva-123')]:
            next(e for e in app.text_input if e.label==label).set_value(value)
        next(e for e in app.button if 'Cambiar contraseña' in e.label).click().run()
        self.assertTrue(any('Contraseña cambiada' in e.value for e in app.success))
        self.assertTrue(verificar_password('nueva-123',self.db.data['usuarios']['teacher']['password_hash']))

    def test_dashboard_form_saves_notice_and_agenda(self):
        app=self.app('dashboard')
        next(e for e in app.text_input if e.label=='Título del aviso').set_value('Aviso ficticio')
        next(e for e in app.checkbox if e.label=='Mostrar aviso institucional').check()
        next(e for e in app.button if e.label=='💾 Guardar configuración').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.db.data['configuracion']['dashboard']['aviso_titulo'],'Aviso ficticio')
        next(e for e in app.text_input if e.label=='Actividad').set_value('Reunión ficticia')
        next(e for e in app.button if e.label=='➕ Agregar actividad').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(self.db.data['agenda']),1)
