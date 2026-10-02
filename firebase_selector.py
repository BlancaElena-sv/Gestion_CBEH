"""
Selector de servicio Firebase según el entorno.

- ENTORNO=demo       → usa firebase_demo_service
- ENTORNO=produccion → usa firebase_service

Este módulo es lo único que app.py necesita importar.
"""

from config import ES_DEMO


if ES_DEMO:
    # Entorno DEMO
    from firebase_demo_service import (
        conectar_firebase_demo as conectar_firebase,
        subir_archivo_demo as subir_archivo,
    )
    print("[Firebase] Modo DEMO activo (edumanager-demo)")

else:
    # Entorno PRODUCCIÓN
    from firebase_service import (
        conectar_firebase,
        subir_archivo,
    )
    print("[Firebase] Modo PRODUCCIÓN activo (gestioncbeh)")