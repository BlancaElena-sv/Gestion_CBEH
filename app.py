import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path

import streamlit as st

APP_DIR = str(Path(__file__).resolve().parent)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

mostrar_maestros = import_module("views.docentes").mostrar_maestros

from auth import generar_hash, verificar_password
from components.sidebar import mostrar_sidebar
from config import APP_NAME, CICLO_LECTIVO, TZ_SV
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
from views.finanzas import mostrar_finanzas
from views.inscripcion import mostrar_inscripcion
from views.notas import mostrar_notas
from views.promocion import mostrar_promocion

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
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


# ==========================================
# FUNCIONES AUXILIARES
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
# 1. CONEXIÓN A SUPABASE
# ==========================================
from supabase_service import (
    conectar_supabase,
    obtener_usuario,
    subir_archivo,
)

supabase, db_error = conectar_supabase()
if db_error:
    st.error(f"Error de conexión con Supabase: {db_error}")
    st.stop()


# ==========================================
# 2. FUNCIONES DE LOGIN / LOGOUT
# ==========================================
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
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h4 style='text-align: center; color: #555;'>"
            "Colegio Profa. Blanca Elena de Hernández"
            "</h4>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button(
                "INICIAR SESIÓN", type="primary", use_container_width=True
            )

        if submitted:
            if not user.strip():
                st.error("❌ Ingrese su usuario.")
                return
            if not password:
                st.error("❌ Ingrese su contraseña.")
                return
            if not supabase:
                st.error("️ Sin conexión con la base de datos.")
                return
            try:
                usuario_data = obtener_usuario(user.strip())
                if not usuario_data:
                    st.error("❌ Usuario no encontrado.")
                    return
                if not usuario_data.get("activo", True):
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
                password_valida = verificar_password(password, password_hash)
                if not password_valida:
                    st.error("❌ Contraseña incorrecta.")
                    return
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = usuario_data.get("rol")
                st.session_state["user_name"] = usuario_data.get("nombre", user)
                st.session_state["user_id"] = user.strip()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al iniciar sesión: {e}")

        st.info(
            "¿Olvidó su credencial? Solicite restablecimiento con la Administración."
        )
        st.markdown(
            "<div style='text-align: center; color: grey; "
            "font-size: 11px; margin-top: 40px;'>"
            "<p>© 2026 David Fuentes Development | "
            "Todos los derechos reservados.</p>"
            "</div>",
            unsafe_allow_html=True,
        )


def logout():
    # Limpiamos el estado de la sesión
    st.session_state.clear()

    # Forzamos a que la próxima vez que entre, caiga en el Inicio
    st.session_state["menu_actual"] = "Inicio"
    st.session_state["logged_in"] = False

    # Recargamos la página
    st.rerun()


# ==========================================
# 3. INICIALIZACIÓN DE SESSION STATE
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
# 4. CONTROL DE ACCESO - VERIFICAR LOGIN
# ==========================================
if not st.session_state.get("logged_in", False):
    login()
    st.stop()

# ==========================================
# 5. BARRA LATERAL
# ==========================================
opcion_seleccionada = mostrar_sidebar(
    st.session_state.get("user_name", ""), st.session_state.get("user_role", "")
)

if opcion_seleccionada == "__logout__":
    logout()


# ==========================================
# 6. FUNCIONES AUXILIARES DE BD
# ==========================================
def borrar_coleccion(tabla, batch_size=10):
    if not supabase:
        return
    try:
        response = supabase.table(tabla).select("id").limit(batch_size).execute()
        if response.data:
            for row in response.data:
                supabase.table(tabla).delete().eq("id", row["id"]).execute()
            if len(response.data) >= batch_size:
                borrar_coleccion(tabla, batch_size)
    except Exception as e:
        st.error(f"Error al borrar colección: {e}")


def verificar_pago_duplicado_hoy(docente_id, tipo_gasto):
    try:
        hoy = obtener_fecha_hoy().isoformat()
        response = (
            supabase.table("finanzas")
            .select("*")
            .eq("docente_id", docente_id)
            .eq("tipo", "egreso")
            .execute()
        )
        for row in response.data:
            fecha_db = row.get("fecha")
            if fecha_db:
                if isinstance(fecha_db, str):
                    f_obj = datetime.fromisoformat(fecha_db).date()
                elif isinstance(fecha_db, datetime):
                    f_obj = fecha_db.astimezone(TZ_SV).date()
                else:
                    f_obj = datetime.fromtimestamp(fecha_db, TZ_SV).date()
                if (
                    f_obj == obtener_fecha_hoy()
                    and "Salario" in row.get("descripcion", "")
                    and "Salario" in tipo_gasto
                ):
                    return True
        return False
    except Exception as e:
        st.error(f"Error al verificar pago duplicado: {e}")
        return False


def existe_duplicado(tabla, campo_id, id_valor, descripcion):
    try:
        hoy = obtener_fecha_hoy().isoformat()
        response = (
            supabase.table(tabla)
            .select("*")
            .eq(campo_id, id_valor)
            .eq("descripcion", descripcion)
            .execute()
        )
        for row in response.data:
            fecha_db = row.get("fecha")
            if fecha_db:
                if isinstance(fecha_db, str):
                    f_obj = datetime.fromisoformat(fecha_db).date()
                elif isinstance(fecha_db, datetime):
                    f_obj = fecha_db.astimezone(TZ_SV).date()
                else:
                    f_obj = datetime.fromtimestamp(fecha_db, TZ_SV).date()
                if f_obj == obtener_fecha_hoy():
                    return True
        return False
    except Exception as e:
        st.error(f"Error al verificar duplicado: {e}")
        return False


# ==========================================
# 7. CONTENIDO PRINCIPAL
# ==========================================
if opcion_seleccionada == "Inicio":
    if st.session_state.get("user_role") == "admin" and supabase:
        mostrar_dashboard_admin(
            db=supabase,
            nombre_usuario=limpiar_nombre(st.session_state.get("user_name", "")),
        )
    elif st.session_state.get("user_role") == "docente" and supabase:
        mostrar_dashboard_docente(
            db=supabase,
            nombre_usuario=st.session_state.get("user_name", ""),
            limpiar_nombre=limpiar_nombre,
        )

if st.session_state.get("user_role") == "admin" and opcion_seleccionada != "Inicio":
    if opcion_seleccionada == "Inscripción":
        mostrar_inscripcion(
            db=supabase,
            lista_grados=LISTA_GRADOS_TODO,
            subir_archivo=subir_archivo,
        )
    elif opcion_seleccionada == "Consulta Alumnos":
        mostrar_consulta_alumnos(
            db=supabase,
            lista_grados=LISTA_GRADOS_TODO,
            mapa_curricular=MAPA_CURRICULAR,
            redondear_mined=redondear_mined,
            get_base64=get_base64,
            obtener_fecha_hoy=obtener_fecha_hoy,
            subir_archivo=subir_archivo,
        )
    elif opcion_seleccionada == "Maestros":
        mostrar_maestros(
            db=supabase,
            lista_grados=LISTA_GRADOS_TODO,
            mapa_curricular=MAPA_CURRICULAR,
            subir_archivo=subir_archivo,
            obtener_fecha_hoy=obtener_fecha_hoy,
            obtener_hora_actual=obtener_hora_actual,
            verificar_pago_duplicado_hoy=verificar_pago_duplicado_hoy,
        )
    elif opcion_seleccionada == "Asistencia Global":
        mostrar_asistencia_global(
            db=supabase,
            lista_grados=LISTA_GRADOS_TODO,
            obtener_fecha_hoy=obtener_fecha_hoy,
        )
    elif opcion_seleccionada == "Notas":
        mostrar_notas(
            db=supabase,
            lista_grados_notas=LISTA_GRADOS_NOTAS,
            lista_meses=LISTA_MESES,
            mapa_curricular=MAPA_CURRICULAR,
            redondear_mined=redondear_mined,
            get_base64=get_base64,
        )
    elif opcion_seleccionada == "Finanzas":
        mostrar_finanzas(
            db=supabase,
            lista_grados=LISTA_GRADOS_TODO,
            obtener_fecha_hoy=obtener_fecha_hoy,
            obtener_hora_actual=obtener_hora_actual,
            existe_duplicado=existe_duplicado,
            verificar_pago_duplicado_hoy=verificar_pago_duplicado_hoy,
            get_base64=get_base64,
        )
    elif opcion_seleccionada == "Promoción de Grado":
        mostrar_promocion(
            db=supabase,
            obtener_fecha_hoy=obtener_fecha_hoy,
            ciclo_origen=CICLO_LECTIVO,
            ciclo_destino=CICLO_LECTIVO + 1,
        )
    elif opcion_seleccionada == "Configuración (Usuarios)":
        mostrar_configuracion(
            db=supabase,
            generar_hash=generar_hash,
            borrar_coleccion=borrar_coleccion,
        )

elif st.session_state.get("user_role") == "docente" and opcion_seleccionada != "Inicio":
    mostrar_panel_docente(
        opcion_seleccionada=opcion_seleccionada,
        db=supabase,
        lista_grados=LISTA_GRADOS_TODO,
        lista_grados_notas=LISTA_GRADOS_NOTAS,
        lista_meses=LISTA_MESES,
        mapa_curricular=MAPA_CURRICULAR,
        redondear_mined=redondear_mined,
        get_base64=get_base64,
        obtener_fecha_hoy=obtener_fecha_hoy,
        obtener_hora_actual=obtener_hora_actual,
    )
