"""Pruebas sin SDK, credenciales, red ni datos reales: python -m unittest discover -s tests -v."""

import ast
import importlib
import io
import os
from pathlib import Path
import socket
import sys
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "edumanager-demo"
MODULES = ("firebase_demo_service", "firebase_service", "firebase_selector")


class FirebaseIsolationTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Red prohibida"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.cred = types.SimpleNamespace(project_id=PROJECT)
        self.app = types.SimpleNamespace(project_id=PROJECT, credential=self.cred)
        self.db = Mock(project=PROJECT)
        self.admin = types.ModuleType("firebase_admin")
        self.admin.credentials = types.SimpleNamespace(Certificate=Mock(return_value=self.cred))
        self.admin.firestore = types.SimpleNamespace(client=Mock(return_value=self.db))
        self.admin.storage = types.SimpleNamespace(bucket=Mock())
        self.admin.get_app = Mock(side_effect=ValueError("No existe"))
        self.admin.initialize_app = Mock(side_effect=self.initialize)
        self.st = types.ModuleType("streamlit")
        self.st.secrets = {"firebase_demo": {"project_id": PROJECT, "private_key": "ficticia\\n"}}
        self.st.error = Mock()
        # Guardar/restaurar módulos para que los dobles no contaminen otras suites.
        self.modules = patch.dict(sys.modules, {"firebase_admin": self.admin, "streamlit": self.st})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        for name in MODULES:
            sys.modules.pop(name, None)
        self.core = importlib.import_module("firebase_demo_service")
        self.facade = importlib.import_module("firebase_service")
        self.selector = importlib.import_module("firebase_selector")
        self.files = patch.object(self.core.os.path, "exists", return_value=False)
        self.files_mock = self.files.start()
        self.addCleanup(self.files.stop)

    def initialize(self, *args, **kwargs):
        self.admin.get_app.side_effect = None
        self.admin.get_app.return_value = self.app
        return self.app

    def existing_app(self):
        self.admin.get_app.side_effect = None
        self.admin.get_app.return_value = self.app

    def file(self, name="foto.png"):
        archivo = io.BytesIO(b"contenido de prueba")
        archivo.name = name
        return archivo

    def bucket(self, name="edumanager-demo.firebasestorage.app"):
        os.environ["FIREBASE_DEMO_STORAGE_BUCKET"] = name
        bucket = Mock()
        bucket.name = name
        self.admin.storage.bucket.return_value = bucket
        return bucket

    def test_all_entry_points_use_same_validated_client(self):
        for connect in (self.core.conectar_firebase_demo, self.facade.conectar_firebase,
                        self.selector.conectar_firebase):
            self.assertEqual(connect(), (self.db, None))
        self.admin.initialize_app.assert_called_once_with(
            self.cred, options={"projectId": PROJECT}, name="edumanager_demo")
        for call in self.admin.firestore.client.call_args_list:
            self.assertEqual(call.kwargs, {"app": self.app})
        self.db.collection.assert_not_called()

    def test_secrets_are_copied_and_newlines_normalized(self):
        self.core.conectar_firebase_demo()
        self.assertEqual(self.admin.credentials.Certificate.call_args.args[0]["private_key"], "ficticia\n")
        self.assertEqual(self.st.secrets["firebase_demo"]["private_key"], "ficticia\\n")

    def test_local_credentials_preserve_priority(self):
        self.files_mock.return_value = True
        self.core.conectar_firebase_demo()
        self.admin.credentials.Certificate.assert_called_once_with("credenciales_demo.json")

    def test_wrong_credentials_rejected_before_initialization(self):
        self.cred.project_id = "gestioncbeh"
        db, error = self.facade.conectar_firebase()
        self.assertIsNone(db)
        self.assertIn("rechazadas", error)
        self.admin.initialize_app.assert_not_called()
        self.admin.firestore.client.assert_not_called()

    def test_existing_wrong_app_rejected(self):
        self.existing_app()
        self.app.project_id = "gestioncbeh"
        self.assertIsNone(self.facade.conectar_firebase()[0])
        self.admin.firestore.client.assert_not_called()

    def test_existing_app_with_wrong_credential_rejected(self):
        self.existing_app()
        self.cred.project_id = "gestioncbeh"
        self.assertIsNone(self.facade.conectar_firebase()[0])
        self.admin.firestore.client.assert_not_called()

    def test_default_app_is_never_selected(self):
        self.existing_app()
        self.core.conectar_firebase_demo()
        self.admin.get_app.assert_called_once_with("edumanager_demo")
        self.admin.credentials.Certificate.assert_not_called()

    def test_wrong_client_is_never_returned_for_reads_or_writes(self):
        self.db.project = "gestioncbeh"
        self.assertIsNone(self.facade.conectar_firebase()[0])
        self.assertIsNone(self.facade.obtener_usuario("prueba"))
        self.db.collection.assert_not_called()

    def test_missing_credentials_do_not_fall_back(self):
        self.st.secrets = {}
        self.assertIsNone(self.facade.conectar_firebase()[0])
        self.admin.initialize_app.assert_not_called()
        self.admin.firestore.client.assert_not_called()

    def test_credential_errors_do_not_disclose_sdk_details(self):
        self.admin.credentials.Certificate.side_effect = RuntimeError("SECRETO_NO_PUBLICAR")
        _, error = self.facade.conectar_firebase()
        self.assertNotIn("SECRETO_NO_PUBLICAR", error)

    def test_client_errors_do_not_disclose_sdk_details(self):
        self.admin.firestore.client.side_effect = RuntimeError("SECRETO_NO_PUBLICAR")
        self.assertNotIn("SECRETO_NO_PUBLICAR", self.facade.conectar_firebase()[1])

    def test_production_and_unknown_environments_block_every_entry_point(self):
        for value in ("produccion", "producción", "prod", "staging", ""):
            with self.subTest(value=value):
                os.environ["ENTORNO"] = value
                self.assertIsNone(self.facade.conectar_firebase()[0])
                self.assertIsNone(self.selector.conectar_firebase()[0])
                with self.assertRaises(self.core.ErrorFirebaseDemo):
                    self.core.conectar_firebase_demo()
                self.assertIsNone(self.core.subir_archivo_demo(self.file(), "expedientes/1"))
        self.admin.initialize_app.assert_not_called()
        self.admin.firestore.client.assert_not_called()
        self.admin.storage.bucket.assert_not_called()

    def test_alternate_endpoints_fail_closed(self):
        for var in ("FIRESTORE_EMULATOR_HOST", "FIREBASE_STORAGE_EMULATOR_HOST", "STORAGE_EMULATOR_HOST"):
            with self.subTest(var=var), patch.dict(os.environ, {var: "localhost:9999"}):
                self.assertIsNone(self.facade.conectar_firebase()[0])
        self.admin.firestore.client.assert_not_called()

    def test_parallel_sessions_initialize_only_once(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.facade.conectar_firebase(), range(20)))
        self.assertTrue(all(result == (self.db, None) for result in results))
        self.admin.initialize_app.assert_called_once()

    def test_authentication_document_contract_is_preserved(self):
        user = {"password_hash": "hash-ficticio", "rol": "docente", "activo": True}
        doc = self.db.collection.return_value.document.return_value.get.return_value
        doc.exists = True
        doc.to_dict.return_value = user
        self.assertEqual(self.facade.obtener_usuario("docente.demo"), user)
        self.db.collection.assert_called_once_with("usuarios")
        self.db.collection.return_value.document.assert_called_once_with("docente.demo")
        self.db.collection.return_value.document.return_value.set.assert_not_called()

    def test_absent_user_returns_none(self):
        self.db.collection.return_value.document.return_value.get.return_value.exists = False
        self.assertIsNone(self.facade.obtener_usuario("ausente"))

    def test_user_read_error_returns_none(self):
        self.db.collection.side_effect = RuntimeError("SECRETO_NO_PUBLICAR")
        self.assertIsNone(self.facade.obtener_usuario("prueba"))

    def test_missing_bucket_blocks_upload_without_guessing(self):
        self.assertIsNone(self.facade.subir_archivo(self.file(), "expedientes/1"))
        self.admin.storage.bucket.assert_not_called()

    def test_other_buckets_rejected_before_storage_access(self):
        for name in ("gestioncbeh.appspot.com", "edumanager-demo.appspot.com.evil", "gs://edumanager-demo.appspot.com"):
            with self.subTest(name=name):
                os.environ["FIREBASE_DEMO_STORAGE_BUCKET"] = name
                self.assertIsNone(self.facade.subir_archivo(self.file(), "expedientes/1"))
        self.admin.storage.bucket.assert_not_called()

    def test_storage_rejects_reused_production_app(self):
        self.existing_app()
        self.app.project_id = "gestioncbeh"
        self.bucket()
        self.assertIsNone(self.facade.subir_archivo(self.file(), "expedientes/1"))
        self.admin.storage.bucket.assert_not_called()

    def test_unexpected_bucket_object_never_receives_upload(self):
        bucket = self.bucket()
        bucket.name = "gestioncbeh.appspot.com"
        self.assertIsNone(self.facade.subir_archivo(self.file(), "expedientes/1"))
        bucket.blob.assert_not_called()

    def test_allowed_buckets_upload_with_explicit_app_and_token(self):
        for name in sorted(self.core.BUCKETS_PERMITIDOS):
            with self.subTest(name=name):
                bucket = self.bucket(name)
                archivo = self.file("mi foto.png")
                url = self.facade.subir_archivo(archivo, "expedientes/1")
                self.admin.storage.bucket.assert_called_with(name=name, app=self.app)
                bucket.blob.return_value.upload_from_file.assert_called_once_with(archivo)
                token = bucket.blob.return_value.metadata["firebaseStorageDownloadTokens"]
                self.assertIn(f"/b/{name}/o/expedientes%2F1%2F", url)
                self.assertTrue(url.endswith(f"?alt=media&token={token}"))
                bucket.blob.return_value.patch.assert_not_called()

    def test_same_filename_gets_unique_object_names(self):
        bucket = self.bucket()
        self.facade.subir_archivo(self.file(), "expedientes/1")
        self.facade.subir_archivo(self.file(), "expedientes/1")
        names = [call.args[0] for call in bucket.blob.call_args_list]
        self.assertNotEqual(*names)

    def test_invalid_paths_block_upload(self):
        bucket = self.bucket()
        for filename, path in (("../foto", "expedientes"), ("a\\b", "expedientes"),
                               ("foto", "../otra"), ("foto", "a//b"), ("", "a"),
                               ("foto", ""), ("foto", "a\x00b")):
            with self.subTest(filename=filename, path=path):
                self.assertIsNone(self.facade.subir_archivo(self.file(filename), path))
        bucket.blob.assert_not_called()

    def test_upload_failure_is_sanitized(self):
        bucket = self.bucket()
        bucket.blob.return_value.upload_from_file.side_effect = RuntimeError("SECRETO_NO_PUBLICAR")
        self.assertIsNone(self.facade.subir_archivo(self.file(), "expedientes/1"))
        self.assertNotIn("SECRETO_NO_PUBLICAR", self.st.error.call_args.args[0])

    def test_no_file_is_a_noop(self):
        self.assertIsNone(self.facade.subir_archivo(None, "expedientes/1"))
        self.admin.get_app.assert_not_called()

    def test_local_configuration_check_does_not_read_or_write(self):
        self.assertEqual(self.core.verificar_conexion_demo(),
                         {"estado": "OK", "project_id": PROJECT, "entorno": "DEMO"})
        self.db.collection.assert_not_called()

    def test_sdk_initialization_only_exists_in_central_service(self):
        for path in ROOT.rglob("*.py"):
            if "tests" in path.parts or path.name == "firebase_demo_service.py":
                continue
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotEqual(node.func.attr, "initialize_app", str(path))
        for name in MODULES:
            tree = ast.parse((ROOT / f"{name}.py").read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("supabase", node.module or "")
                elif isinstance(node, ast.Import):
                    self.assertTrue(all("supabase" not in alias.name for alias in node.names))


if __name__ == "__main__":
    unittest.main()
