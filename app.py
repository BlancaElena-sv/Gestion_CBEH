import streamlit as st
import pandas as pd
from firebase_admin import firestore
from firebase_service import (
    conectar_firebase,
    subir_archivo,
)
from datetime import datetime, date, timedelta
import base64
import time
import os
import streamlit.components.v1 as components
import re

from config import APP_NAME, COLEGIO_NOMBRE, CICLO_LECTIVO, TZ_SV
from utils import get_base64, redondear_mined
from auth import generar_hash, verificar_password
from styles import aplicar_estilos
from components.sidebar import mostrar_sidebar
from views.alumnos import mostrar_consulta_alumnos
from views.inscripcion import mostrar_inscripcion
from views.docentes import mostrar_maestros
from views.promocion import mostrar_promocion
from views.asistencia import mostrar_asistencia_global
from views.notas import mostrar_notas
from views.finanzas import mostrar_finanzas
from views.configuracion import mostrar_configuracion
from views.docente_panel import mostrar_panel_docente

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title=APP_NAME, 
    layout="wide", 
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

aplicar_estilos()

from academic_config import (
    MAPA_CURRICULAR,
    LISTA_GRADOS_TODO,
    LISTA_GRADOS_NOTAS,
    LISTA_MESES,
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
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "user_role" not in st.session_state: st.session_state["user_role"] = None
if "user_name" not in st.session_state: st.session_state["user_name"] = None
if "user_id" not in st.session_state: st.session_state["user_id"] = None

def limpiar_nombre(nombre):
    if not nombre: return ""
    return nombre.replace("*", "").replace("_", " ").strip()

def login():
    col_izq, col_centro, col_der = st.columns([1, 2, 1])

    with col_centro:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)

        try:
            sc1, sc2, sc3 = st.columns([1, 1, 1])

            with sc2:
                st.image("logo.png", use_container_width=True)

        except Exception:
            st.warning("⚠️")

        st.markdown(
            "<h1 style='text-align: center; color: #1E3A8A;'>EduManager</h1>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<h4 style='text-align: center; color: #555;'>"
            "Colegio Profa. Blanca Elena de Hernández"
            "</h4>",
            unsafe_allow_html=True
        )

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")

            submitted = st.form_submit_button(
                "INICIAR SESIÓN",
                type="primary",
                use_container_width=True
            )

        if submitted:

                # ------------------------------------------
                # VALIDACIONES BÁSICAS
                # ------------------------------------------

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
                    # --------------------------------------
                    # BUSCAR USUARIO
                    # --------------------------------------

                    doc = (
                        db.collection("usuarios")
                        .document(user.strip())
                        .get()
                    )

                    if not doc.exists:
                        st.error("❌ Usuario no encontrado.")
                        return

                    d = doc.to_dict()

                    # --------------------------------------
                    # COMPROBAR ESTADO
                    # --------------------------------------

                    if not d.get("activo", True):
                        st.error(
                            "⛔ Este usuario se encuentra inactivo. "
                            "Contacte a la Administración."
                        )
                        return

                    # --------------------------------------
                    # COMPROBAR CONTRASEÑA HASH
                    # --------------------------------------

                    password_hash = d.get("password_hash")

                    if not password_hash:
                        st.error(
                            "⚠️ La cuenta no posee una credencial válida. "
                            "Contacte a la Administración."
                        )
                        return

                    password_valida = verificar_password(
                        password,
                        password_hash
                    )

                    if not password_valida:
                        st.error("❌ Contraseña incorrecta.")
                        return

                    # --------------------------------------
                    # LOGIN CORRECTO
                    # --------------------------------------

                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = d.get("rol")
                    st.session_state["user_name"] = d.get(
                        "nombre",
                        user
                    )
                    st.session_state["user_id"] = user.strip()

                    st.rerun()

                except Exception as e:
                    st.error(
                        f"❌ Error al iniciar sesión: {e}"
                    )

                else:
                    st.error("⚠️ Sin conexión.")

        st.info(
            "¿Olvidó su credencial? Solicite restablecimiento "
            "con la Administración."
        )

        st.markdown(
            "<div style='text-align: center; color: grey; "
            "font-size: 11px; margin-top: 40px;'>"
            "<p>© 2026 David Fuentes Development | "
            "Todos los derechos reservados.</p>"
            "</div>",
            unsafe_allow_html=True
        )

def logout():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state["logged_in"] = False
    st.rerun()

if not st.session_state["logged_in"]:
    login()
    st.stop()
# ==========================================
# 3. FUNCIONES AUXILIARES
# ==========================================
def borrar_coleccion(coll_name, batch_size=10):
    if not db: return
    docs = db.collection(coll_name).limit(batch_size).stream()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    if deleted >= batch_size: return borrar_coleccion(coll_name, batch_size)

def verificar_pago_duplicado_hoy(docente_id, tipo_gasto):
    docs = db.collection("finanzas").where("docente_id", "==", docente_id).where("tipo", "==", "egreso").stream()
    hoy = obtener_fecha_hoy() 
    for d in docs:
        data = d.to_dict()
        fecha_db = data.get("fecha")
        if fecha_db:
            if isinstance(fecha_db, datetime): f_obj = fecha_db.astimezone(TZ_SV).date()
            else: f_obj = datetime.fromtimestamp(fecha_db.timestamp(), TZ_SV).date()
            
            if f_obj == hoy and "Salario" in data.get("descripcion", "") and "Salario" in tipo_gasto:
                return True
    return False

def existe_duplicado(coleccion, campo_id, id_valor, descripcion):
    docs = db.collection(coleccion).where(campo_id, "==", id_valor).where("descripcion", "==", descripcion).stream()
    hoy = obtener_fecha_hoy() 
    for d in docs:
        data = d.to_dict()
        fecha_db = data.get("fecha")
        if fecha_db:
            if isinstance(fecha_db, datetime): f_obj = fecha_db.astimezone(TZ_SV).date()
            else: f_obj = datetime.fromtimestamp(fecha_db.timestamp(), TZ_SV).date()
            if f_obj == hoy: return True
    return False

# ==========================================
# 4. BARRA LATERAL
# ==========================================
opcion_seleccionada = mostrar_sidebar(
    st.session_state["user_name"],
    st.session_state["user_role"]
)

if opcion_seleccionada == "__logout__":
    logout()

# ==========================================
# 5. CONTENIDO PRINCIPAL
# ==========================================

# --- INICIO ---
if opcion_seleccionada == "Inicio":
    st.title("🍎 Tablero Institucional")

    if st.session_state["user_role"] == "docente" and db:
        nombre_limpio = limpiar_nombre(st.session_state.get("user_name", ""))
        found_prof = None

        try:
            q_prof = (
                db.collection("maestros_perfil")
                .where("nombre", "==", st.session_state["user_name"])
                .stream()
            )
            for p in q_prof:
                found_prof = p.to_dict()
        except Exception:
            pass

        if not found_prof:
            try:
                q_prof_clean = (
                    db.collection("maestros_perfil")
                    .where("nombre", "==", nombre_limpio)
                    .stream()
                )
                for p in q_prof_clean:
                    found_prof = p.to_dict()
            except Exception:
                pass

        col_p1, col_p2 = st.columns([1, 4])

        with col_p1:
            if found_prof and found_prof.get("foto_url"):
                st.image(found_prof["foto_url"], width=150)
            else:
                st.markdown(
                    "<h1 style='text-align: center;'>👤</h1>",
                    unsafe_allow_html=True,
                )

        with col_p2:
            st.subheader(f"Bienvenido, {nombre_limpio}")
            st.info("Panel Docente - EduManager")

            if found_prof:
                st.write(
                    f"📞 {found_prof.get('telefono', '')} | "
                    f"📧 {found_prof.get('email', '')}"
                )

    else:
        st.markdown(
            f"""
<div class="dashboard-header">
    <div class="dashboard-eyebrow">PANEL ADMINISTRATIVO</div>
    <div class="dashboard-title">
        Bienvenido, {limpiar_nombre(st.session_state['user_name'])}
    </div>
    <div class="dashboard-subtitle">
        {COLEGIO_NOMBRE} · Ciclo Lectivo {CICLO_LECTIVO}
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        try:
            alumnos_activos = list(
                db.collection("alumnos")
                .where("estado", "==", "Activo")
                .stream()
            )

            docentes_activos = list(
                db.collection("maestros_perfil")
                .where("activo", "==", True)
                .stream()
            )

            total_alumnos = len(alumnos_activos)
            total_docentes = len(docentes_activos)

        except Exception:
            total_alumnos = 0
            total_docentes = 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        with kpi1:
            st.metric(
                label="👨‍🎓 Alumnos activos",
                value=total_alumnos,
            )

        with kpi2:
            st.metric(
                label="👩‍🏫 Docentes activos",
                value=total_docentes,
            )

        with kpi3:
            st.metric(
                label="📅 Ciclo lectivo",
                value=CICLO_LECTIVO,
            )

        with kpi4:
            st.metric(
                label="🟢 Estado",
                value="Operativo",
            )

    st.markdown("---")
    st.subheader("📅 Agenda de Actividades")

    col_izq, col_der = st.columns(2)

    with col_izq:
        st.info("**ESTADO: PERIODO DE INSCRIPCIÓN FINALIZADO**")
        st.write("- Recepción de documentos.")
        st.write("- Actualización de datos.")

    with col_der:
        st.success("**PRÓXIMO: INICIO DE EXÁMENES MENSUALES**")
        st.metric("Fecha", "23 de Febrero", "2026")

    cronograma = [
        {
            "Fecha": "16 Feb - 18 Feb",
            "Actividad": "Matrícula Extraordinaria",
            "Estado": "En Curso",
        },
        {
            "Fecha": "20 Feb",
            "Actividad": "Última fecha de Pagos",
            "Estado": "En Curso",
        },
        {
            "Fecha": "19 Feb",
            "Actividad": "Entrega de Exámenes a Dirección",
            "Estado": "Programado",
        },
        {
            "Fecha": "23 Feb",
            "Actividad": "Inicio de exámenes mensuales",
            "Estado": "Pendiente",
        },
    ]

    st.table(pd.DataFrame(cronograma))


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
        # --- 5. ASISTENCIA GLOBAL ---

        st.caption(
            f"📅 Ciclo Lectivo actual: {CICLO_LECTIVO}"
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
            ciclo_origen=2026,
                ciclo_destino=2027,
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