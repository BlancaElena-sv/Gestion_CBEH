from datetime import datetime

import streamlit as st

from auth import generar_hash
from components.sidebar import mostrar_sidebar
from config import (
    APP_NAME,
    CICLO_LECTIVO,
    TZ_SV,
)
from firebase_selector import (
    conectar_firebase,
    subir_archivo,
)
from styles import aplicar_estilos
from utils import get_base64, redondear_mined
from views.alumnos import mostrar_consulta_alumnos
from views.asistencia import mostrar_asistencia_global
from views.configuracion import mostrar_configuracion
from views.dashboard import (
    mostrar_dashboard_admin,
    mostrar_dashboard_docente,
)
from views.docente_panel import mostrar_panel_docente
from views.docentes import mostrar_maestros
from views.finanzas import mostrar_finanzas
from views.inscripcion import mostrar_inscripcion
from views.notas import mostrar_notas
from views.promocion import mostrar_promocion

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title=APP_NAME, layout="wide", page_icon="🎓", initial_sidebar_state="expanded"
)

aplicar_estilos()

from academic_config import (
    LISTA_GRADOS_NOTAS,
    LISTA_GRADOS_TODO,
    LISTA_MESES,
    MAPA_CURRICULAR,
)


def obtener_fecha_hoy():
    """Retorna la fecha actual en El Salvador"""
    return datetime.now(TZ_SV).date()


def obtener_hora_actual():
    """Retorna fecha y hora legible en El Salvador"""
    return datetime.now(TZ_SV).strftime("%d/%m/%Y %H:%M")


# ==========================================
# 1. SISTEMA DE SEGURIDAD Y CONEXIÓN
# ==========================================

db = None

db_conn, db_error = conectar_firebase()

if db_error:
    st.error(f"Error de conexión con Firebase: {db_error}")

if db_conn:
    db = db_conn

# --- GESTIÓN DE SESIÓN ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None


def limpiar_nombre(nombre):
    if not nombre:
        return ""
    return nombre.replace("*", "").replace("_", " ").strip()


def login():
    # ==========================================
    # CSS DEL LOGIN MODERNO (VERSIÓN DEMO)
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

        /* Contenedores intermedios transparentes */
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
        .stImage img {
            filter: drop-shadow(0 8px 16px rgba(0,0,0,0.25)) !important;
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
            box-shadow: 0 0 0 3px rgba(36,87,166,0.13) !important;
            outline: none !important;
        }

        .stTextInput label {
            color: #334155 !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }

        /* ==========================================
           6. BOTÓN INICIAR SESIÓN
        ========================================== */
        .stForm button[kind="primary"] {
            background: linear-gradient(135deg, #E34B4B 0%, #C92F3B 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 13px 20px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            letter-spacing: 0.4px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 5px 15px rgba(201,47,59,0.25) !important;
            width: 100% !important;
        }

        .stForm button[kind="primary"]:hover {
            background: linear-gradient(135deg, #EF5555 0%, #B91C35 100%) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(201,47,59,0.35) !important;
        }

        /* ==========================================
           7. MENSAJES DE ALERTA
        ========================================== */
        .stAlert {
            border-radius: 10px !important;
            border: none !important;
            padding: 12px 15px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
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

    # ... resto de tu función login() con Firebase ...


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["logged_in"] = False
    st.rerun()


if not st.session_state["logged_in"]:
    login()
    st.stop()


# ==========================================
# 3. FUNCIONES AUXILIARES
# ==========================================
def borrar_coleccion(coll_name, batch_size=10):
    if not db:
        return
    docs = db.collection(coll_name).limit(batch_size).stream()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    if deleted >= batch_size:
        return borrar_coleccion(coll_name, batch_size)


def verificar_pago_duplicado_hoy(docente_id, tipo_gasto):
    docs = (
        db.collection("finanzas")
        .where("docente_id", "==", docente_id)
        .where("tipo", "==", "egreso")
        .stream()
    )
    hoy = obtener_fecha_hoy()
    for d in docs:
        data = d.to_dict()
        fecha_db = data.get("fecha")
        if fecha_db:
            if isinstance(fecha_db, datetime):
                f_obj = fecha_db.astimezone(TZ_SV).date()
            else:
                f_obj = datetime.fromtimestamp(fecha_db.timestamp(), TZ_SV).date()

            if (
                f_obj == hoy
                and "Salario" in data.get("descripcion", "")
                and "Salario" in tipo_gasto
            ):
                return True
    return False


def existe_duplicado(coleccion, campo_id, id_valor, descripcion):
    docs = (
        db.collection(coleccion)
        .where(campo_id, "==", id_valor)
        .where("descripcion", "==", descripcion)
        .stream()
    )
    hoy = obtener_fecha_hoy()
    for d in docs:
        data = d.to_dict()
        fecha_db = data.get("fecha")
        if fecha_db:
            if isinstance(fecha_db, datetime):
                f_obj = fecha_db.astimezone(TZ_SV).date()
            else:
                f_obj = datetime.fromtimestamp(fecha_db.timestamp(), TZ_SV).date()
            if f_obj == hoy:
                return True
    return False


# ==========================================
# 4. BARRA LATERAL
# ==========================================
opcion_seleccionada = mostrar_sidebar(
    st.session_state["user_name"], st.session_state["user_role"]
)

if opcion_seleccionada == "__logout__":
    logout()

# ==========================================
# 5. CONTENIDO PRINCIPAL
# ==========================================

# --- INICIO ---
if opcion_seleccionada == "Inicio":
    if st.session_state["user_role"] == "admin" and db:
        mostrar_dashboard_admin(
            db=db,
            nombre_usuario=limpiar_nombre(st.session_state["user_name"]),
        )

    elif st.session_state["user_role"] == "docente" and db:
        mostrar_dashboard_docente(
            db=db,
            nombre_usuario=st.session_state["user_name"],
            limpiar_nombre=limpiar_nombre,
        )


# ==========================================
# MÓDULOS DE ADMINISTRADOR
# ==========================================
if st.session_state["user_role"] == "admin" and opcion_seleccionada != "Inicio":
    # --- INSCRIPCIÓN ---
    if opcion_seleccionada == "Inscripción":
        mostrar_inscripcion(
            db=db,
            lista_grados=LISTA_GRADOS_TODO,
            subir_archivo=subir_archivo,
        )

    # --- CONSULTA ALUMNOS ---
    elif opcion_seleccionada == "Consulta Alumnos":
        mostrar_consulta_alumnos(
            db=db,
            lista_grados=LISTA_GRADOS_TODO,
            mapa_curricular=MAPA_CURRICULAR,
            redondear_mined=redondear_mined,
            get_base64=get_base64,
            obtener_fecha_hoy=obtener_fecha_hoy,
            subir_archivo=subir_archivo,
        )
        # ---  MAESTROS ---
    elif opcion_seleccionada == "Maestros":
        mostrar_maestros(
            db=db,
            lista_grados=LISTA_GRADOS_TODO,
            mapa_curricular=MAPA_CURRICULAR,
            subir_archivo=subir_archivo,
            obtener_fecha_hoy=obtener_fecha_hoy,
            obtener_hora_actual=obtener_hora_actual,
            verificar_pago_duplicado_hoy=verificar_pago_duplicado_hoy,
        )

    elif opcion_seleccionada == "Asistencia Global":
        mostrar_asistencia_global(
            db=db,
            lista_grados=LISTA_GRADOS_TODO,
            obtener_fecha_hoy=obtener_fecha_hoy,
        )
    elif opcion_seleccionada == "Notas":
        mostrar_notas(
            db=db,
            lista_grados_notas=LISTA_GRADOS_NOTAS,
            lista_meses=LISTA_MESES,
            mapa_curricular=MAPA_CURRICULAR,
            redondear_mined=redondear_mined,
            get_base64=get_base64,
        )

    elif opcion_seleccionada == "Finanzas":
        mostrar_finanzas(
            db=db,
            lista_grados=LISTA_GRADOS_TODO,
            obtener_fecha_hoy=obtener_fecha_hoy,
            obtener_hora_actual=obtener_hora_actual,
            existe_duplicado=existe_duplicado,
            verificar_pago_duplicado_hoy=verificar_pago_duplicado_hoy,
            get_base64=get_base64,
        )

    elif opcion_seleccionada == "Promoción de Grado":
        mostrar_promocion(
            db=db,
            obtener_fecha_hoy=obtener_fecha_hoy,
            ciclo_origen=CICLO_LECTIVO,
            ciclo_destino=CICLO_LECTIVO + 1,
        )

    elif opcion_seleccionada == "Configuración (Usuarios)":
        mostrar_configuracion(
            db=db,
            generar_hash=generar_hash,
            borrar_coleccion=borrar_coleccion,
        )

# ==========================================
# MÓDULOS DE DOCENTE
# ==========================================
elif st.session_state["user_role"] == "docente" and opcion_seleccionada != "Inicio":
    mostrar_panel_docente(
        opcion_seleccionada=opcion_seleccionada,
        db=db,
        lista_grados=LISTA_GRADOS_TODO,
        lista_grados_notas=LISTA_GRADOS_NOTAS,
        lista_meses=LISTA_MESES,
        mapa_curricular=MAPA_CURRICULAR,
        redondear_mined=redondear_mined,
        get_base64=get_base64,
        obtener_fecha_hoy=obtener_fecha_hoy,
        obtener_hora_actual=obtener_hora_actual,
    )
