import os
import uuid
import urllib.parse

import streamlit as st
import firebase_admin

from firebase_admin import credentials, firestore, storage


# ============================================================
# CONFIGURACIÓN EXCLUSIVA DE EDUManager DEMO
# ============================================================

ARCHIVO_CREDENCIALES = "credenciales_demo.json"
PROJECT_ID_DEMO = "edumanager-demo"
NOMBRE_APP_FIREBASE = "edumanager_demo"


def conectar_firebase_demo():
    """
    Conecta exclusivamente con el proyecto Firebase
    utilizado para EduManager DEMO.

    Fuentes de credenciales (en orden de prioridad):
    1. Archivo local 'credenciales_demo.json' (desarrollo)
    2. Secrets de Streamlit Cloud, sección [firebase_demo] (producción)
    """

    # --------------------------------------------------------
    # 1. Intentar con archivo local
    # --------------------------------------------------------

    cred = None

    if os.path.exists(ARCHIVO_CREDENCIALES):
        cred = credentials.Certificate(ARCHIVO_CREDENCIALES)

    # --------------------------------------------------------
    # 2. Si no hay archivo, intentar con Secrets de Streamlit
    # --------------------------------------------------------

    elif "firebase_demo" in st.secrets:
        credenciales_dict = dict(st.secrets["firebase_demo"])

        # Firebase necesita saltos de línea reales en private_key
        if "private_key" in credenciales_dict:
            credenciales_dict["private_key"] = (
                credenciales_dict["private_key"].replace("\\n", "\n")
            )

        cred = credentials.Certificate(credenciales_dict)

    # --------------------------------------------------------
    # 3. Si no hay ni archivo ni secrets, error claro
    # --------------------------------------------------------

    else:
        raise FileNotFoundError(
            "No se encontraron credenciales para la DEMO.\n"
            "En local: agrega credenciales_demo.json en la raíz.\n"
            "En Streamlit Cloud: agrega la sección [firebase_demo] "
            "en los Secrets de la app."
        )

    # --------------------------------------------------------
    # 4. Validar que sea el proyecto DEMO
    # --------------------------------------------------------

    project_id = cred.project_id

    if project_id != PROJECT_ID_DEMO:
        raise RuntimeError(
            "\n"
            "====================================================\n"
            "OPERACIÓN CANCELADA POR SEGURIDAD\n"
            "====================================================\n"
            f"Proyecto detectado: {project_id}\n"
            f"Proyecto permitido: {PROJECT_ID_DEMO}\n\n"
            "Las credenciales NO pertenecen a EduManager DEMO.\n"
            "===================================================="
        )

    # --------------------------------------------------------
    # 3. PROTECCIÓN CRÍTICA
    # --------------------------------------------------------

    if project_id != PROJECT_ID_DEMO:
        raise RuntimeError(
            "\n"
            "====================================================\n"
            "OPERACIÓN CANCELADA POR SEGURIDAD\n"
            "====================================================\n"
            f"Proyecto detectado: {project_id}\n"
            f"Proyecto permitido: {PROJECT_ID_DEMO}\n\n"
            "Las credenciales NO pertenecen a EduManager DEMO.\n"
            "No se realizará ninguna operación.\n"
            "===================================================="
        )

    # --------------------------------------------------------
    # 4. Crear/reutilizar aplicación Firebase independiente
    # --------------------------------------------------------

    try:
        app_demo = firebase_admin.get_app(NOMBRE_APP_FIREBASE)

    except ValueError:
        app_demo = firebase_admin.initialize_app(
            cred,
            name=NOMBRE_APP_FIREBASE,
        )

    # --------------------------------------------------------
    # 5. Obtener Firestore asociado específicamente a DEMO
    # --------------------------------------------------------

    db_demo = firestore.client(app=app_demo)

    return db_demo, None

def subir_archivo_demo(archivo, ruta):
    """
    Sube archivos exclusivamente al Storage
    del proyecto EduManager DEMO.
    """

    if not archivo:
        return None

    try:
        # Obtener exclusivamente la app Firebase DEMO
        app_demo = firebase_admin.get_app(
            NOMBRE_APP_FIREBASE
        )

        # Obtener el bucket asociado a esa app
        bucket = storage.bucket(
            app=app_demo
        )

        nombre_archivo = archivo.name.replace(
            " ",
            "_",
        )

        blob_name = f"{ruta}/{nombre_archivo}"

        blob = bucket.blob(blob_name)

        blob.upload_from_file(archivo)

        token = str(uuid.uuid4())

        blob.metadata = {
            "firebaseStorageDownloadTokens": token
        }

        blob.patch()

        url = (
            "https://firebasestorage.googleapis.com/v0/b/"
            f"{bucket.name}/o/"
            f"{urllib.parse.quote(blob_name, safe='')}"
            f"?alt=media&token={token}"
        )

        return url

    except Exception as error:
        st.error(
            f"Error al subir archivo DEMO: {error}"
        )
        return None

def verificar_conexion_demo():
    """
    Comprueba la configuración sin escribir datos en Firestore.
    """

    db_demo, error = conectar_firebase_demo()
    if error:
        raise RuntimeError(
            "No se pudo establecer la conexión DEMO.\n"
            f"Error: {error}"
        )

    project_id = db_demo.project

    if project_id != PROJECT_ID_DEMO:
        raise RuntimeError(
            "La conexión obtenida no corresponde "
            "al proyecto DEMO autorizado."
        )

    return {
        "estado": "OK",
        "project_id": project_id,
        "entorno": "DEMO",
    }


if __name__ == "__main__":

    print()
    print("=" * 60)
    print("EDUMANAGER - VERIFICACIÓN DE FIREBASE DEMO")
    print("=" * 60)

    try:
        resultado = verificar_conexion_demo()

        print()
        print("Conexión correcta.")
        print(f"Entorno: {resultado['entorno']}")
        print(f"Proyecto: {resultado['project_id']}")
        print()
        print("No se escribió ningún dato en Firestore.")

    except Exception as error:

        print()
        print("ERROR DE SEGURIDAD O CONEXIÓN")
        print()
        print(error)

    print()
    print("=" * 60)