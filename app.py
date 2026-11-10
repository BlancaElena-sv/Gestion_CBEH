import html
from datetime import datetime

import streamlit as st

from components.sidebar import mostrar_sidebar
from config import APP_NAME, TZ_SV, COLEGIO_NOMBRE, LOGO_INSTITUCIONAL
from styles import aplicar_estilos
from authorization import AccessDenied, authorize
from view_dispatch import render_module
from views.dashboard import (
    mostrar_dashboard_admin,
    mostrar_dashboard_docente,
)

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title=APP_NAME, layout="wide", page_icon="🎓", initial_sidebar_state="expanded"
)

# ==========================================
# 1. CONEXIÓN A FIREBASE
# ==========================================
from firebase_service import conectar_firebase, obtener_usuario

db, db_error = conectar_firebase()
if db_error:
    st.error(f"❌ Error de conexión con Firebase: {db_error}")
    st.stop()

# ==========================================
# 2. GESTIÓN DE SESIÓN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None


# ==========================================
# 3. FUNCIONES AUXILIARES
# ==========================================
def obtener_fecha_hoy():
    return datetime.now(TZ_SV).date()


def obtener_hora_actual():
    return datetime.now(TZ_SV).strftime("%d/%m/%Y %H:%M")


def limpiar_nombre(nombre):
    if not nombre:
        return ""
    return nombre.replace("*", "").replace("_", " ").strip()


# ==========================================
# 4. FUNCIÓN LOGIN CON CSS MODERNO
# ==========================================
def login():
    # ==========================================
    # EDUMANAGER - LOGIN INSTITUCIONAL PREMIUM
    # ==========================================
    st.markdown(
        """
        <style>
            /* ==========================================
               1. FONDO INSTITUCIONAL
            ========================================== */

            .stApp {
                background:
                    radial-gradient(
                        circle at 85% 15%,
                        rgba(59, 130, 246, 0.22),
                        transparent 35%
                    ),
                    linear-gradient(
                        135deg,
                        #142B4F 0%,
                        #193B70 55%,
                        #2457A6 100%
                    ) !important;
                background-attachment: fixed !important;
                min-height: 100vh;
            }

            /* Contenedores intermedios transparentes para que se vea el degradado */
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                background: transparent !important;
            }

            /* Ocultar encabezado Streamlit */
            header[data-testid="stHeader"] {
                display: none !important;
            }

            /* Eliminar espacios superiores innecesarios */
            .block-container {
                padding-top: 2rem !important;
                padding-bottom: 1rem !important;
            }

            /* ==========================================
               2. TARJETA DE ACCESO
            ========================================== */

            .stForm {
                background: #F8FAFC !important;
                border: 1px solid rgba(255,255,255,0.65) !important;
                border-radius: 22px !important;
                padding: 35px 32px !important;
                box-shadow:
                    0 20px 55px rgba(0,0,0,0.25),
                    0 0 0 1px rgba(255,255,255,0.08) !important;
                max-width: 450px !important;
                margin: 0 auto !important;
                animation: slideUp 0.6s ease-out !important;
            }

            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(25px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            /* ==========================================
               3. LOGO INSTITUCIONAL
            ========================================== */

            .stImage img,
            [data-testid="stImageContainer"] img {
                aspect-ratio: 1 / 1;
                object-fit: contain;
            }

            .stImage img {
                filter: drop-shadow(
                    0 8px 16px rgba(0,0,0,0.25)
                ) !important;
                animation: fadeIn 0.9s ease-out;
            }

            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: scale(0.92);
                }
                to {
                    opacity: 1;
                    transform: scale(1);
                }
            }

            /* ==========================================
               4. TÍTULO EDUMANAGER
            ========================================== */

            h1 {
                color: #FFFFFF !important;
                background: none !important;
                -webkit-text-fill-color: #FFFFFF !important;
                font-size: 2.8rem !important;
                font-weight: 800 !important;
                text-align: center !important;
                letter-spacing: -0.8px !important;
                text-shadow: 0 2px 14px rgba(0, 0, 0, 0.35) !important;
                margin-top: 12px !important;
                margin-bottom: 5px !important;
            }

            .login-subtitle {
                color: #FFFFFF !important;
                text-align: center;
                font-size: 19px;
                font-weight: 600;
                letter-spacing: 0.3px;
                text-shadow: 0 1px 8px rgba(0, 0, 0, 0.3);
                margin-top: 8px;
                margin-bottom: 25px;
            }

            .login-divider {
                width: 55px;
                height: 3px;
                background: #F2B544;
                border-radius: 5px;
                margin: 12px auto 22px auto;
            }

            /* ==========================================
               5. CAMPOS DE TEXTO
            ========================================== */

            .stTextInput input {
                background: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
                border-radius: 10px !important;
                padding: 13px 15px !important;
                color: #142B4F !important;
                font-size: 15px !important;
                transition: all 0.25s ease !important;
            }

            .stTextInput input:focus {
                border-color: #2457A6 !important;
                box-shadow:
                    0 0 0 3px rgba(36,87,166,0.13) !important;
                outline: none !important;
            }

            .stTextInput label {
                color: #334155 !important;
                font-weight: 600 !important;
                font-size: 14px !important;
            }

            /* Iconos de los campos */
            .stTextInput button {
                color: #475569 !important;
            }

            /* ==========================================
               6. BOTÓN INICIAR SESIÓN
            ========================================== */

            .stForm button[kind="primary"] {
                background: linear-gradient(
                    135deg,
                    #E34B4B 0%,
                    #C92F3B 100%
                ) !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 10px !important;
                padding: 13px 20px !important;
                font-size: 15px !important;
                font-weight: 700 !important;
                letter-spacing: 0.4px !important;
                transition: all 0.3s ease !important;
                box-shadow:
                    0 5px 15px rgba(201,47,59,0.25) !important;
                width: 100% !important;
            }

            .stForm button[kind="primary"]:hover {
                background: linear-gradient(
                    135deg,
                    #EF5555 0%,
                    #B91C35 100%
                ) !important;
                transform: translateY(-2px) !important;
                box-shadow:
                    0 8px 20px rgba(201,47,59,0.35) !important;
            }

            /* ==========================================
               7. MENSAJES DE ALERTA
            ========================================== */

            .stAlert {
                border-radius: 10px !important;
                border: none !important;
                padding: 12px 15px !important;
                box-shadow:
                    0 4px 12px rgba(0,0,0,0.08) !important;
            }

            /* ==========================================
               8. RECUPERACIÓN DE CREDENCIALES
            ========================================== */

            .login-recovery {
                text-align: center;
                color: #E2EAF6;
                font-size: 13px;
                margin-top: 24px;
                line-height: 1.6;
            }

            .login-recovery strong {
                color: #F2B544;
                font-weight: 600;
            }

            /* ==========================================
               9. INFORMACIÓN DE BASE DE DATOS
            ========================================== */

            .login-info {
                text-align: center;
                color: #E2EAF6;
                font-size: 12px;
                line-height: 1.6;
                margin-top: 18px;
                padding: 12px 15px;
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(242,181,68,0.35);
                border-radius: 10px;
                max-width: 500px;
                margin-left: auto;
                margin-right: auto;
            }

            .login-info strong {
                color: #F2B544;
            }

            /* ==========================================
               10. FOOTER
            ========================================== */

            .login-footer {
                text-align: center;
                color: rgba(226,234,246,0.65);
                font-size: 11px;
                margin-top: 30px;
                padding-bottom: 10px;
            }

            /* ==========================================
               11. RESPONSIVE
            ========================================== */

            @media (max-width: 640px) {
                .stForm {
                    padding: 25px 20px !important;
                    border-radius: 18px !important;
                }

                h1 {
                    font-size: 1.9rem !important;
                }

                .login-subtitle {
                    font-size: 14px;
                }

                .block-container {
                    padding-top: 1rem !important;
                }
            }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # ==========================================
    # CONTENEDOR CENTRAL
    # ==========================================

    col_izq, col_centro, col_der = st.columns([1, 2, 1])

    with col_centro:
        # LOGO
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)

        try:
            sc1, sc2, sc3 = st.columns([1, 1, 1])

            with sc2:
                st.image(LOGO_INSTITUCIONAL, use_container_width=True)

        except Exception:
            st.warning("⚠️ No se pudo cargar el logo institucional.")

        # TÍTULO
        st.markdown(f"<h1>{html.escape(APP_NAME)}</h1>", unsafe_allow_html=True)

        # SUBTÍTULO
        st.markdown(
            f"""
            <div class="login-subtitle">
                {html.escape(COLEGIO_NOMBRE)}
            </div>
            <div class="login-divider"></div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        # ==========================================
        # FORMULARIO DE AUTENTICACIÓN
        # ==========================================

        with st.form("login_form"):
            user = st.text_input("Usuario")

            password = st.text_input("Contraseña", type="password")

            submitted = st.form_submit_button(
                "INICIAR SESIÓN", type="primary", use_container_width=True
            )

        # ==========================================
        # VALIDACIÓN DE CREDENCIALES
        # ==========================================

        if submitted:
            if not user.strip():
                st.error("❌ Ingrese su usuario.")
                return
            if not password:
                st.error("❌ Ingrese su contraseña.")
                return
            if not db:
                st.error("⚠️ Sin conexión con la base de datos.")
                return
            try:
                usuario_data = obtener_usuario(user.strip())
                if not usuario_data:
                    st.error("❌ Usuario no encontrado.")
                    return
                if usuario_data.get("activo") is not True:
                    st.error(
                        "⛔ Este usuario se encuentra inactivo. Contacte a la Administración."
                    )
                    return
                password_hash = usuario_data.get("password_hash")
                if not password_hash:
                    st.error(
                        "⚠️ La cuenta no posee una credencial válida. Contacte a la Administración."
                    )
                    return
                from auth import verificar_password

                password_valida = verificar_password(password, password_hash)
                if not password_valida:
                    st.error("❌ Contraseña incorrecta.")
                    return
                if usuario_data.get("rol") not in ("admin", "docente"):
                    st.error("Usuario sin un rol autorizado.")
                    return
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = usuario_data.get("rol")
                st.session_state["user_name"] = usuario_data.get("nombre", user)
                st.session_state["user_id"] = user.strip()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al iniciar sesión: {e}")

        # ==========================================
        # RECUPERACIÓN DE CREDENCIALES
        # ==========================================

        st.markdown(
            """
            <div class="login-recovery">
                ¿Olvidó su credencial?
                Solicite restablecimiento con la
                <strong>Administración</strong>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ==========================================
        # INFORMACIÓN DE BASE DE DATOS
        # ==========================================

        st.markdown(
            """
            <div class="login-info">
                💡 <strong>Nota:</strong>
                Si la base de datos estuvo inactiva,
                puede tardar unos segundos en "despertar".
                Por favor, espera un momento si el inicio
                de sesión es lento.
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ==========================================
        # FOOTER
        # ==========================================

        st.markdown(
            """
            <div class="login-footer">
                © 2026 David Fuentes Development |
                Todos los derechos reservados.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==========================================
# 5. FUNCIÓN LOGOUT
# ==========================================
def logout():
    st.session_state.clear()
    st.rerun()


# ==========================================
# 6. CONTROL DE ACCESO
# ==========================================
if not st.session_state["logged_in"]:
    login()
    st.stop()

try:
    principal = authorize(db, "Inicio")
    st.session_state["user_name"] = principal.name
except AccessDenied as error:
    st.session_state.clear()
    st.error(str(error))
    st.stop()

# ==========================================
# 7. BARRA LATERAL
# ==========================================
aplicar_estilos()

opcion_seleccionada = mostrar_sidebar(
    st.session_state["user_name"], st.session_state["user_role"]
)

if opcion_seleccionada == "__logout__":
    logout()

# ==========================================
# 8. CONTENIDO PRINCIPAL
# ==========================================
try:
    render_module(db, opcion_seleccionada)
except AccessDenied as error:
    st.error(str(error))
except Exception:
    st.error("No se pudo completar la operación. Revise la conexión DEMO y vuelva a intentarlo.")
