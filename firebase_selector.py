"""Imports compatibles: esta rama nunca selecciona un backend de producción.

La validación de ENTORNO ocurre al conectar o subir un archivo.
"""

from firebase_service import conectar_firebase, obtener_usuario, subir_archivo

__all__ = ["conectar_firebase", "obtener_usuario", "subir_archivo"]
