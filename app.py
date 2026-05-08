# ============================================================
# REEMPLAZA COMPLETAMENTE LA SECCIÓN "4. BARRA LATERAL"
# de tu archivo principal de EduManager
# ============================================================
#
# También agrega st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
# justo DESPUÉS de st.set_page_config(...)
# ============================================================

# ── 1. CSS (pégalo como variable global, antes del login) ──────────

SIDEBAR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {
    --azul:   #1E3A8A;
    --acento: #F59E0B;
    --blanco: #F8FAFC;
}

/* Sidebar fondo degradado */
[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #1a3276 0%, #1e3a8a 45%, #1d4ed8 100%) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem !important;
}

/* Tipografía global sidebar */
[data-testid="stSidebar"],
[data-testid="stSidebar"] * {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Chip de usuario */
.user-chip {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 10px 12px;
    margin: 6px 0 16px 0;
    border: 1px solid rgba(255,255,255,0.12);
}
.user-avatar {
    width: 38px; height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, #F59E0B, #fbbf24);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 16px;
    color: #1E3A8A !important;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(245,158,11,0.4);
}
.user-name {
    font-size: 13px; font-weight: 700;
    color: #fff !important; line-height: 1.2;
}
.user-role {
    font-size: 11px;
    color: rgba(255,255,255,0.5) !important;
    text-transform: capitalize; letter-spacing: 0.3px;
}

/* Etiqueta de sección */
.nav-section-label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.35) !important;
    padding: 12px 4px 5px 4px;
    display: block;
}

/* Botones de navegación */
div[data-testid="stSidebar"] .stButton > button {
    display: flex !important;
    align-items: center !important;
    gap: 9px !important;
    width: 100% !important;
    padding: 9px 13px !important;
    margin: 1px 0 !important;
    border: none !important;
    border-radius: 10px !important;
    background: transparent !important;
    color: rgba(255,255,255,0.7) !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.13) !important;
    color: #fff !important;
    transform: translateX(3px) !important;
}

/* Botón ACTIVO — clase especial */
div[data-testid="stSidebar"] .nav-active .stButton > button {
    background: rgba(255,255,255,0.17) !important;
    color: #fff !important;
    font-weight: 700 !important;
    box-shadow: inset 3px 0 0 #F59E0B !important;
}

/* Botón cerrar sesión */
div[data-testid="stSidebar"] .btn-logout .stButton > button {
    background: rgba(239,68,68,0.12) !important;
    color: #fca5a5 !important;
    border: 1px solid rgba(239,68,68,0.25) !important;
    margin-top: 4px !important;
}
div[data-testid="stSidebar"] .btn-logout .stButton > button:hover {
    background: rgba(239,68,68,0.28) !important;
    color: #fff !important;
    transform: none !important;
}

/* HR */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
    margin: 8px 0 !important;
}

/* Caption footer */
[data-testid="stSidebar"] .stCaption p {
    color: rgba(255,255,255,0.25) !important;
    font-size: 10px !important;
    text-align: center !important;
}

/* Logo */
[data-testid="stSidebar"] img {
    border-radius: 10px;
}

/* Tipografía app principal */
[data-testid="stAppViewContainer"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
</style>
"""

# ── 2. SECCIÓN 4 COMPLETA — reemplaza el bloque "with st.sidebar:" ──

# Menús
MENU_ADMIN = [
    ("🏠", "Inicio"),
    ("📝", "Inscripción"),
    ("🔎", "Consulta Alumnos"),
    ("👩‍🏫", "Maestros"),
    ("📅", "Asistencia Global"),
    ("📊", "Notas"),
    ("💰", "Finanzas"),
    ("⚙️", "Configuración (Usuarios)"),
]

MENU_DOCENTE = [
    ("🏠", "Inicio"),
    ("🖨️", "Mis Listados"),
    ("📅", "Tomar Asistencia"),
    ("📝", "Cargar Notas"),
    ("📋", "Ver Mis Cargas"),
    ("📂", "Expediente Alumnos"),
    ("📄", "Boletas de Notas"),
]

# Inicializar página seleccionada
if "opcion_seleccionada" not in st.session_state:
    st.session_state["opcion_seleccionada"] = "Inicio"

# Inyectar CSS
st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)

with st.sidebar:
    # Logo
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.markdown("🎓")

    # Chip de usuario
    nombre_mostrar = limpiar_nombre(st.session_state.get("user_name", "Usuario"))
    rol_display    = st.session_state.get("user_role", "")
    inicial        = nombre_mostrar[0].upper() if nombre_mostrar else "U"

    st.markdown(f"""
        <div class="user-chip">
            <div class="user-avatar">{inicial}</div>
            <div>
                <div class="user-name">{nombre_mostrar}</div>
                <div class="user-role">{rol_display}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Seleccionar menú según rol
    menu = MENU_ADMIN if st.session_state["user_role"] == "admin" else MENU_DOCENTE

    # Etiqueta de sección
    st.markdown('<span class="nav-section-label">Navegación</span>', unsafe_allow_html=True)

    # Renderizar ítems de menú
    for icon, label in menu:
        is_active = st.session_state["opcion_seleccionada"] == label
        # Envolver en div con clase nav-active si está activo
        if is_active:
            st.markdown('<div class="nav-active">', unsafe_allow_html=True)

        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
            if st.session_state["opcion_seleccionada"] != label:
                # Limpiar estados de página al navegar
                keys_to_clear = [
                    "alum_view", "recibo", "pa", "recibo_temp",
                    "pago_alum", "prof_view", "sel_prof_idx",
                    "edit_prof_mode", "gasto_temp", "last_page"
                ]
                for k in keys_to_clear:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state["opcion_seleccionada"] = label
                st.rerun()

        if is_active:
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Botón cerrar sesión
    st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
    if st.button("🚪  Cerrar Sesión", use_container_width=True, key="btn_logout"):
        logout()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("© 2026 David Fuentes | EduManager")

# Esta variable la usa todo el resto del código — sin cambios necesarios
opcion_seleccionada = st.session_state["opcion_seleccionada"]

# ── FIN DE LA SECCIÓN 4 ──────────────────────────────────────────────
#
# IMPORTANTE: Elimina también el bloque "if 'last_page' not in st.session_state..."
# que venía después del radio original, ya que la limpieza de estado
# ahora ocurre dentro de cada botón de navegación.
# ─────────────────────────────────────────────────────────────────