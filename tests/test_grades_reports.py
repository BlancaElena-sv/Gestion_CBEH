"""Notas y reportes: cálculos existentes, persistencia y alcance con datos ficticios."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from test_academic_modules import AcademicDB
from config import CICLO_LECTIVO as CYCLE, COLEGIO_NOMBRE
from utils import redondear_mined
from views.notas_historicas import _calcular_promedios

COLUMNS = ['Act1 (25%)', 'Act2 (25%)', 'Alt1 (10%)', 'Alt2 (10%)', 'Examen (30%)']


class GradeTests(unittest.TestCase):
    def setUp(self):
        self.db = AcademicDB()
        self.month_id = f'{CYCLE}_Primer_Grado_Comunicación_Febrero'
        self.details = dict(zip(COLUMNS, [8., 9., 6., 7., 10.]))
        self.db.data['notas_mensuales'][self.month_id] = dict(
            ciclo_lectivo=CYCLE, grado='Primer Grado', materia='Comunicación', mes='Febrero',
            detalles={'1': dict(self.details, Promedio=9.)})
        for target, kwargs in (
            ('firebase_service.conectar_firebase', dict(return_value=(self.db, None))),
            ('socket.socket.connect', dict(side_effect=AssertionError('Red prohibida'))),
            ('view_dispatch.get_base64', dict(return_value='')),
        ):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self, teacher=False):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        for key, value in dict(logged_in=True, user_id='teacher' if teacher else 'admin',
                               user_role='docente' if teacher else 'admin', user_name='Ana',
                               menu_actual='Cargar Notas' if teacher else 'Notas').items():
            app.session_state[key] = value
        return app.run(timeout=15)

    def monthly(self, teacher=False, subject='Comunicación'):
        app = self.app(teacher)
        app = app.selectbox(key='doc_notas_grado' if teacher else 'g_reg').select('Primer Grado').run()
        app = app.selectbox(key='doc_notas_materia' if teacher else 'm_reg').select(subject).run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        return app

    def save(self, app, teacher=False):
        return app.button(key='doc_guardar_notas' if teacher else 'doc_guardar_notas_admin').click().run(timeout=15)

    def test_existing_weighted_average_and_teacher_match(self):
        for teacher in (False, True):
            with self.subTest(teacher=teacher):
                app = self.monthly(teacher)
                self.assertEqual(app.dataframe[0].value.iloc[0]['Promedio'], 9.)
                app = self.save(app, teacher)
                self.assertEqual(len(app.exception), 0, str(app.exception))
                self.assertEqual(self.db.data['notas']['1_'+self.month_id]['promedio_final'], 9.)

    def test_conduct_uses_single_grade_and_existing_rounding(self):
        self.db.data['carga_academica']['c1']['materias'] = ['Conducta']
        month_id = f'{CYCLE}_Primer_Grado_Conducta_Febrero'
        self.db.data['notas_mensuales'][month_id] = dict(
            ciclo_lectivo=CYCLE, grado='Primer Grado', materia='Conducta', mes='Febrero',
            detalles={'1': {'Nota Conducta': 8.5, 'Promedio': 9.}})
        for teacher in (False, True):
            with self.subTest(teacher=teacher):
                app = self.monthly(teacher, 'Conducta')
                self.assertIn('Nota Conducta', app.dataframe[0].value.columns)
                app = self.save(app, teacher)
                self.assertEqual(len(app.exception), 0, str(app.exception))
                self.assertEqual(self.db.data['notas']['1_'+month_id]['promedio_final'], 9.)

    def test_repeated_save_updates_same_ids_without_duplicate_records(self):
        app = self.monthly()
        app = self.save(app)
        app = self.save(app)
        self.assertEqual(len(app.exception), 0, str(app.exception))
        self.assertEqual(set(self.db.data['notas']), {'1_'+self.month_id})
        self.assertEqual(set(self.db.data['notas_mensuales']), {self.month_id})
        self.assertEqual(len(self.db.writes), 4)

    def test_monthly_and_individual_records_queued_in_same_batch(self):
        app = self.monthly()
        batch = Mock()
        batch.commit.side_effect = RuntimeError('Fallo simulado de commit')
        with patch.object(self.db, 'batch', return_value=batch):
            app = self.save(app)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(batch.set.call_count, 2)
        self.assertEqual({call.args[0].name for call in batch.set.call_args_list}, {'notas', 'notas_mensuales'})
        self.assertFalse(self.db.writes)
        self.assertEqual(self.db.data['notas'], {})

    def test_current_capture_excludes_previous_cycle_students(self):
        app = self.monthly()
        self.assertEqual(list(app.dataframe[0].value['NIE']), ['1'])

    def test_current_save_does_not_modify_historical_records(self):
        old = dict(nie='1', grado='Primer Grado', materia='Comunicación', mes='Febrero',
                   ciclo_lectivo=CYCLE-1, promedio_final=2.)
        self.db.data['notas']['historical'] = deepcopy(old)
        self.db.data['notas_mensuales']['legacy'] = {'detalles': {'1': {'Promedio': 2.}}, 'ciclo_lectivo': CYCLE-1}
        before = deepcopy(self.db.data['notas_mensuales']['legacy'])
        app = self.save(self.monthly())
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(self.db.data['notas']['historical'], old)
        self.assertEqual(self.db.data['notas_mensuales']['legacy'], before)

    def test_fallback_shows_only_current_saved_average_without_writing(self):
        self.db.data['notas_mensuales'] = {}
        self.db.data['notas'] = {
            'current': dict(nie='1', grado='Primer Grado', materia='Comunicación', mes='Febrero', ciclo_lectivo=CYCLE, promedio_final=8.),
            'old': dict(nie='1', grado='Primer Grado', materia='Comunicación', mes='Febrero', ciclo_lectivo=CYCLE-1, promedio_final=2.),
        }
        app = self.monthly()
        self.assertEqual(app.dataframe[0].value.iloc[0]['Promedio'], 8.)
        self.assertTrue(any('Solo se muestra el promedio final guardado' in w.value for w in app.warning))
        self.assertFalse(self.db.writes)

    def test_previous_cycle_only_does_not_fill_current_average(self):
        self.db.data['notas_mensuales'] = {}
        self.db.data['notas']['old'] = dict(nie='1', grado='Primer Grado', materia='Comunicación', mes='Febrero', ciclo_lectivo=CYCLE-1, promedio_final=9.)
        app = self.monthly()
        self.assertEqual(app.dataframe[0].value.iloc[0]['Promedio'], 0.)
        self.assertFalse(self.db.writes)

    def test_teacher_backup_contains_only_assigned_students_and_subject(self):
        app = self.monthly(True)
        with patch('components.academic_reports.components.html') as html:
            app = app.button(key='doc_pdf_cuadro_mes').click().run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        report = html.call_args.args[0]
        self.assertIn('Prueba Uno', report)
        self.assertNotIn('>Dos</td>', report)
        self.assertIn('Comunicación', report)
        self.assertNotIn('Responsable Prueba', report)
        self.assertNotIn('2200-0000', report)
        self.assertFalse(self.db.writes)

    def test_admin_rejects_invalid_scores_before_any_write(self):
        for value in (11., -1., float('nan')):
            with self.subTest(value=value):
                app = self.monthly()
                def edited(frame, **kwargs):
                    result = frame.copy()
                    result[COLUMNS[0]] = value
                    return result
                with patch('views.notas.st.data_editor', side_effect=edited):
                    app = self.save(app)
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(any('entre 0 y 10' in e.value for e in app.error))
                self.assertFalse(self.db.writes)

    def test_conflicting_monthly_cycle_is_not_read_as_current(self):
        self.db.data['notas_mensuales'][self.month_id]['ciclo_lectivo'] = CYCLE-1
        app = self.monthly()
        self.assertTrue(any('otro ciclo' in e.value for e in app.error))
        self.assertFalse(self.db.writes)

    def test_conflicting_individual_cycle_is_not_overwritten(self):
        row = dict(nie='1', grado='Primer Grado', materia='Comunicación', mes='Febrero',
                   ciclo_lectivo=CYCLE-1, promedio_final=2.)
        self.db.data['notas']['1_'+self.month_id] = deepcopy(row)
        app = self.save(self.monthly())
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('otro ciclo' in e.value for e in app.error))
        self.assertEqual(self.db.data['notas']['1_'+self.month_id], row)
        self.assertFalse(self.db.writes)


class ReportCalculationTests(unittest.TestCase):
    def test_existing_rounding_boundaries(self):
        self.assertEqual([redondear_mined(v) for v in [0., 4.49, 4.5, 9.49, 9.5, 10.]], [0., 4., 5., 9., 10., 10.])

    def test_historical_quarters_and_final_preserve_formula(self):
        notes = dict(zip(['Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre'],
                         [5.,5.,6.,6.,6.,7.,7.,7.,8.]))
        self.assertEqual(_calcular_promedios(notes, redondear_mined), (5.,6.,7.,6.))
        self.assertEqual(_calcular_promedios({}, redondear_mined), (0.,0.,0.,0.))

    def report(self, average_only=False):
        from components.academic_reports import mostrar_respaldo_mensual
        row = dict(NIE='1', Nombre='<script>Nombre</script>', Promedio=8.5,
                   **dict(zip(COLUMNS, [8.,9.,6.,7.,10.])))
        with patch('components.academic_reports.st.button', return_value=True), \
             patch('components.academic_reports.st.markdown'), \
             patch('components.academic_reports.components.html') as html:
            mostrar_respaldo_mensual(pd.DataFrame([row]), COLUMNS, 'Primer Grado', 'Comunicación',
                                    'Febrero', redondear_mined, lambda _: '', solo_promedios=average_only)
        return html.call_args.args[0]

    def test_monthly_report_uses_demo_identity_and_safe_text(self):
        html = self.report()
        self.assertIn(COLEGIO_NOMBRE.upper(), html)
        self.assertIn(f'CICLO {CYCLE}', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>Nombre', html)
        self.assertIn('>9.0</td>', html)
        self.assertIn('window.print()', html)
        self.assertIn('@media print', html)

    def test_average_only_report_does_not_fabricate_activity_scores(self):
        html = self.report(True)
        self.assertIn('actividades detalladas no disponibles', html)
        self.assertIn('>8.5</td>', html)
        self.assertEqual(html.count('<td>–</td>'), 5)


if __name__ == '__main__':
    unittest.main()
