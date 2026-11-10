import firebase_admin
from firebase_admin import credentials, firestore


def conectar_firebase():
    """
    Conecta con Firebase Firestore.
    Retorna: (db, error)
    """
    try:
        cred = credentials.Certificate("credenciales_demo.json")
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        return db, None
    except Exception as e:
        return None, str(e)


def obtener_usuario(usuario):
    """
    Obtiene un usuario de la colección 'usuarios' en Firebase.
    """
    try:
        db, _ = conectar_firebase()
        doc = db.collection("usuarios").document(usuario).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception:
        return None
