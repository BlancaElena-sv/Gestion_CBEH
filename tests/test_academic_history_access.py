"""Históricos y política de acceso a expedientes/boletas: lectura y privacidad."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from test_academic_modules import AcademicDB
from authorization import AccessDenied, authorize
from config import CICLO_LECTIVO as CYCLE, COLEGIO_NOMBRE


class HistoryAccessTests(unittest.TestCase):
    def setUp(self):
        self.db = AcademicDB()
        months = ['Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre']
        for cycle, value in [(CYCLE, 9.), (CYCLE-1, 6.)]:
            for month in months:
                self.db.data['notas'][f'1_{cycle}_{month}'] = dict(
                    nie='1', ciclo_lectivo=cycle, grado='Primer Grado', materia='Comunicación',
                    mes=month, promedio_final=value)
        self.before = deepcopy(self.db.data['notas'])
        for target, kwargs in (
            ('firebase_service.conectar_firebase', dict(return_value=(self.db, None))),
            ('socket.socket.connect', dict(side_effect=AssertionError('Red prohibida'))),
            ('view_dispatch.get_base64', dict(return_value='')),
        ):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        for key, value in dict(logged_in=True, user_id='admin', user_role='admin',
                               user_name='Admin', menu_actual='Notas').items():
            app.session_state[key] = value
        return app.run(timeout=15)

    def history(self, cycle):
        app = self.app()
        app = app.selectbox(key='hist_ciclo_notas').select(cycle).run()
        app = app.selectbox(key='hist_grado_notas').select('Primer Grado').run()
        selector = app.selectbox(key='hist_alumno_notas')
        app = selector.select(next(v for v in selector.options if 'NIE 1' in v)).run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        return app

    def test_history_selects_student_and_keeps_cycles_separate(self):
        app = self.history(CYCLE-1)
        frame = app.tabs[2].dataframe[0].value
        self.assertEqual(frame.iloc[0]['Feb'], 6.)
        self.assertEqual(frame.iloc[0]['PF'], 6.)
        app = app.selectbox(key='hist_ciclo_notas').select(CYCLE).run()
        if not app.tabs[2].dataframe:
            selector = app.selectbox(key='hist_alumno_notas')
            app = selector.select(next(v for v in selector.options if 'NIE 1' in v)).run()
        self.assertEqual(app.tabs[2].dataframe[0].value.iloc[0]['PF'], 9.)
        self.assertEqual(self.db.data['notas'], self.before)
        self.assertFalse(self.db.writes)

    def test_historical_legacy_without_cycle_remains_2026(self):
        self.db.data['notas'] = {'legacy': dict(nie='1', grado='Primer Grado', materia='Comunicación', mes='Febrero', promedio_final=7.)}
        app = self.history(2026)
        self.assertEqual(app.tabs[2].dataframe[0].value.iloc[0]['Feb'], 7.)
        self.assertFalse(self.db.writes)

    def test_history_empty_cycle_has_no_print_action(self):
        app = self.app()
        app = app.selectbox(key='hist_ciclo_notas').select(CYCLE-2).run()
        app = app.selectbox(key='hist_grado_notas').select('Primer Grado').run()
        self.assertTrue(any('No se encontraron notas' in item.value for item in app.tabs[2].warning))
        self.assertFalse(any(button.key == 'btn_boleta_historica' for button in app.button))
        self.assertFalse(self.db.writes)

    def test_historical_print_has_selected_cycle_identity_and_average(self):
        app = self.history(CYCLE-1)
        with patch('views.notas_historicas.components.html') as html:
            app = app.button(key='btn_boleta_historica').click().run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        report = html.call_args.args[0]
        self.assertIn(COLEGIO_NOMBRE.upper(), report)
        self.assertIn(f'CICLO {CYCLE-1}', report)
        self.assertIn('Prueba Uno', report)
        self.assertIn('class="final">6.0', report)
        self.assertIn('window.print()', report)
        self.assertIn('@page', report)
        self.assertEqual(self.db.data['notas'], self.before)
        self.assertFalse(self.db.writes)

    def test_historical_print_requires_subject_selection(self):
        app = self.history(CYCLE-1)
        app = app.multiselect(key='hist_materias_boleta').set_value([]).run()
        self.assertTrue(any('Seleccione al menos una materia' in i.value for i in app.tabs[2].info))
        self.assertFalse(any(b.key == 'btn_boleta_historica' for b in app.button))
        self.assertFalse(self.db.writes)

    def test_historical_print_escapes_personal_text(self):
        self.db.data['alumnos']['1']['nombres'] = '<script>Nombre</script>'
        app = self.history(CYCLE-1)
        with patch('views.notas_historicas.components.html') as html:
            app = app.button(key='btn_boleta_historica').click().run()
        report = html.call_args.args[0]
        self.assertNotIn('<script>Nombre</script>', report)
        self.assertIn('&lt;script&gt;Nombre&lt;/script&gt;', report)
        self.assertFalse(self.db.writes)

    def session(self):
        return dict(logged_in=True, user_id='teacher', user_role='docente', user_name='Ana')

    def test_guide_identity_is_bound_to_teacher_id_and_current_cycle(self):
        self.db.data['usuarios']['teacher']['id_docente'] = 't1'
        self.db.data['carga_academica']['c1']['es_guia'] = True
        self.db.data['carga_academica']['c2']['es_guia'] = True
        self.db.data['carga_academica']['old']['es_guia'] = True
        principal = authorize(self.db, 'Inicio', self.session())
        self.assertEqual(principal.teacher_id, 't1')
        self.assertEqual(principal.guide_grades, frozenset({'Primer Grado'}))
        self.assertNotIn('Segundo Grado', principal.guide_grades)
        self.assertNotIn('Tercer Grado', principal.guide_grades)

    def test_teacher_and_guide_cannot_read_full_records_or_all_subject_reports(self):
        for guide in (False, True):
            self.db.data['carga_academica']['c1']['es_guia'] = guide
            for module in ('Expediente Alumnos', 'Boletas de Notas', 'Consulta Alumnos', 'Notas'):
                self.db.reads.clear()
                with self.subTest(guide=guide, module=module), self.assertRaises(AccessDenied):
                    authorize(self.db, module, self.session())
                self.assertFalse(any(name in {'alumnos','bitacora','finanzas','notas'} for name, _ in self.db.reads))
        self.assertFalse(self.db.writes)

    def test_multiple_guide_flags_do_not_unlock_sensitive_modules(self):
        self.db.data['carga_academica']['c1']['es_guia'] = True
        self.db.data['carga_academica']['c2'].update(grado='Primer Grado', es_guia=True)
        for module in ('Expediente Alumnos', 'Boletas de Notas'):
            with self.assertRaises(AccessDenied):
                authorize(self.db, module, self.session())
        self.assertFalse(self.db.writes)

    def test_direct_historical_function_rejects_teacher(self):
        from views.notas_historicas import mostrar_notas_historicas
        with patch('authorization.st.session_state', self.session()), self.assertRaises(AccessDenied):
            mostrar_notas_historicas(self.db, [], {}, lambda x: x, lambda _: '')
        self.assertFalse(self.db.writes)

    def student_report(self, cycle=CYCLE):
        self.db.data['alumnos']['1']['ciclo_lectivo'] = cycle
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        for key, value in dict(logged_in=True, user_id='admin', user_role='admin', user_name='Admin',
                               menu_actual='Consulta Alumnos', alum_view=deepcopy(self.db.data['alumnos']['1'])).items():
            app.session_state[key] = value
        with patch('views.alumnos.components.html') as html:
            app = app.run(timeout=15)
        self.assertEqual(len(app.exception), 0, str(app.exception))
        return app, html.call_args.args[0]

    def test_individual_report_uses_student_cycle_without_mixing_years(self):
        app, report = self.student_report()
        self.assertIn(f'INFORME DE NOTAS · CICLO {CYCLE}', report)
        self.assertIn('<td>9.0</td>', report)
        self.assertNotIn('<td>6.0</td>', report)
        self.assertEqual(self.db.data['notas'], self.before)
        self.assertFalse(self.db.writes)

    def test_individual_report_can_show_students_previous_cycle(self):
        _, report = self.student_report(CYCLE-1)
        self.assertIn(f'CICLO {CYCLE-1}', report)
        self.assertIn('<td>6.0</td>', report)
        self.assertNotIn('<td>9.0</td>', report)
        self.assertFalse(self.db.writes)

    def test_individual_report_does_not_assign_previous_cycle_guide(self):
        self.db.data['carga_academica']['old_guide'] = dict(
            grado='Primer Grado', es_guia=True, ciclo_lectivo=CYCLE-1,
            id_docente='t2', nombre_docente='Guía anterior')
        _, report = self.student_report()
        self.assertNotIn('Guía anterior', report)
        self.assertIn('No Asignado', report)
        _, report = self.student_report(CYCLE-1)
        self.assertIn('Guía anterior', report)

    def test_individual_report_escapes_name_and_keeps_demo_identity(self):
        self.db.data['alumnos']['1']['nombres'] = '<script>Nombre</script>'
        _, report = self.student_report()
        self.assertIn('&lt;script&gt;Nombre&lt;/script&gt;', report)
        self.assertNotIn('<script>Nombre</script>', report)
        self.assertIn(COLEGIO_NOMBRE.upper(), report)
        self.assertIn('window.print()', report)

    def test_annual_report_keeps_current_cycle_and_averages(self):
        app = self.app()
        app = app.selectbox(key='g_rep_anual').select('Primer Grado').run()
        with patch('views.notas.components.html') as html:
            app = next(b for b in app.button if b.label=='Generar Reporte de Rendimiento Anual').click().run(timeout=15)
        self.assertEqual(len(app.exception), 0, str(app.exception))
        report = html.call_args.args[0]
        self.assertIn(f'CICLO {CYCLE}', report)
        self.assertIn('Prueba Uno', report)
        self.assertIn('>9.0</td>', report)
        self.assertNotIn('>6.0</td>', report)
        self.assertFalse(self.db.writes)

    def test_batch_reports_keep_subject_selection_and_current_cycle(self):
        app = self.app()
        app = app.selectbox(key='g_lote_v2').select('Primer Grado').run()
        app.multiselect[0].set_value(['Comunicación'])
        with patch('views.notas.components.html') as html:
            app = next(b for b in app.button if b.label=='Generar Lote Personalizado').click().run(timeout=15)
        self.assertEqual(len(app.exception), 0, str(app.exception))
        report = html.call_args.args[0]
        self.assertEqual(report.count('class="boleta-container"'), 1)
        self.assertIn(f'ACADÉMICO - {CYCLE}', ' '.join(report.split()))
        self.assertIn('Comunicación', report)
        self.assertNotIn('Inglés', report)
        self.assertIn('>9.0</td>', report)
        self.assertFalse(self.db.writes)

    def test_batch_reports_reject_empty_subject_selection(self):
        app = self.app()
        app = app.selectbox(key='g_lote_v2').select('Primer Grado').run()
        app.multiselect[0].set_value([])
        with patch('views.notas.components.html') as html:
            app = next(b for b in app.button if b.label=='Generar Lote Personalizado').click().run()
        self.assertTrue(any('Seleccione al menos una materia' in w.value for w in app.warning))
        html.assert_not_called()
        self.assertFalse(self.db.writes)


if __name__ == '__main__':
    unittest.main()
