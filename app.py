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
from views.dashboard import (
    mostrar_dashboard_admin,
    mostrar_dashboard_docente,
)

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

    if (
        st.session_state["user_role"] == "admin"
        and db
    ):
        mostrar_dashboard_admin(
            db=db,
            nombre_usuario=limpiar_nombre(
                st.session_state["user_name"]
            ),
        )

    elif (
        st.session_state["user_role"] == "docente"
        and db
    ):
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