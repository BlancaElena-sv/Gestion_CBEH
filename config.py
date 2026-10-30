import logging

import pytz
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

# ==========================================
# CONFIGURACIÓN GENERAL DE EDUMANAGER
# ==========================================
APP_NAME = "EduManager"
COLEGIO_NOMBRE = "Colegio Profa. Blanca Elena de Hernández"
CICLO_LECTIVO = 2026
TZ_SV = pytz.timezone("America/El_Salvador")

# ==========================================
# CONFIGURACIÓN DE SUPABASE
# ==========================================
SUPABASE_URL = "https://hzqkmecrtimroiqaqpss.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6cWttZWNydGltcm9pcWFxcHNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxNTA2MDAsImV4cCI6MjEwODcyNjYwMH0.RQEsbyM7fKqPsoSZXpOxg_puW6G2PlPOBcNJ3kqYHm8"

# Para Streamlit Cloud (opcional, leerá desde st.secrets si existe)
try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except StreamlitSecretNotFoundError:
    logging.getLogger(__name__).warning(
        "No se encontraron secrets de Streamlit; se usarán los valores locales."
    )
