"""Ubicación por pestaña y seguridad de controles; solo Firestore simulado."""
from copy import deepcopy
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from test_academic_modules import AcademicDB


class StudentAdminPlacementTests(unittest.TestCase):
    def setUp(self):
        self.db = AcademicDB()
        self.history = [
            dict(ciclo=2025, grado='Primer Grado', resultado='Promovido',
                 grado_destino='Segundo Grado', ciclo_destino=2026, fecha='20/11/2025', usuario='Prueba'),
            dict(ciclo=2026, grado='Segundo Grado', resultado='Promovido',
                 grado_destino='Tercer Grado', ciclo_destino=2027, fecha='20/11/2026', usuario='Prueba'),
        ]
        self.db.data['alumnos']['1']['historial_academico'] = deepcopy(self.history)
        for target, kwargs in (
            ('firebase_service.conectar_firebase', dict(return_value=(self.db, None))),
            ('socket.socket.connect', dict(side_effect=AssertionError('Red prohibida'))),
        ):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self, role='admin', active=True):
        if not active:
            self.db.data['alumnos']['1'].update(estado='Retirado', fecha_baja='10/11/2026',
                                               motivo_baja='Cambio de institución')
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        for key, value in dict(logged_in=True, user_id='admin' if role == 'admin' else 'teacher',
                               user_role=role, user_name='Prueba', menu_actual='Consulta Alumnos',
                               alum_view=deepcopy(self.db.data['alumnos']['1'])).items():
            app.session_state[key] = value
        return app.run(timeout=15)

    def assert_clean(self, app):
        self.assertEqual(len(app.exception), 0, str(app.exception))

    def test_active_controls_only_in_state_tab_and_not_duplicated(self):
        app = self.app()
        self.assert_clean(app)
        state_keys = {button.key for button in app.tabs[5].button}
        self.assertIn('btn_baja_1', state_keys)
        self.assertIn('delete_alumno_1', state_keys)
        self.assertEqual(len(app.tabs[6].button), 0)
        for key in ('btn_baja_1', 'delete_alumno_1'):
            self.assertEqual(sum(button.key == key for button in app.button), 1)
        self.assertFalse(self.db.writes)

    def test_reactivation_only_in_state_tab_and_not_duplicated(self):
        app = self.app(active=False)
        self.assert_clean(app)
        self.assertIn('btn_reactivar_1', {button.key for button in app.tabs[5].button})
        self.assertNotIn('btn_baja_1', {button.key for button in app.button})
        self.assertEqual(sum(button.key == 'btn_reactivar_1' for button in app.button), 1)
        self.assertEqual(len(app.tabs[6].button), 0)
        self.assertFalse(self.db.writes)

    def test_complete_history_preserves_table_order_and_trajectory(self):
        app = self.app()
        self.assert_clean(app)
        frame = app.tabs[6].dataframe[0].value
        self.assertEqual(list(frame['Ciclo']), [2026, 2025])
        self.assertEqual(list(frame['Grado cursado']), ['Segundo Grado', 'Primer Grado'])
        self.assertEqual(list(frame['Procesado por']), ['Prueba', 'Prueba'])
        self.assertTrue(any('Trayectoria del alumno' in item.value for item in app.tabs[6].markdown))
        self.assertEqual(self.db.data['alumnos']['1']['historial_academico'], self.history)
        self.assertFalse(self.db.writes)

    def test_empty_history_keeps_its_messages_and_no_admin_inputs(self):
        self.db.data['alumnos']['1']['historial_academico'] = []
        app = self.app()
        self.assert_clean(app)
        self.assertTrue(any('no tiene registros históricos' in item.value for item in app.tabs[6].info))
        self.assertEqual(len(app.tabs[6].text_input), 0)
        self.assertEqual(len(app.tabs[6].checkbox), 0)
        self.assertFalse(self.db.writes)

    def test_deactivation_other_reason_still_required(self):
        app = self.app()
        app = app.selectbox(key='motivo_baja_1').select('Otro').run()
        app = app.button(key='btn_baja_1').click().run()
        self.assert_clean(app)
        self.assertTrue(any('Debe especificar el motivo' in item.value for item in app.tabs[5].error))
        self.assertFalse(self.db.writes)

    def test_simulated_deactivation_writes_once_and_preserves_history(self):
        app = self.app()
        app = app.button(key='btn_baja_1').click().run(timeout=15)
        self.assert_clean(app)
        self.assertEqual(len(self.db.writes), 1)
        self.assertEqual(self.db.writes[0][:2], ('alumnos', '1'))
        self.assertEqual(self.db.data['alumnos']['1']['estado'], 'Retirado')
        self.assertEqual(self.db.data['alumnos']['1']['historial_academico'], self.history)
        self.assertIn('btn_reactivar_1', {button.key for button in app.tabs[5].button})

    def test_simulated_reactivation_writes_once_and_preserves_history(self):
        app = self.app(active=False)
        app = app.button(key='btn_reactivar_1').click().run(timeout=15)
        self.assert_clean(app)
        self.assertEqual(len(self.db.writes), 1)
        self.assertEqual(self.db.data['alumnos']['1']['estado'], 'Activo')
        self.assertEqual(self.db.data['alumnos']['1']['historial_academico'], self.history)
        self.assertIn('btn_baja_1', {button.key for button in app.tabs[5].button})

    def test_delete_requires_both_nie_and_confirmation_checkbox(self):
        app = self.app()
        app = app.button(key='delete_alumno_1').click().run()
        self.assert_clean(app)
        self.assertTrue(any('NIE escrito no coincide' in item.value for item in app.tabs[5].error))
        app.text_input(key='confirm_delete_1').set_value('1')
        app = app.button(key='delete_alumno_1').click().run()
        self.assert_clean(app)
        self.assertTrue(any('Debe confirmar que comprende' in item.value for item in app.tabs[5].error))
        self.assertIn('1', self.db.data['alumnos'])
        self.assertFalse(self.db.writes)

    def test_teacher_cannot_render_admin_controls(self):
        app = self.app(role='docente')
        self.assert_clean(app)
        self.assertEqual(len(app.tabs), 0)
        self.assertTrue(app.error)
        self.assertFalse(self.db.writes)


if __name__ == '__main__':
    unittest.main()
