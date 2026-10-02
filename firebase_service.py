import os
import streamlit as st
import firebase_admin

from firebase_admin import credentials, firestore, storage

from config import FIREBASE_PROJECT_ID


@st.cache_resource
def conectar_firebase():
    """
    Inicializa Firebase Admin SDK para PRODUCCIÓN
    y devuelve una conexión a Firestore.
    """

    try:
        if not firebase_admin._apps:
            cred = obtener_credenciales()

            if cred is None:
                return None, "No se encontraron credenciales de Firebase."

            firebase_admin.initialize_app(
                cred,
                {
                    "storageBucket": f"{FIREBASE_PROJECT_ID}.firebasestorage.app"
                }
            )

        db = firestore.client()

        return db, None

    except Exception as error:
        return None, str(error)


def obtener_credenciales():
    """
    Busca las credenciales de Firebase para PRODUCCIÓN.
    """

    if os.path.exists("credenciales.json"):
        return credentials.Certificate("credenciales.json")

    if os.path.exists("credenciales"):
        return credentials.Certificate("credenciales")

    if "firebase_key" in st.secrets:
        credenciales_dict = dict(st.secrets["firebase_key"])
        if "private_key" in credenciales_dict:
            credenciales_dict["private_key"] = (
                credenciales_dict["private_key"].replace("\\n", "\n")
            )
        return credentials.Certificate(credenciales_dict)

    return None


def obtener_bucket():
    """
    Devuelve el bucket de Firebase Storage.
    """

    try:
        return storage.bucket()
    except Exception:
        return None

import uuid
import urllib.parse

def subir_archivo(archivo, ruta):
    """
    Sube un archivo a Firebase Storage
    y devuelve su URL de acceso.
    """

    if not archivo:
        return None

    try:
        bucket = storage.bucket()

        nombre_archivo = archivo.name.replace(" ", "_")
        blob_name = f"{ruta}/{nombre_archivo}"

        blob = bucket.blob(blob_name)

        blob.upload_from_file(archivo)

        token = str(uuid.uuid4())

        blob.metadata = {
            "firebaseStorageDownloadTokens": token
        }

        blob.patch()

        url = (
            f"https://firebasestorage.googleapis.com/v0/b/"
            f"{bucket.name}/o/"
            f"{urllib.parse.quote(blob_name, safe='')}"
            f"?alt=media&token={token}"
        )

        return url

    except Exception as error:
        st.error(f"Error al subir archivo: {error}")
        return None