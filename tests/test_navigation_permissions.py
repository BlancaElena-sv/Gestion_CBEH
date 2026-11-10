"""Datos ficticios en memoria; sin Firebase remoto, secretos ni escrituras reales."""
from copy import deepcopy
import importlib
import inspect
import socket
import unittest
from unittest.mock import Mock, patch

from authorization import AccessDenied, Principal, authorize
from config import CICLO_LECTIVO as CYCLE
from navigation import BY_NAME, MODULES, modules_for_role
from teacher_store import Snapshot, TeacherStore


class FakeQuery:
    def __init__(self, db, name, filters=()):
        self.db, self.name, self.filters = db, name, filters

    def where(self, field, op, value):
        return FakeQuery(self.db, self.name, self.filters + ((field, op, value),))

    def stream(self):
        self.db.reads.append((self.name, self.filters))
        for key, row in list(self.db.data.get(self.name, {}).items()):
            if all(row.get(field) == value if op == "==" else row.get(field) in value
                   for field, op, value in self.filters):
                yield Snapshot(key, row)

    def document(self, doc_id):
        return FakeDocument(self.db, self.name, doc_id)

    def get(self):
        return list(self.stream())


class FakeDocument:
    def __init__(self, db, name, doc_id):
        self.db, self.name, self.id = db, name, doc_id

    def get(self):
        self.db.reads.append((self.name, self.id))
        return Snapshot(self.id, self.db.data.get(self.name, {}).get(self.id))

    def set(self, data):
        self.db.writes.append((self.name, self.id, deepcopy(data)))
        self.db.data.setdefault(self.name, {})[self.id] = deepcopy(data)


class FakeBatch:
    def __init__(self):
        self.pending = []

    def set(self, ref, data):
        self.pending.append((ref, data))

    def commit(self):
        for ref, data in self.pending:
            ref.set(data)


class FakeDB:
    project = "edumanager-demo"

    def __init__(self):
        self.data = {
            "usuarios": {"teacher": {"nombre": "Ana", "rol": "docente", "activo": True},
                         "admin": {"nombre": "Admin", "rol": "admin", "activo": True}},
            "maestros_perfil": {"t1": {"nombre": "Ana", "activo": True},
                                "t2": {"nombre": "Otro", "activo": True}},
            "carga_academica": {
                "c1": {"id_docente": "t1", "nombre_docente": "Ana", "grado": "Primer Grado",
                       "materias": ["Comunicación"], "ciclo_lectivo": CYCLE, "es_guia": False},
                "c2": {"id_docente": "t2", "nombre_docente": "Otro", "grado": "Segundo Grado",
                       "materias": ["Inglés"], "ciclo_lectivo": CYCLE},
                "old": {"id_docente": "t1", "grado": "Tercer Grado", "materias": ["Inglés"], "ciclo_lectivo": CYCLE-1}},
            "alumnos": {
                "1": {"nie": "1", "nombres": "Uno", "apellidos": "Prueba", "estado": "Activo",
                      "grado_actual": "Primer Grado", "ciclo_lectivo": CYCLE, "finanzas": "privado", "direccion": "privado"},
                "2": {"nie": "2", "nombres": "Dos", "estado": "Activo", "grado_actual": "Segundo Grado", "ciclo_lectivo": CYCLE},
                "old": {"nie": "old", "estado": "Activo", "grado_actual": "Primer Grado", "ciclo_lectivo": CYCLE-1}},
        }
        self.reads, self.writes = [], []

    def collection(self, name):
        return FakeQuery(self, name)

    def batch(self):
        return FakeBatch()


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.session = {"logged_in": True, "user_id": "teacher", "user_role": "docente", "user_name": "Ana"}
        session_patch = patch("authorization.st.session_state", self.session)
        session_patch.start()
        self.addCleanup(session_patch.stop)
        network = patch.object(socket.socket, "connect", side_effect=AssertionError("Red prohibida"))
        network.start()
        self.addCleanup(network.stop)

    def admin(self):
        self.session.update(user_id="admin", user_role="admin", user_name="Admin")

    def store(self, module="Cargar Notas"):
        return TeacherStore(self.db, authorize(self.db, module), module)

    def note(self, **overrides):
        data = dict(nie="1", grado="Primer Grado", materia="Comunicación", mes="Febrero",
                    ciclo_lectivo=CYCLE, promedio_final=8.0)
        data.update(overrides)
        return data

    def note_id(self, data):
        return f"{data['nie']}_{CYCLE}_{data['grado']}_{data['materia']}_{data['mes']}".replace(" ", "_")

    def test_catalog_has_unique_names_keys_and_only_known_roles(self):
        self.assertEqual(len(MODULES), len(BY_NAME))
        self.assertEqual(len(MODULES), len({m.key for m in MODULES}))
        self.assertTrue(all(set(m.roles) <= {"admin", "docente"} for m in MODULES))
        self.assertFalse(modules_for_role("desconocido"))

    def test_navigation_by_role_matches_server_authorization(self):
        for role, user in (("admin", "admin"), ("docente", "teacher")):
            self.session.update(user_id=user, user_role=role)
            for module in MODULES:
                with self.subTest(role=role, module=module.name):
                    if role in module.roles and not module.blocked:
                        self.assertEqual(authorize(self.db, module.name).role, role)
                    else:
                        with self.assertRaises(AccessDenied):
                            authorize(self.db, module.name)

    def test_invalid_sessions_denied(self):
        for changes in ({"logged_in": False}, {"logged_in": 1}, {"user_id": ""},
                        {"user_id": "ausente"}, {"user_role": "admin"}, {"user_role": "otro"}):
            with self.subTest(changes=changes):
                session = dict(self.session, **changes)
                with self.assertRaises(AccessDenied):
                    authorize(self.db, "Inicio", session)
        with self.assertRaises(AccessDenied):
            authorize(self.db, "Inicio", {})

    def test_inactive_missing_active_and_unknown_roles_denied(self):
        for user in ({"rol": "docente", "activo": False}, {"rol": "docente"},
                     {"rol": "otro", "activo": True}):
            self.db.data["usuarios"]["teacher"] = user
            with self.assertRaises(AccessDenied):
                authorize(self.db, "Inicio")

    def test_project_mismatch_denied(self):
        self.db.project = "gestioncbeh"
        with self.assertRaises(AccessDenied):
            authorize(self.db, "Inicio")

    def test_read_failure_denies_access(self):
        with patch.object(self.db, "collection", side_effect=RuntimeError("detalle sensible")):
            with self.assertRaises(AccessDenied) as result:
                authorize(self.db, "Inicio")
        self.assertNotIn("detalle sensible", str(result.exception))

    def test_unknown_and_blocked_modules_denied_before_dispatch_import(self):
        from view_dispatch import render_module
        for module in ("otra", "Mi Perfil", "Boletas de Notas", "Expediente Alumnos", "Finanzas"):
            with patch("view_dispatch.import_module") as loader:
                with self.assertRaises(AccessDenied):
                    render_module(self.db, module)
                loader.assert_not_called()

    def test_unique_legacy_name_resolves_id_and_current_assignments(self):
        principal = authorize(self.db, "Inicio")
        self.assertEqual(principal.teacher_id, "t1")
        self.assertEqual(principal.assignments, frozenset({("Primer Grado", "Comunicación")}))
        self.assertFalse(principal.guide_grades)

    def test_ambiguous_legacy_name_is_denied(self):
        self.db.data["maestros_perfil"]["duplicado"] = {"nombre": "Ana", "activo": True}
        with self.assertRaises(AccessDenied):
            authorize(self.db, "Inicio")

    def test_explicit_id_takes_priority_over_legacy_name(self):
        self.db.data["usuarios"]["teacher"]["id_docente"] = "t1"
        self.db.data["usuarios"]["teacher"]["nombre"] = "Nombre antiguo"
        self.assertEqual(authorize(self.db, "Inicio").teacher_id, "t1")

    def test_invalid_explicit_id_and_inactive_profile_are_denied(self):
        self.db.data["usuarios"]["teacher"]["id_docente"] = "ausente"
        with self.assertRaises(AccessDenied):
            authorize(self.db, "Inicio")
        self.db.data["usuarios"]["teacher"]["id_docente"] = "t1"
        self.db.data["maestros_perfil"]["t1"]["activo"] = False
        with self.assertRaises(AccessDenied):
            authorize(self.db, "Inicio")

    def test_direct_admin_view_functions_are_protected(self):
        for path in ("alumnos", "asistencia", "configuracion", "configuracion_dashboard", "docentes",
                     "finanzas", "inscripcion", "notas", "notas_historicas", "promocion"):
            module = importlib.import_module("views."+path)
            for name, function in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith("mostrar_") or function.__module__ != module.__name__:
                    continue
                kwargs = {key: self.db if key == "db" else None for key in inspect.signature(function).parameters}
                with self.subTest(function=name), self.assertRaises(AccessDenied):
                    function(**kwargs)

    def test_direct_teacher_panel_rejects_admin_unknown_and_invalid_sessions(self):
        from views.docente_panel import mostrar_panel_docente
        kwargs = {key: self.db if key == "db" else None for key in inspect.signature(mostrar_panel_docente).parameters}
        kwargs["opcion_seleccionada"] = "Tomar Asistencia"
        self.admin()
        with self.assertRaises(AccessDenied):
            mostrar_panel_docente(**kwargs)
        self.session.clear()
        with self.assertRaises(AccessDenied):
            mostrar_panel_docente(**kwargs)

    def test_teacher_cannot_access_financial_or_user_collections(self):
        store = self.store()
        for collection in ("finanzas", "usuarios", "bitacora", "otra"):
            with self.subTest(collection=collection), self.assertRaises(AccessDenied):
                store.collection(collection)

    def test_student_query_requires_authorized_grade(self):
        store = self.store()
        for grade in (None, "Segundo Grado"):
            query = store.collection("alumnos")
            if grade:
                query = query.where("grado_actual", "==", grade)
            with self.assertRaises(AccessDenied):
                list(query.stream())

    def test_students_are_current_cycle_and_personal_fields_are_redacted(self):
        rows = list(self.store().collection("alumnos").where("grado_actual", "==", "Primer Grado").stream())
        self.assertEqual([row.id for row in rows], ["1"])
        self.assertNotIn("direccion", rows[0].to_dict())
        self.assertNotIn("finanzas", rows[0].to_dict())
        self.assertFalse(hasattr(rows[0], "reference"))

    def test_old_cycle_query_is_rejected(self):
        with self.assertRaises(AccessDenied):
            list(self.store().collection("alumnos").where("grado_actual", "==", "Primer Grado")
                 .where("ciclo_lectivo", "==", CYCLE-1).stream())

    def test_note_reads_exclude_other_subjects_and_cycles(self):
        self.db.data["notas"] = {"ok": self.note(), "other": self.note(materia="Inglés"),
                                 "old": self.note(ciclo_lectivo=CYCLE-1)}
        rows = list(self.store().collection("notas").where("grado", "==", "Primer Grado").stream())
        self.assertEqual([row.id for row in rows], ["ok"])

    def test_own_loads_only(self):
        rows = list(self.store("Ver Mis Cargas").collection("carga_academica").stream())
        self.assertEqual([row.id for row in rows], ["c1"])

    def test_direct_foreign_and_legacy_monthly_documents_are_rejected_before_read(self):
        store = self.store()
        self.db.reads.clear()
        for doc_id in (f"{CYCLE}_Segundo_Grado_Inglés_Febrero", "Primer_Grado_Comunicación_Febrero",
                       f"{CYCLE-1}_Primer_Grado_Comunicación_Febrero"):
            with self.assertRaises(AccessDenied):
                store.collection("notas_mensuales").document(doc_id).get()
        self.assertFalse(self.db.reads)

    def test_note_write_is_scoped_by_grade_subject_cycle_and_student(self):
        for changes in ({"grado": "Segundo Grado"}, {"materia": "Inglés"},
                        {"ciclo_lectivo": CYCLE-1}, {"nie": "2"}, {"nie": "old"},
                        {"promedio_final": float("nan")}, {"promedio_final": 11}):
            data = self.note(**changes)
            with self.subTest(changes=changes), self.assertRaises(AccessDenied):
                self.store().collection("notas").document(self.note_id(data)).set(data)
        self.assertFalse(self.db.writes)

    def test_authorized_note_and_monthly_batch_commits_together(self):
        store = self.store()
        data = self.note()
        batch = store.batch()
        batch.set(store.collection("notas").document(self.note_id(data)), data)
        monthly = {key: data[key] for key in ("grado", "materia", "mes", "ciclo_lectivo")}
        monthly["detalles"] = {"1": {"Promedio": 8.0}}
        monthly_id = self.note_id(data)[2:]
        batch.set(store.collection("notas_mensuales").document(monthly_id), monthly)
        self.assertFalse(self.db.writes)
        batch.commit()
        self.assertEqual(len(self.db.writes), 2)

    def test_one_invalid_batch_record_prevents_all_writes(self):
        store = self.store()
        batch = store.batch()
        for data in (self.note(), self.note(materia="Inglés")):
            batch.set(store.collection("notas").document(self.note_id(data)), data)
        with self.assertRaises(AccessDenied):
            batch.commit()
        self.assertFalse(self.db.writes)

    def test_revoked_assignment_and_inactive_user_block_writes(self):
        for change in ("assignment", "active"):
            store = self.store()
            if change == "assignment":
                self.db.data["carga_academica"]["c1"]["materias"] = []
            else:
                self.db.data["usuarios"]["teacher"]["activo"] = False
            data = self.note()
            with self.assertRaises(AccessDenied):
                store.collection("notas").document(self.note_id(data)).set(data)
            self.db.data["carga_academica"]["c1"]["materias"] = ["Comunicación"]
        self.assertFalse(self.db.writes)

    def test_attendance_allowed_grade_only_and_student_membership(self):
        store = self.store("Tomar Asistencia")
        doc_id = f"{CYCLE}_{CYCLE}-02-01_Primer Grado"
        data = dict(grado="Primer Grado", ciclo_lectivo=CYCLE,
                    registros={"1": "Presente"}, observaciones={"1": ""})
        store.collection("asistencia").document(doc_id).set(data)
        self.assertEqual(len(self.db.writes), 1)
        data["registros"]["2"] = "Presente"
        with self.assertRaises(AccessDenied):
            store.collection("asistencia").document(doc_id).set(data)
        with self.assertRaises(AccessDenied):
            store.collection("asistencia").document(f"{CYCLE}_{CYCLE}-02-01_Segundo Grado").get()
        self.assertEqual(len(self.db.writes), 1)

    def test_read_only_module_cannot_write(self):
        store = self.store("Mis Listados")
        with self.assertRaises(AccessDenied):
            store.collection("asistencia").document("cualquier").set({})

    def test_extra_fields_in_teacher_write_are_rejected(self):
        data = self.note(password_hash="prohibido")
        with self.assertRaises(AccessDenied):
            self.store().collection("notas").document(self.note_id(data)).set(data)
        self.assertFalse(self.db.writes)

    def test_dashboard_adapter_exposes_only_own_profile_loads_and_teacher_agenda(self):
        store = self.store("Inicio")
        self.db.data["agenda"] = {
            "all": {"audiencia": "Todos"}, "teacher": {"audiencia": "Docentes"},
            "admin": {"audiencia": "Administración"}}
        self.assertEqual({doc.id for doc in store.collection("agenda").stream()}, {"all", "teacher"})
        self.assertEqual([doc.id for doc in store.collection("maestros_perfil").where("nombre", "==", "Ana").stream()], ["t1"])
        with self.assertRaises(AccessDenied):
            store.collection("maestros_perfil").document("t2").get()
        with self.assertRaises(AccessDenied):
            store.collection("configuracion").document("general").get()

    def test_admin_dispatch_contracts_are_resolved_from_catalog(self):
        from view_dispatch import render_module
        self.admin()
        for module in modules_for_role("admin"):
            if module.blocked or module.name == "Inicio":
                continue
            path, name = module.target.split(":")
            target = getattr(importlib.import_module(path), name)
            mock = Mock(__signature__=inspect.signature(target))
            with self.subTest(module=module.name), patch.object(importlib.import_module(path), name, mock):
                render_module(self.db, module.name)
                mock.assert_called_once()
                inspect.signature(target).bind(**mock.call_args.kwargs)

    def test_mass_reset_callback_stays_blocked(self):
        from view_dispatch import render_module
        self.admin()
        def configuration(**kwargs):
            with self.assertRaises(AccessDenied):
                kwargs["borrar_coleccion"]("alumnos")
        target = importlib.import_module("views.configuracion").mostrar_configuracion
        mock = Mock(side_effect=configuration, __signature__=inspect.signature(target))
        with patch("views.configuracion.mostrar_configuracion", mock):
            render_module(self.db, "Configuración (Usuarios)")
        self.assertFalse(self.db.writes)


class AppNavigationTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        network = patch.object(socket.socket, "connect", side_effect=AssertionError("Red prohibida"))
        network.start()
        self.addCleanup(network.stop)
        connection = patch("firebase_service.conectar_firebase", return_value=(self.db, None))
        connection.start()
        self.addCleanup(connection.stop)

    def app(self, role, module):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        for key, value in dict(logged_in=True, user_id="admin" if role == "admin" else "teacher",
                               user_role=role, user_name="Nombre de sesión", menu_actual=module).items():
            app.session_state[key] = value
        return app.run(timeout=15)

    def test_admin_modules_render_without_writing(self):
        for module in modules_for_role("admin"):
            if module.blocked:
                continue
            with self.subTest(module=module.name):
                app = self.app("admin", module.name)
                self.assertEqual(len(app.exception), 0, str(app.exception))
                self.assertEqual(len(app.error), 0, str(app.error))
        self.assertFalse(self.db.writes)

    def test_teacher_modules_render_without_writing(self):
        for module in modules_for_role("docente"):
            if module.blocked:
                continue
            with self.subTest(module=module.name):
                app = self.app("docente", module.name)
                self.assertEqual(len(app.exception), 0, str(app.exception))
                self.assertEqual(len(app.error), 0, str(app.error))
                self.assertNotIn("Finanzas", [button.label for button in app.sidebar.button])
        self.assertFalse(self.db.writes)

    def test_forged_navigation_to_finances_shows_denial(self):
        app = self.app("docente", "Finanzas")
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertFalse(any(name == "finanzas" for name, _ in self.db.reads))

    def test_inactive_session_is_cleared_before_sidebar(self):
        self.db.data["usuarios"]["teacher"]["activo"] = False
        app = self.app("docente", "Tomar Asistencia")
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertEqual(len(app.sidebar.button), 0)
        self.assertNotIn("logged_in", app.session_state)

    def test_no_assignments_disables_operations_without_crashing(self):
        self.db.data["carga_academica"] = {}
        app = self.app("docente", "Tomar Asistencia")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("No tiene asignaciones" in info.value for info in app.info))
        self.assertFalse(self.db.writes)

    def test_teacher_can_save_attendance_only_for_current_students(self):
        app = self.app("docente", "Tomar Asistencia")
        save = next(button for button in app.button if "Guardar Asistencia" in button.label)
        app = save.click().run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        self.assertEqual(len(self.db.writes), 1)
        collection, _, row = self.db.writes[0]
        self.assertEqual(collection, "asistencia")
        self.assertEqual(set(row["registros"]), {"1"})
        self.assertEqual(row["ciclo_lectivo"], CYCLE)

    def test_teacher_can_save_notes_atomically_for_assigned_subject(self):
        app = self.app("docente", "Cargar Notas")
        self.assertEqual(app.selectbox(key="doc_notas_grado").options, ["Select...", "Primer Grado"])
        app = app.selectbox(key="doc_notas_grado").select("Primer Grado").run()
        self.assertEqual(app.selectbox(key="doc_notas_materia").options, ["Select...", "Comunicación"])
        app = app.selectbox(key="doc_notas_materia").select("Comunicación").run()
        app = app.button(key="doc_guardar_notas").click().run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        self.assertEqual({name for name, _, _ in self.db.writes}, {"notas", "notas_mensuales"})
        self.assertEqual(len(self.db.writes), 2)

    def test_revoked_teacher_cannot_save_from_already_rendered_form(self):
        app = self.app("docente", "Tomar Asistencia")
        self.db.data["usuarios"]["teacher"]["activo"] = False
        save = next(button for button in app.button if "Guardar Asistencia" in button.label)
        app = save.click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertFalse(self.db.writes)


if __name__ == "__main__":
    unittest.main()
