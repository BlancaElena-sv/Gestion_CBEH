"""Seguridad de la presentación HTML al reutilizar los componentes de main."""
from datetime import date, datetime
import unittest
from unittest.mock import patch

from views import dashboard


class DashboardPresentationTests(unittest.TestCase):
    def test_database_text_is_escaped_in_agenda(self):
        with patch.object(dashboard.st, 'markdown') as markdown:
            dashboard._mostrar_agenda([dict(fecha='2027-02-03', titulo='<script>test</script>',
                                           descripcion='<img src=x onerror=test>', estado='<b>estado</b>')])
        html = markdown.call_args.args[0]
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;b&gt;estado&lt;/b&gt;', html)
        self.assertIn('agenda-estado', html)

    def test_invalid_agenda_date_displays_placeholder(self):
        with patch.object(dashboard.st, 'markdown') as markdown:
            dashboard._mostrar_agenda([dict(fecha='sin fecha', titulo='Actividad')])
        self.assertIn('agenda-dia">–', markdown.call_args.args[0])

    def test_financial_card_preserves_value_and_escapes_label(self):
        with patch.object(dashboard.st, 'markdown') as markdown:
            dashboard._tarjeta_finanza('<b>Saldo</b>', -1250.5, '#dc2626')
        html = markdown.call_args.args[0]
        self.assertIn('$-1,250.50', html)
        self.assertIn('&lt;b&gt;Saldo&lt;/b&gt;', html)

    def test_agenda_parser_preserves_calendar_date(self):
        self.assertEqual(dashboard._parsear_fecha('2027-02-03'), date(2027, 2, 3))
        self.assertEqual(dashboard._parsear_fecha(datetime(2027, 2, 3)), date(2027, 2, 3))
        self.assertIsNone(dashboard._parsear_fecha('no es fecha'))

    def test_dashboard_read_failures_show_safe_warnings(self):
        from unittest.mock import Mock
        db = Mock()
        db.collection.side_effect = RuntimeError('DETALLE_PRIVADO')
        with patch.object(dashboard.st, 'warning') as warning:
            config = dashboard._cargar_configuracion(db)
            agenda = dashboard._cargar_agenda(db, 'Docentes')
        self.assertEqual(config, dashboard.DEFAULT_DASHBOARD)
        self.assertEqual(agenda, [])
        self.assertEqual(warning.call_count, 2)
        self.assertNotIn('DETALLE_PRIVADO', str(warning.call_args_list))


if __name__ == '__main__':
    unittest.main()
