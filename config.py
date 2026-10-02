import os
import pytz


# ==========================================
# CONFIGURACIÓN GENERAL DE EDUMANAGER
# ==========================================
# Detecta el entorno en runtime:
#   ENTORNO=demo       → EduManager DEMO (ciclo 2027)
#   ENTORNO=produccion → EduManager producción (ciclo 2026)
#   sin ENTORNO        → fallback a demo (para no romper)
# ==========================================

_ENTORNO_RAW = os.environ.get("ENTORNO", "demo").strip().lower()

if _ENTORNO_RAW in ("produccion", "producción", "prod"):
    ENTORNO = "PRODUCCION"
    ES_DEMO = False
else:
    ENTORNO = "DEMO"
    ES_DEMO = True


# ==========================================
# CONFIGURACIÓN POR ENTORNO
# ==========================================

if ES_DEMO:

    APP_NAME = "EduManager DEMO"

    COLEGIO_NOMBRE = "Centro Educativo Nuevo Horizonte"

    CICLO_LECTIVO = 2027

    LOGO_INSTITUCIONAL = "logo_demo.png"
    SELLO_INSTITUCIONAL = "sello_demo.png"

    FIREBASE_PROJECT_ID = "edumanager-demo"

else:

    APP_NAME = "EduManager"

    COLEGIO_NOMBRE = "Colegio Profa. Blanca Elena de Hernández"

    CICLO_LECTIVO = 2026

    LOGO_INSTITUCIONAL = "logo.png"
    SELLO_INSTITUCIONAL = "sello.png"

    FIREBASE_PROJECT_ID = "gestioncbeh"


# ==========================================
# CONFIGURACIÓN COMÚN
# ==========================================

TZ_SV = pytz.timezone("America/El_Salvador")