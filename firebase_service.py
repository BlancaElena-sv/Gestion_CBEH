"""Fachada compatible para app.py y herramientas existentes, solo Firebase DEMO."""

from firebase_demo_service import (
    ErrorFirebaseDemo,
    conectar_firebase_demo,
    subir_archivo_demo as subir_archivo,
)


def conectar_firebase():
    """Conserva el contrato (db, error), sin conexiones de respaldo."""
    try:
        return conectar_firebase_demo()
    except ErrorFirebaseDemo as error:
        return None, str(error)


def obtener_usuario(usuario):
    """Conserva usuarios/<usuario> y su password_hash existente."""
    db, error = conectar_firebase()
    if error:
        return None
    try:
        doc = db.collection("usuarios").document(usuario).get()
        return doc.to_dict() if doc.exists else None
    except Exception:
        return None
