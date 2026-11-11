"""Integración opcional. Ejecutar explícitamente, solo en el emulador localhost."""
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if os.environ.get('FIRESTORE_EMULATOR_HOST') != '127.0.0.1:8787':
    raise RuntimeError('Se requiere el emulador local explícito 127.0.0.1:8787; no hay fallback remoto.')

from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore import Client
from integrity_service import IntegrityError, mutate_user
from promotion_service import promote_student
from authorization import AccessDenied


def session(actor='integrity-a'):
    return dict(logged_in=True, user_id=actor, user_role='admin')


def values(actor, role='docente'):
    return dict(usuario=actor, nombre='Ficticio local', rol=role, password_hash='ficticio-no-credencial')


class EmulatorIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.db = Client(project='edumanager-demo', credentials=AnonymousCredentials())
        for actor in ['integrity-a', 'integrity-b']:
            self.db.collection('usuarios').document(actor).set(dict(rol='admin', activo=True, nombre='Prueba'))
        self.student = self.db.collection('alumnos').document('integrity-student')
        self.student.set(dict(estado='Activo', grado_actual='Primer Grado', ciclo_lectivo=2027,
                              historial_academico=[dict(ciclo=2025, nota='Conservar')]))

    def tearDown(self):
        self.db.close()

    def promote(self):
        return promote_student(self.db, self.student.id, 'Promover', 'Primer Grado',
                               2027, 2028, '01/01/2028', session())

    def test_last_admin_cannot_be_demoted(self):
        mutate_user(self.db, 'integrity-b', 'save', values('integrity-b'), session())
        with self.assertRaises(IntegrityError):
            mutate_user(self.db, 'integrity-a', 'save', values('integrity-a'), session())
        self.assertEqual(self.db.collection('usuarios').document('integrity-a').get().to_dict()['rol'], 'admin')

    def test_concurrent_demotions_keep_one_admin(self):
        def demote(actor):
            try:
                return mutate_user(self.db, actor, 'save', values(actor), session(actor))
            except (IntegrityError, AccessDenied):
                return False
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(demote, ['integrity-a', 'integrity-b']))
        self.assertEqual(sum(results), 1)
        active = list(self.db.collection('usuarios').where('rol', '==', 'admin').where('activo', '==', True).stream())
        self.assertEqual(len(active), 1)

    def test_promotion_preserves_history_and_rejects_duplicate(self):
        self.assertEqual(self.promote().status, 'promovido')
        self.assertEqual(self.promote().status, 'rechazado')
        data = self.student.get().to_dict()
        self.assertEqual(data['ciclo_lectivo'], 2028)
        self.assertEqual(len(data['historial_academico']), 2)
        self.assertEqual(data['historial_academico'][0]['ciclo'], 2025)

    def test_concurrent_promotion_has_one_success(self):
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.promote().status, range(2)))
        self.assertCountEqual(results, ['promovido', 'rechazado'])
        self.assertEqual(len(self.student.get().to_dict()['historial_academico']), 2)

    def test_user_create_and_repeated_save(self):
        # Reactivar de forma controlada el mismo documento ficticio entre pruebas.
        vals = values('integrity-new')
        self.assertIsInstance(mutate_user(self.db, 'integrity-new', 'save', vals, session()), bool)
        self.assertFalse(mutate_user(self.db, 'integrity-new', 'save', vals, session()))
        self.assertEqual(self.db.collection('usuarios').document('integrity-new').get().to_dict()['rol'], 'docente')

    def test_concurrent_history_append_is_preserved(self):
        from firebase_admin import firestore
        def append_history():
            @firestore.transactional
            def change(tx):
                data = self.student.get(transaction=tx).to_dict()
                history = data['historial_academico'] + [dict(ciclo=2026, nota='Concurrente')]
                tx.update(self.student, {'historial_academico': history})
            change(self.db.transaction())
        with ThreadPoolExecutor(2) as pool:
            promotion = pool.submit(self.promote)
            addition = pool.submit(append_history)
            self.assertEqual(promotion.result().status, 'promovido')
            addition.result()
        history = self.student.get().to_dict()['historial_academico']
        self.assertEqual(len(history), 3)
        self.assertEqual({row['ciclo'] for row in history}, {2025, 2026, 2027})

    def test_commercial_financial_concurrent_duplicate(self):
        from datetime import datetime
        from uuid import uuid4
        from config import TZ_SV
        from finance_service import record_movement
        self.student.update({'nie': 'integrity-1'})
        data = dict(tipo='ingreso', monto=25.5, alumno_nie='integrity-1',
                    descripcion='Cobro ficticio '+uuid4().hex, fecha=datetime.now(TZ_SV),
                    fecha_legible=datetime.now(TZ_SV).strftime('%d/%m/%Y %H:%M'), ciclo_lectivo=2027)
        def record():
            try:
                record_movement(self.db, data, session=session())
                return True
            except IntegrityError:
                return False
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(lambda _: record(), range(2))), 1)
        records=list(self.db.collection('finanzas').where('descripcion', '==', data['descripcion']).stream())
        self.assertEqual(len(records),1)
        self.assertEqual(records[0].to_dict()['grado_alumno'],'Primer Grado')
        record_movement(self.db, records[0].to_dict(), session=session(), operation_id=records[0].id)
        self.assertEqual(len(list(self.db.collection('finanzas').where('descripcion', '==', data['descripcion']).stream())), 1)

    def test_commercial_profile_personal_and_password(self):
        from auth import generar_hash, verificar_password
        from profile_service import save_profile
        actor='integrity-teacher'
        self.db.collection('usuarios').document(actor).set(dict(rol='docente', activo=True, nombre='Docente Ficticio', password_hash=generar_hash('Ficticia123!')))
        self.db.collection('maestros_perfil').document(actor).set(dict(nombre='Docente Ficticio', activo=True))
        teacher_session=dict(logged_in=True,user_id=actor,user_role='docente')
        save_profile(self.db,'personal',{'nombre':'Nombre nuevo'},session=teacher_session)
        save_profile(self.db,'password',current_password='Ficticia123!',new_password='NuevaFicticia123!',session=teacher_session)
        row=self.db.collection('usuarios').document(actor).get().to_dict()
        self.assertEqual(row['id_docente'],actor)
        self.assertTrue(verificar_password('NuevaFicticia123!',row['password_hash']))
        self.assertEqual(row['rol'],'docente')

    def test_commercial_dashboard_notice_and_agenda(self):
        from unittest.mock import patch
        from views.configuracion_dashboard import _write_dashboard
        with patch('integrity_service.st.session_state',session()):
            _write_dashboard(self.db,'config',data=dict(aviso_activo=True,aviso_titulo='Ficticio local'))
            _write_dashboard(self.db,'add','integrity-event',dict(titulo='Actividad ficticia',activo=True))
            _write_dashboard(self.db,'toggle','integrity-event')
            self.assertFalse(self.db.collection('agenda').document('integrity-event').get().to_dict()['activo'])
            _write_dashboard(self.db,'delete','integrity-event')
        self.assertFalse(self.db.collection('agenda').document('integrity-event').get().exists)


if __name__ == '__main__':
    unittest.main()
