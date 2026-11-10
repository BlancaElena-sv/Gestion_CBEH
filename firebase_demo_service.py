"""Única conexión Firebase de esta rama: exclusivamente EduManager DEMO."""

import os
import threading
import urllib.parse
import uuid

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore, storage

ARCHIVO_CREDENCIALES = "credenciales_demo.json"
PROJECT_ID_DEMO = "edumanager-demo"
NOMBRE_APP_FIREBASE = "edumanager_demo"
BUCKETS_PERMITIDOS = frozenset({
    "edumanager-demo.appspot.com",
    "edumanager-demo.firebasestorage.app",
})
_APP_LOCK = threading.RLock()


class ErrorFirebaseDemo(RuntimeError):
    """Error seguro para mostrar, sin contenido de credenciales o del SDK."""


def _validar_entorno():
    if os.environ.get("ENTORNO", "demo").strip().lower() != "demo":
        raise ErrorFirebaseDemo("Esta aplicación solo admite ENTORNO=demo.")
    for variable in (
        "FIRESTORE_EMULATOR_HOST",
        "FIREBASE_STORAGE_EMULATOR_HOST",
        "STORAGE_EMULATOR_HOST",
    ):
        if os.environ.get(variable):
            raise ErrorFirebaseDemo("Endpoint Firebase alternativo no autorizado.")


def _cargar_credenciales():
    try:
        if os.path.exists(ARCHIVO_CREDENCIALES):
            cred = credentials.Certificate(ARCHIVO_CREDENCIALES)
        elif "firebase_demo" in st.secrets:
            datos = dict(st.secrets["firebase_demo"])
            if "private_key" in datos:
                datos["private_key"] = datos["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(datos)
        else:
            raise ErrorFirebaseDemo(
                "Faltan credenciales DEMO: use credenciales_demo.json "
                "o la sección firebase_demo de Streamlit Secrets."
            )
        if cred.project_id != PROJECT_ID_DEMO:
            raise ErrorFirebaseDemo("Credenciales rechazadas: proyecto distinto de edumanager-demo.")
        return cred
    except ErrorFirebaseDemo:
        raise
    except Exception:
        raise ErrorFirebaseDemo("No se pudieron cargar las credenciales DEMO.") from None


def _obtener_app_demo():
    _validar_entorno()
    with _APP_LOCK:
        try:
            app = firebase_admin.get_app(NOMBRE_APP_FIREBASE)
        except ValueError:
            cred = _cargar_credenciales()
            app = firebase_admin.initialize_app(
                cred,
                options={"projectId": PROJECT_ID_DEMO},
                name=NOMBRE_APP_FIREBASE,
            )
        # Validar también al reutilizar: nunca confiar solo en el nombre.
        if (
            app.project_id != PROJECT_ID_DEMO
            or app.credential.project_id != PROJECT_ID_DEMO
        ):
            raise ErrorFirebaseDemo("Aplicación Firebase rechazada: proyecto no autorizado.")
        return app


def conectar_firebase_demo():
    """Devuelve (cliente, None); falla cerrado sin recurrir a otra conexión.

    Conserva el contrato DEMO de generar excepción en caso de error.
    La fachada firebase_service conserva (None, error) para app.py.
    Inicializar el cliente no comprueba conectividad remota ni permisos IAM.
    """
    try:
        app = _obtener_app_demo()
        db = firestore.client(app=app)
        if db.project != PROJECT_ID_DEMO:
            raise ErrorFirebaseDemo("Cliente Firestore rechazado: proyecto no autorizado.")
        return db, None
    except ErrorFirebaseDemo:
        raise
    except Exception:
        raise ErrorFirebaseDemo("No se pudo inicializar Firebase DEMO.") from None


def _nombre_objeto(archivo, ruta):
    if not isinstance(ruta, str) or not ruta.strip("/"):
        raise ErrorFirebaseDemo("Ruta de archivo no válida.")
    carpeta = ruta.strip("/")
    nombre = str(archivo.name).replace(" ", "_")
    partes = carpeta.split("/") + [nombre]
    if any(
        not parte or parte in {".", ".."} or "\\" in parte
        or any(ord(caracter) < 32 for caracter in parte)
        for parte in partes
    ) or "/" in nombre:
        raise ErrorFirebaseDemo("Ruta de archivo no válida.")
    return f"{carpeta}/{uuid.uuid4().hex}_{nombre}"


def subir_archivo_demo(archivo, ruta):
    """Sube solo a un bucket DEMO explícito; conserva URL o None como retorno."""
    if archivo is None:
        return None
    try:
        app = _obtener_app_demo()
        bucket_name = os.environ.get("FIREBASE_DEMO_STORAGE_BUCKET", "").strip()
        if not bucket_name:
            raise ErrorFirebaseDemo("Configure FIREBASE_DEMO_STORAGE_BUCKET para habilitar archivos DEMO.")
        if bucket_name not in BUCKETS_PERMITIDOS:
            raise ErrorFirebaseDemo("Bucket rechazado: almacenamiento ajeno a DEMO.")
        objeto = _nombre_objeto(archivo, ruta)
        bucket = storage.bucket(name=bucket_name, app=app)
        if bucket.name != bucket_name:
            raise ErrorFirebaseDemo("Bucket Firebase recibido no autorizado.")
        blob = bucket.blob(objeto)
        token = str(uuid.uuid4())
        # Metadatos en la misma subida, sin patch posterior.
        blob.metadata = {"firebaseStorageDownloadTokens": token}
        blob.upload_from_file(archivo)
        return (
            "https://firebasestorage.googleapis.com/v0/b/"
            f"{bucket.name}/o/{urllib.parse.quote(objeto, safe='')}"
            f"?alt=media&token={token}"
        )
    except ErrorFirebaseDemo as error:
        st.error(str(error))
        return None
    except Exception:
        st.error("No se pudo subir el archivo a Firebase DEMO.")
        return None


def verificar_conexion_demo():
    """Valida configuración local, sin leer ni escribir documentos remotos."""
    db, _ = conectar_firebase_demo()
    return {"estado": "OK", "project_id": db.project, "entorno": "DEMO"}


if __name__ == "__main__":
    try:
        print(verificar_conexion_demo())
        print("Configuración validada; conectividad remota no comprobada.")
    except ErrorFirebaseDemo as error:
        print(str(error))
        raise SystemExit(1)
