import html

import streamlit as st

from navigation import modules_for_role
from config import APP_NAME, CICLO_LECTIVO, LOGO_INSTITUCIONAL


def mostrar_sidebar(nombre_usuario, rol_usuario):
    """
    EduManager - Sidebar institucional (azul oscuro).

    Idea del diseño:
    - Fondo azul marino (el mismo azul del login).
    - Botones "planos": sin caja blanca, solo texto sobre el azul.
    - La opción activa lleva una barra dorada a la izquierda.
    - Íconos Material (:material/nombre:) en vez de emojis: todos del mismo estilo.
    """

    if "menu_actual" not in st.session_state:
        st.session_state["menu_actual"] = "Inicio"

    # --- Datos del usuario (html.escape evita que un nombre con "<" rompa la página)
    nombre_seguro = html.escape(str(nombre_usuario or "Usuario"))
    inicial = html.escape((str(nombre_usuario or "U").strip()[:1] or "U").upper())
    rol_texto = {"admin": "Administrador", "docente": "Docente"}.get(
        str(rol_usuario or "").lower(), str(rol_usuario or "Usuario").capitalize()
    )
    rol_seguro = html.escape(rol_texto)
    es_admin = str(rol_usuario or "").lower() == "admin"

    # ==========================================
    # PALETA (cambia aquí los colores y se actualiza todo el sidebar)
    # ==========================================
    FONDO_ARRIBA = "#0F2347"
    FONDO_ABAJO = "#142B4F"
    TEXTO = "#D6E2F5"  # texto normal de los botones
    TEXTO_SUAVE = "#8FA6C8"  # títulos de sección y detalles
    BLANCO = "#FFFFFF"
    DORADO = "#F2B544"  # acento (el mismo del login)
    HOVER = "rgba(255,255,255,0.08)"
    ACTIVO = "rgba(242,181,68,0.14)"
    LINEA = "rgba(255,255,255,0.12)"
    ROJO_TEXTO = "#FCA5A5"
    ROJO_FONDO = "rgba(239,68,68,0.12)"

    st.markdown(
        f"""
        <style>
        /* ---------- Fondo del sidebar ---------- */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {FONDO_ARRIBA} 0%, {FONDO_ABAJO} 100%) !important;
            border-right: 1px solid {LINEA} !important;
        }}
        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            background: transparent !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
        section[data-testid="stSidebar"] .block-container {{
            padding-top: 1.2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }}
        section[data-testid="stSidebar"] hr {{
            border-color: {LINEA} !important;
            margin: 14px 0 !important;
        }}

        /* ---------- Marca ---------- */
        section[data-testid="stSidebar"] [data-testid="stImage"] img,
        section[data-testid="stSidebar"] [data-testid="stImageContainer"] img {{
            aspect-ratio: 1 / 1;
            object-fit: contain;
        }}
        section[data-testid="stSidebar"] [data-testid="stImage"] img {{
            filter: drop-shadow(0 6px 12px rgba(0,0,0,0.35));
        }}
        .edu-brand-title {{
            color: {BLANCO} !important;
            font-size: 22px;
            font-weight: 800;
            text-align: center;
            letter-spacing: -0.3px;
            margin-top: 10px;
        }}
        .edu-brand-subtitle {{
            color: {TEXTO_SUAVE} !important;
            font-size: 9.5px;
            font-weight: 700;
            letter-spacing: 1.3px;
            text-align: center;
            text-transform: uppercase;
            margin-top: 3px;
        }}

        /* ---------- Tarjeta de usuario ---------- */
        .edu-user-card {{
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(255,255,255,0.06);
            border: 1px solid {LINEA};
            border-radius: 12px;
            padding: 12px 14px;
            margin: 4px 0 6px 0;
        }}
        .edu-avatar {{
            width: 38px;
            height: 38px;
            min-width: 38px;
            border-radius: 50%;
            background: {DORADO};
            color: {FONDO_ARRIBA};
            font-weight: 800;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .edu-user-name {{
            color: {BLANCO} !important;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.2;
        }}
        .edu-user-role {{
            color: {DORADO} !important;
            font-size: 11px;
            font-weight: 600;
            margin-top: 3px;
        }}

        /* ---------- Títulos de sección ---------- */
        .menu-section-title {{
            color: {TEXTO_SUAVE} !important;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.4px;
            text-transform: uppercase;
            padding-left: 6px;
            margin-top: 20px;
            margin-bottom: 6px;
        }}

        /* ---------- Botones del menú (planos) ---------- */
        section[data-testid="stSidebar"] .stButton > button {{
            width: 100% !important;
            min-height: 40px !important;
            background: transparent !important;
            border: none !important;
            border-left: 3px solid transparent !important;
            border-radius: 8px !important;
            box-shadow: none !important;
            padding: 8px 12px !important;
            margin-bottom: 2px !important;
            justify-content: flex-start !important;
            text-align: left !important;
            transition: background 0.2s ease !important;
        }}
        section[data-testid="stSidebar"] .stButton > button,
        section[data-testid="stSidebar"] .stButton > button * {{
            color: {TEXTO} !important;
            -webkit-text-fill-color: {TEXTO} !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            justify-content: flex-start !important;
            text-align: left !important;
        }}
        section[data-testid="stSidebar"] .stButton > button p {{
            margin: 0 !important;
        }}

        /* Hover */
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: {HOVER} !important;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover,
        section[data-testid="stSidebar"] .stButton > button:hover * {{
            color: {BLANCO} !important;
            -webkit-text-fill-color: {BLANCO} !important;
        }}

        /* Opción activa */
        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {{
            background: {ACTIVO} !important;
            border-left: 3px solid {DORADO} !important;
        }}
        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] *,
        section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"],
        section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] * {{
            color: {BLANCO} !important;
            -webkit-text-fill-color: {BLANCO} !important;
            font-weight: 700 !important;
        }}

        /* Cerrar sesión */
        section[data-testid="stSidebar"] .st-key-btn_logout_sidebar > button {{
            background: {ROJO_FONDO} !important;
            border: 1px solid rgba(239,68,68,0.35) !important;
            border-left: 1px solid rgba(239,68,68,0.35) !important;
        }}
        section[data-testid="stSidebar"] .st-key-btn_logout_sidebar > button,
        section[data-testid="stSidebar"] .st-key-btn_logout_sidebar > button * {{
            color: {ROJO_TEXTO} !important;
            -webkit-text-fill-color: {ROJO_TEXTO} !important;
            font-weight: 600 !important;
        }}
        section[data-testid="stSidebar"] .st-key-btn_logout_sidebar > button:hover {{
            background: rgba(239,68,68,0.22) !important;
        }}

        /* ---------- Pie ---------- */
        .edu-footer {{
            color: #6F86AB !important;
            text-align: center;
            font-size: 10.5px;
            line-height: 1.7;
            margin-top: 16px;
            padding-bottom: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ==========================================
    # CONSTRUCCIÓN DEL SIDEBAR
    # ==========================================
    with st.sidebar:
        # Logo centrado
        _, col_logo, _ = st.columns([1, 2, 1])
        with col_logo:
            try:
                st.image(LOGO_INSTITUCIONAL, use_container_width=True)
            except Exception:
                st.markdown(
                    "<div style='text-align:center;font-size:55px;'>🎓</div>",
                    unsafe_allow_html=True,
                )

        st.markdown(
            f"""
            <div class="edu-brand-title">{html.escape(APP_NAME)}</div>
            <div class="edu-brand-subtitle">Gestión Académica Institucional</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        st.markdown(
            f"""
            <div class="edu-user-card">
                <div class="edu-avatar">{inicial}</div>
                <div>
                    <div class="edu-user-name">{nombre_seguro}</div>
                    <div class="edu-user-role">{rol_seguro}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        def seccion(titulo):
            st.markdown(
                f'<div class="menu-section-title">{titulo}</div>',
                unsafe_allow_html=True,
            )

        def opcion_menu(texto, pagina, key):
            """Dibuja un botón del menú. Si es la página actual, se marca como 'primary'."""
            seleccionada = st.session_state["menu_actual"] == pagina
            if st.button(
                texto,
                key=key,
                type="primary" if seleccionada else "secondary",
                use_container_width=True,
            ):
                st.session_state["menu_actual"] = pagina
                st.rerun()

        seccion_actual = None
        for modulo in modules_for_role(rol_usuario):
            seccion_modulo = modulo.section
            if modulo.name == "Mi Perfil" and es_admin:
                seccion_modulo = "Sistema"
            if seccion_modulo != seccion_actual:
                seccion(seccion_modulo)
                seccion_actual = seccion_modulo
            opcion_menu(modulo.label, modulo.name, modulo.key)

        st.markdown("---")
        cerrar_sesion = st.button(
            ":material/logout:  Cerrar sesión",
            key="btn_logout_sidebar",
            type="secondary",
            use_container_width=True,
        )
        if cerrar_sesion:
            return "__logout__"

        st.markdown(
            f"""
            <div class="edu-footer">
                © 2026 David Fuentes - EduManager<br>
                Ciclo lectivo {CICLO_LECTIVO} · DEMO
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["menu_actual"]
