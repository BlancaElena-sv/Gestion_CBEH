"""Regresiones académicas con Firestore simulado; nunca datos o archivos reales."""
from datetime import date, datetime
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from test_navigation_permissions import FakeDB, FakeQuery, FakeDocument
from config import CICLO_LECTIVO, TZ_SV


class AcademicDB(FakeDB):
    def __init__(self):
        super().__init__()
        self.data['alumnos']['1'].update(
            turno='Matutino', encargado=dict(nombre='Responsable Prueba',telefono='2200-0000',direccion='Dirección de prueba'),
            documentos=dict(foto_url=None,doc_urls=[]),historial_academico=[])
        for key,data in self.data['maestros_perfil'].items():
            data.update(codigo=key.upper(),telefono='2200-0000',email='prueba@example.invalid',direccion='Dirección de prueba')
        self.data['finanzas']={}
        self.data['notas']={}
        self.data['bitacora']={}
        self.data['asistencia']={}
        self.data['notas_mensuales']={}

    def collection(self,name):
        return AcademicQuery(self,name)


class AcademicQuery(FakeQuery):
    def where(self,field,op,value):
        return AcademicQuery(self.db,self.name,self.filters+((field,op,value),))

    def document(self,doc_id):
        return AcademicDocument(self.db,self.name,doc_id)

    def add(self,data):
        key=f'test-{len(self.db.data.get(self.name,{}))+1}'
        doc=self.document(key)
        doc.set(data)
        return None,doc


class AcademicDocument(FakeDocument):
    def update(self,data):
        self.db.writes.append((self.name,self.id,data.copy()))
        self.db.data[self.name][self.id].update(data)

    def delete(self):
        self.db.writes.append((self.name,self.id,{'operation':'delete'}))
        self.db.data.get(self.name,{}).pop(self.id,None)


class AcademicModuleTests(unittest.TestCase):
    def setUp(self):
        self.db=AcademicDB()
        for target,kwargs in [
            ('firebase_service.conectar_firebase',dict(return_value=(self.db,None))),
            ('socket.socket.connect',dict(side_effect=AssertionError('Red prohibida'))),
        ]:
            patcher=patch(target,**kwargs);patcher.start();self.addCleanup(patcher.stop)

    def app(self,module,role='admin'):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        for key,value in dict(logged_in=True,user_id='admin' if role=='admin' else 'teacher',user_role=role,
                              user_name='Admin' if role=='admin' else 'Ana',menu_actual=module).items():
            app.session_state[key]=value
        return app.run(timeout=15)

    def fill(self,app,label,value):
        next(item for item in app.text_input if item.label==label).set_value(value)

    def submit(self,app,label):
        return next(item for item in app.button if item.label.strip()==label).click().run(timeout=15)

    def test_registration_required_fields_preserve_validation(self):
        for nie,names,surname in [('', '', ''),('nuevo','',''),('nuevo','Nombre','')]:
            with self.subTest(nie=nie,names=names):
                app=self.app('Inscripción')
                for label,value in [('NIE*',nie),('Nombres*',names),('Apellidos*',surname)]:self.fill(app,label,value)
                app=self.submit(app,'Guardar inscripción')
                self.assertEqual(len(app.exception),0)
                self.assertTrue(any('obligatorios' in e.value for e in app.error))
                self.assertFalse(self.db.writes)

    def test_registration_duplicate_nie_does_not_write(self):
        app=self.app('Inscripción')
        for label,value in [('NIE*','1'),('Nombres*','Nombre'),('Apellidos*','Apellido')]:self.fill(app,label,value)
        app=self.submit(app,'Guardar inscripción')
        self.assertTrue(any('ya está registrado' in e.value for e in app.error))
        self.assertFalse(self.db.writes)

    def test_registration_saves_original_nested_firebase_schema(self):
        app=self.app('Inscripción')
        for label,value in [('NIE*',' nuevo '),('Nombres*',' Nombre '),('Apellidos*',' Apellido '),
                            ('Responsable','Responsable'),('Teléfono','2200-0000')]:self.fill(app,label,value)
        app=self.submit(app,'Guardar inscripción')
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(self.db.writes),1)
        row=self.db.data['alumnos']['nuevo']
        self.assertEqual(row['nombres'],'Nombre')
        self.assertEqual(row['ciclo_lectivo'],CICLO_LECTIVO)
        self.assertEqual(row['encargado']['nombre'],'Responsable')
        self.assertEqual(row['documentos'],dict(foto_url=None,doc_urls=[]))
        self.assertNotIn('encargado_nombre',row)

    def test_registration_uses_demo_cycle_and_production_button(self):
        app=self.app('Inscripción')
        self.assertEqual(app.title[0].value.strip(),f'Inscripción {CICLO_LECTIVO}')
        self.assertTrue(any(button.label==' Guardar inscripción' for button in app.button))

    def test_academic_admin_modules_reject_teacher(self):
        for name in ['Inscripción','Consulta Alumnos','Maestros','Asistencia Global']:
            with self.subTest(module=name):
                app=self.app(name,'docente')
                self.assertEqual(len(app.exception),0)
                self.assertTrue(app.error)
                self.assertFalse(self.db.writes)

    def student(self):
        app=self.app('Consulta Alumnos')
        self.fill(app,'Ingrese NIE:','1')
        return self.submit(app,'Buscar Expediente')

    def test_student_search_missing_and_existing(self):
        app=self.app('Consulta Alumnos')
        self.fill(app,'Ingrese NIE:','ausente')
        app=self.submit(app,'Buscar Expediente')
        self.assertTrue(any(e.value=='No existe' for e in app.error))
        app=self.student()
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertTrue(any('Prueba Uno' in title.value for title in app.title))
        self.assertEqual(len(app.tabs),7)
        self.assertFalse(self.db.writes)

    def test_student_search_by_grade_preserves_filter(self):
        app=self.app('Consulta Alumnos')
        app=app.radio[0].set_value('Grado').run()
        grade=next(item for item in app.selectbox if item.label=='Filtrar Grado')
        app=grade.select('Primer Grado').run()
        students=next(item for item in app.selectbox if item.label=='Seleccionar Alumno')
        self.assertTrue(any(option.startswith('1 -') for option in students.options))
        self.assertFalse(any(option.startswith('2 -') for option in students.options))
        self.assertFalse(self.db.writes)

    def test_student_edit_keeps_nested_fields_and_updates_session(self):
        app=self.student()
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.fill(app,'Nombres','Nombre actualizado')
        self.fill(app,'Responsable','Responsable actualizado')
        app=self.submit(app,'💾 Guardar Cambios')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertEqual(self.db.data['alumnos']['1']['encargado']['nombre'],'Responsable actualizado')
        self.assertEqual(app.session_state['alum_view']['nombres'],'Nombre actualizado')
        self.assertNotIn('encargado_nombre',self.db.data['alumnos']['1'])

    def test_student_delete_without_confirmation_is_rejected(self):
        app=self.student()
        app=self.submit(app,'🗑️ ELIMINAR DEFINITIVAMENTE')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertTrue(any('NIE escrito no coincide' in e.value for e in app.error))
        self.assertFalse(self.db.writes)

    def test_legacy_student_document_remains_available(self):
        self.db.data['alumnos']['1']['documentos']['doc_url']='https://example.invalid/documento.pdf'
        app=self.student()
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertTrue(any('Visualizar Documento 1' in item.label for item in app.expander))

    def teacher(self):
        app=self.app('Maestros')
        selector=app.selectbox(key='sel_prof_main')
        return selector.select(next(option for option in selector.options if 'Ana' in option)).run()

    def test_teacher_creation_requires_name(self):
        app=self.submit(self.app('Maestros'),'💾 Guardar')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertTrue(any('nombre del docente es obligatorio' in error.value for error in app.error))
        self.assertFalse(self.db.writes)

    def test_teacher_creation_preserves_original_fields(self):
        app=self.app('Maestros')
        self.fill(app,'Nombre',' Docente Prueba ')
        self.fill(app,'Código',' TEST ')
        app=self.submit(app,'💾 Guardar')
        self.assertEqual(len(app.exception),0,str(app.exception))
        row=next(row for row in self.db.data['maestros_perfil'].values() if row['nombre']=='Docente Prueba')
        self.assertEqual(row['codigo'],'TEST')
        self.assertTrue(row['activo'])
        self.assertIsNone(row['foto_url'])

    def test_teacher_profile_edit_preserves_firestore_id(self):
        app=self.teacher()
        app=app.button(key='btn_edit_t1').click().run()
        self.fill(app,'Teléfono','2222-3333')
        app=self.submit(app,'💾 Guardar Cambios')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertEqual(self.db.data['maestros_perfil']['t1']['telefono'],'2222-3333')

    def test_load_requires_at_least_one_subject(self):
        app=self.submit(self.teacher(),'Guardar Carga')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertTrue(any('al menos una materia' in warning.value for warning in app.warning))
        self.assertFalse(self.db.writes)

    def test_load_saves_teacher_id_subject_list_and_cycle(self):
        app=self.teacher()
        app=app.selectbox(key='g_prof').select('Primer Grado').run()
        app.multiselect[0].set_value(['Comunicación'])
        app=self.submit(app,'Guardar Carga')
        self.assertEqual(len(app.exception),0,str(app.exception))
        rows=[row for name,_,row in self.db.writes if name=='carga_academica']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['id_docente'],'t1')
        self.assertEqual(rows[0]['materias'],['Comunicación'])
        self.assertEqual(rows[0]['ciclo_lectivo'],CICLO_LECTIVO)

    def test_load_deletion_uses_only_selected_document(self):
        app=self.teacher()
        app=app.button(key='del_carga_c1').click().run()
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertNotIn('c1',self.db.data['carga_academica'])
        self.assertIn('c2',self.db.data['carga_academica'])

    def attendance(self):
        app=self.app('Asistencia Global')
        app=app.selectbox[0].select('Primer Grado').run()
        for control in app.date_input:control.set_value(date(CICLO_LECTIVO,2,15))
        return app

    def test_attendance_rejects_inverted_date_range(self):
        app=self.attendance()
        app.date_input[0].set_value(date(CICLO_LECTIVO,2,16))
        app=self.submit(app,'Generar Reporte')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertTrue(any('fecha inicial no puede ser mayor' in e.value for e in app.error))
        self.assertFalse(self.db.writes)

    def test_attendance_empty_students_and_empty_records(self):
        app=self.submit(self.attendance(),'Generar Reporte')
        self.assertTrue(any('No hay tomas' in info.value for info in app.info))
        self.db.data['alumnos']={}
        app=self.submit(self.attendance(),'Generar Reporte')
        self.assertTrue(any('No hay alumnos activos' in warning.value for warning in app.warning))
        self.assertFalse(self.db.writes)

    def test_attendance_report_preserves_totals_and_observations(self):
        self.db.data['asistencia']['day']=dict(
            grado='Primer Grado',ciclo_lectivo=CICLO_LECTIVO,
            fecha=TZ_SV.localize(datetime(CICLO_LECTIVO,2,15,12)),
            registros={'1':'Presente'},observaciones={'1':'Observación de prueba'})
        app=self.submit(self.attendance(),'Generar Reporte')
        self.assertEqual(len(app.exception),0,str(app.exception))
        row=app.dataframe[0].value.query("Alumno == 'Prueba Uno'").iloc[0]
        self.assertEqual(row['Asistencias'],1)
        self.assertEqual(row['% Asist.'],'100%')
        self.assertIn('Observación de prueba',row['Observaciones'])
        self.assertFalse(self.db.writes)

    def test_teacher_attendance_retains_scope_and_persistence(self):
        app=self.app('Tomar Asistencia','docente')
        self.assertEqual(app.selectbox[0].options,['Primer Grado'])
        app=app.date_input[0].set_value(date(CICLO_LECTIVO,2,15)).run()
        self.assertEqual(list(app.dataframe[0].value['NIE']),['1'])
        app=self.submit(app,'💾 Guardar Asistencia')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertEqual(len(self.db.writes),1)
        row=self.db.writes[0][2]
        self.assertEqual(row['ciclo_lectivo'],CICLO_LECTIVO)
        self.assertEqual(row['registros'],{'1':'Presente'})

    def test_teacher_attendance_empty_scope_does_not_write(self):
        self.db.data['alumnos']={}
        app=self.app('Tomar Asistencia','docente')
        self.assertEqual(len(app.exception),0,str(app.exception))
        self.assertTrue(any('Sin alumnos' in warning.value for warning in app.warning))
        self.assertFalse(self.db.writes)


if __name__=='__main__':unittest.main()
