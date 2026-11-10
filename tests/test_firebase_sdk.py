"""Compatibilidad con SDK reales usando claves efímeras y sin tráfico remoto."""

import importlib.util
import os
import socket
import unittest
from unittest.mock import patch

AVAILABLE = all(importlib.util.find_spec(name) is not None for name in
                ("firebase_admin", "streamlit", "bcrypt", "cryptography"))


@unittest.skipUnless(AVAILABLE, "Instale requirements.txt para comprobar SDK y bcrypt reales")
class RealSdkTests(unittest.TestCase):
    def setUp(self):
        import firebase_admin
        from firebase_admin import credentials
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import firebase_demo_service as core

        self.core = core
        self.admin = firebase_admin
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        guard = patch.object(socket.socket, "connect", side_effect=AssertionError("Red prohibida"))
        guard.start()
        self.addCleanup(guard.stop)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(serialization.Encoding.PEM,
                               serialization.PrivateFormat.PKCS8,
                               serialization.NoEncryption()).decode()
        self.credential = credentials.Certificate({
            "type": "service_account",
            "project_id": "edumanager-demo",
            "private_key": pem,
            "client_email": "test@edumanager-demo.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        # Clave generada en memoria: nunca se carga un archivo o secret real.
        loader = patch.object(core, "_cargar_credenciales", return_value=self.credential)
        loader.start()
        self.addCleanup(loader.stop)
        self.addCleanup(self.remove_app)

    def remove_app(self):
        try:
            self.admin.delete_app(self.admin.get_app(self.core.NOMBRE_APP_FIREBASE))
        except ValueError:
            pass

    def test_real_sdk_builds_and_reuses_only_named_demo_client(self):
        db, error = self.core.conectar_firebase_demo()
        self.assertIsNone(error)
        self.assertEqual(db.project, "edumanager-demo")
        self.assertIs(db, self.core.conectar_firebase_demo()[0])
        app = self.admin.get_app("edumanager_demo")
        self.assertEqual(app.credential.project_id, "edumanager-demo")
        with self.assertRaises(ValueError):
            self.admin.get_app()

    def test_real_storage_resolves_explicit_demo_bucket_without_upload(self):
        from firebase_admin import storage
        self.core.conectar_firebase_demo()
        app = self.admin.get_app("edumanager_demo")
        for name in self.core.BUCKETS_PERMITIDOS:
            self.assertEqual(storage.bucket(name=name, app=app).name, name)

    def test_existing_bcrypt_authentication_is_unchanged(self):
        from auth import generar_hash, verificar_password
        hashed = generar_hash("prueba-efimera")
        self.assertTrue(verificar_password("prueba-efimera", hashed))
        self.assertFalse(verificar_password("incorrecta", hashed))
        self.assertFalse(verificar_password("prueba-efimera", "hash-invalido"))

    def test_app_stops_cleanly_when_demo_connection_is_rejected(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest

        app_file = Path(__file__).resolve().parents[1] / "app.py"
        with patch.object(self.core, "_cargar_credenciales",
                          side_effect=self.core.ErrorFirebaseDemo("Conexión DEMO rechazada")):
            app = AppTest.from_file(str(app_file)).run(timeout=10)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertIn("Conexión DEMO rechazada", app.error[0].value)
        self.assertEqual(len(app.text_input), 0)


if __name__ == "__main__":
    unittest.main()
