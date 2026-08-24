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
    
    if opcion_seleccionada == "Mis Listados":
        st.title("🖨️ Imprimir Listas")
        g = st.selectbox("Grado:", LISTA_GRADOS_TODO)
        mes_lista = st.selectbox("Mes:", LISTA_MESES)
        if st.button("Generar Hoja de Control"):
            docs = (
                db.collection("alumnos")
                .where("grado_actual", "==", g)
                .where("estado", "==", "Activo")
                .stream()
            )
            lista = sorted([f"{d.to_dict().get('apellidos', '')} {d.to_dict().get('nombres', '')}" for d in docs])
            if not lista: st.warning("Sin alumnos")
            else:
                logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="50">' if logo else ""
                rows = ""
                for i, n in enumerate(lista):
                    rows += f"<tr><td>{i+1}</td><td style='text-align:left;padding-left:5px;'>{n}</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>"
                html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:15px'><h3>COLEGIO PROFA. BLANCA ELENA</h3><h4>CONTROL DE EVALUACIÓN - {mes_lista.upper()} - {g.upper()}</h4></div></div><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#eee;font-weight:bold;'><td width='5%'>No.</td><td width='40%'>NOMBRE</td><td width='8%'>ACT1</td><td width='8%'>ACT2</td><td width='8%'>ALT1</td><td width='8%'>ALT2</td><td width='8%'>EXAM</td><td width='10%'>PROM</td></tr>{rows}</table></div>"""
                components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR LISTADO</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

    elif opcion_seleccionada == "Tomar Asistencia":
        st.title("📅 Control de Asistencia")
        c1, c2 = st.columns(2)
        fecha_asist = c1.date_input("Fecha:", obtener_fecha_hoy())
        grado_asist = c2.selectbox("Grado:", LISTA_GRADOS_TODO)
        if grado_asist:
            id_asistencia = ( f"{CICLO_LECTIVO}_{fecha_asist}_{grado_asist}")
            doc_ref = db.collection("asistencia").document(id_asistencia)
            doc_snap = doc_ref.get()
            alumnos_ref = (
                db.collection("alumnos")
                .where("grado_actual", "==", grado_asist)
                .where("estado", "==", "Activo")
                .stream()
            )    
            lista_alumnos = [{"NIE": d.to_dict()['nie'], "Nombre": f"{d.to_dict().get('apellidos', '')} {d.to_dict().get('nombres', '')}"} for d in alumnos_ref]
            lista_alumnos.sort(key=lambda x: x["Nombre"])
            if lista_alumnos:
                datos = doc_snap.to_dict().get("registros", {}) if doc_snap.exists else {}
                observaciones = doc_snap.to_dict().get("observaciones", {}) if doc_snap.exists else {}
                data_editor = []
                for alum in lista_alumnos:
                    data_editor.append({"NIE": alum["NIE"], "Nombre": alum["Nombre"], "Estado": datos.get(alum["NIE"], "Presente"), "Observación": observaciones.get(alum["NIE"], "")})
                df_asist = pd.DataFrame(data_editor)
                ed = st.data_editor(df_asist, column_config={"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True), "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente", "Tardanza", "Permiso"], required=True), "Observación": st.column_config.TextColumn(width="medium")}, hide_index=True, use_container_width=True, key=id_asistencia)
                if st.button("💾 Guardar Asistencia"):
                    regs = {r["NIE"]: r["Estado"] for r in ed.to_dict(orient="records")}
                    obs_regs = {r["NIE"]: r["Observación"] for r in ed.to_dict(orient="records")}
                    doc_ref.set({"fecha": datetime.combine(fecha_asist, datetime.min.time()), "ciclo_lectivo": CICLO_LECTIVO, "grado": grado_asist, "registros": regs, "observaciones": obs_regs})
                    st.success("Guardado.")
            else: st.warning("Sin alumnos.")

    elif opcion_seleccionada == "Cargar Notas":
        st.title("📝 Registro de Notas")
        c1, c2, c3 = st.columns(3)
        g = c1.selectbox("Grado", ["Select..."]+LISTA_GRADOS_NOTAS)
        mp = MAPA_CURRICULAR.get(g,[]) if g!="Select..." else []
        m = c2.selectbox("Materia", ["Select..."]+mp)
        mes = c3.selectbox("Mes", LISTA_MESES)
        if g!="Select..." and m!="Select...":
            docs = (
                db.collection("alumnos")
                .where("grado_actual", "==", g)
                .where("estado", "==", "Activo")
                .stream()
            )
            lista = [{"NIE": d.to_dict()['nie'], "Nombre": f"{d.to_dict().get('apellidos', '')} {d.to_dict().get('nombres', '')}"} for d in docs]
            if not lista: st.warning("Sin alumnos")
            else:
                df = pd.DataFrame(lista).sort_values("Nombre")
                id_doc = (f"{CICLO_LECTIVO}_{g}_{m}_{mes}".replace(" ","_"))
                cols = ["Nota Conducta"] if m == "Conducta" else ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
                doc_ref = db.collection("notas_mensuales").document(id_doc).get()
                if doc_ref.exists:
                    dd = doc_ref.to_dict().get('detalles', {})
                    for c in cols: df[c] = df["NIE"].map(lambda x: dd.get(x, {}).get(c, 0.0))
                else:
                    for c in cols: df[c] = 0.0
                df["Promedio"] = 0.0
                cfg = {"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True, width="medium"), "Promedio": st.column_config.NumberColumn(disabled=True)}
                for c in cols: cfg[c] = st.column_config.NumberColumn(min_value=0.0, max_value=10.0, step=0.01)
                if m == "Conducta": df["Promedio"] = df[cols[0]]
                else: df["Promedio"] = (df["Act1 (25%)"]*0.25 + df["Act2 (25%)"]*0.25 + df["Alt1 (10%)"]*0.10 + df["Alt2 (10%)"]*0.10 + df["Examen (30%)"]*0.30).apply(redondear_mined)
                ed = st.data_editor(df, column_config=cfg, hide_index=True, use_container_width=True, key=id_doc)
                if st.button("Guardar"):
                    batch = db.batch()
                    detalles = {}
                    for _, r in ed.iterrows():
                        if m == "Conducta": prom = r[cols[0]]
                        else: prom = (r[cols[0]]*0.25 + r[cols[1]]*0.25 + r[cols[2]]*0.1 + r[cols[3]]*0.1 + r[cols[4]]*0.3)
                        prom_r = redondear_mined(prom)
                        detalles[r["NIE"]] = {c: r[c] for c in cols}
                        detalles[r["NIE"]]["Promedio"] = prom_r
                        ref = db.collection("notas").document(f"{r['NIE']}_{id_doc}")
                        batch.set(ref, {"nie": r["NIE"], "grado": g, "materia": m, "mes": mes, "promedio_final": prom_r,"ciclo_lectivo": CICLO_LECTIVO })
                    db.collection("notas_mensuales").document(id_doc).set({"ciclo_lectivo": CICLO_LECTIVO, "grado": g, "materia": m, "mes": mes, "detalles": detalles})
                    batch.commit()
                    st.success("Guardado"); time.sleep(1); st.rerun()

    elif opcion_seleccionada == "Ver Mis Cargas":
        st.title("📋 Mi Carga Académica")
        cargas = db.collection("carga_academica").where("nombre_docente", "==", st.session_state["user_name"]).stream()
        found = False
        for c in cargas:
            found = True
            d = c.to_dict()
            with st.container(border=True):
                st.subheader(d['grado'])
                st.write("**Materias:** " + ", ".join(d['materias']))
                if d.get('es_guia'): st.success("🌟 MAESTRO GUÍA")
        if not found: st.info("No se encontraron cargas asignadas a su nombre exacto. Contacte a Dirección.")

    elif opcion_seleccionada == "Expediente Alumnos":
        st.title("📂 Bitácora del Alumno")
        c1, c2 = st.columns(2)
        grado_sel = c1.selectbox("Seleccionar Grado", LISTA_GRADOS_TODO)
        alumnos_grado = (
            db.collection("alumnos")
            .where("grado_actual", "==", grado_sel)
            .where("estado", "==", "Activo")
            .stream()
        )
        dict_alumnos = {f"{a.to_dict().get('apellidos', '')} {a.to_dict().get('nombres', '')}": a.to_dict() for a in alumnos_grado}
        if dict_alumnos:
            nombre_alum = c2.selectbox("Seleccionar Alumno", ["Seleccionar..."] + sorted(list(dict_alumnos.keys())))
            if nombre_alum != "Seleccionar...":
                alum_data = dict_alumnos[nombre_alum]
                nie_actual = alum_data['nie']
                st.markdown("---")
                cp1, cp2 = st.columns([1, 4])
                with cp1:
                    foto_url_alum = (
                        alum_data.get("documentos", {})
                        .get("foto_url")
                    )

                    if foto_url_alum:
                        try:
                            st.image(
                                foto_url_alum,
                                width=130
                            )
                        except Exception:
                            st.markdown(
                                """
                                <div style="
                                    width:130px;
                                    height:130px;
                                    border-radius:50%;
                                    background:#e9edf5;
                                    display:flex;
                                    align-items:center;
                                    justify-content:center;
                                    font-size:55px;
                                    margin:auto;
                                ">
                                    👤
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            """
                            <div style="
                                width:130px;
                                height:130px;
                                border-radius:50%;
                                background:#e9edf5;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                font-size:55px;
                                margin:auto;
                            ">
                                👤
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                with cp2:
                    st.subheader(f"{alum_data.get('apellidos', '')} {alum_data.get('nombres', '')}")
                    st.write(f"**NIE:** {alum_data['nie']} | **Responsable:** {alum_data.get('encargado',{}).get('nombre','-')}")
                    st.write(f"**Tel:** {alum_data.get('encargado',{}).get('telefono','-')}")
                st.divider()
                st.markdown("### 📝 Historial de Observaciones")
                with st.expander("➕ Agregar Nueva Nota / Observación", expanded=True):
                    with st.form("form_bitacora"):
                        nota_texto = st.text_area("Escriba la observación:")
                        if st.form_submit_button("Guardar en Bitácora"):
                            if nota_texto:
                                nueva_entrada = {"nie": nie_actual, "alumno": nombre_alum, "grado": grado_sel, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": obtener_hora_actual(), "autor": st.session_state["user_name"], "contenido": nota_texto}
                                db.collection("bitacora").add(nueva_entrada)
                                st.success("Nota agregada."); time.sleep(1); st.rerun()
                            else: st.warning("La nota no puede estar vacía.")
                logs = db.collection("bitacora").where("nie", "==", nie_actual).stream()
                lista_logs = [l.to_dict() for l in logs]
                lista_logs.sort(key=lambda x: x.get('fecha_legible', ''), reverse=True)
                if lista_logs:
                    for log in lista_logs:
                        with st.container(border=True):
                            c_meta, c_body = st.columns([1, 3])
                            with c_meta:
                                st.caption(f"📅 {log.get('fecha_legible')}")
                                st.caption(f"✍️ **{log.get('autor')}**")
                            with c_body: st.write(log.get('contenido'))
                else: st.info("No hay registros en la bitácora de este alumno.")
        else: c2.warning("No hay alumnos inscritos en este grado.")

    # AÑADIDO: MÓDULO DE BOLETAS PARA DOCENTES
    elif opcion_seleccionada == "Boletas de Notas":
        st.title("🖨️ Impresión de Boletas de Notas")
        c1, c2 = st.columns(2)
        grado_sel = c1.selectbox("Seleccionar Grado", LISTA_GRADOS_TODO)
        alumnos_grado = (
            db.collection("alumnos")
            .where("grado_actual", "==", grado_sel)
            .where("estado", "==", "Activo")
            .stream()
        )
        dict_alumnos = {f"{a.to_dict().get('apellidos', '')} {a.to_dict().get('nombres', '')}": a.to_dict() for a in alumnos_grado}
        
        if dict_alumnos:
            nombre_alum = c2.selectbox("Seleccionar Alumno", ["Seleccionar..."] + sorted(list(dict_alumnos.keys())))
            if nombre_alum != "Seleccionar...":
                alum_data = dict_alumnos[nombre_alum]
                malla_completa = MAPA_CURRICULAR.get(grado_sel, [])
                
                st.markdown("---")
                st.subheader("Configuración de Boleta")
                st.info("Puede eliminar de la lista las materias que aún no desea que aparezcan en el reporte impreso.")
                materias_seleccionadas = st.multiselect("Seleccione las materias a incluir en la boleta:", malla_completa, default=malla_completa)
                
                if st.button("Generar Boleta") and materias_seleccionadas:
                    # Obtener al guía del grado
                    q_guia = db.collection("carga_academica").where("grado", "==", grado_sel).where("es_guia", "==", True).stream()
                    maestro_guia = "No Asignado"
                    for d in q_guia: maestro_guia = d.to_dict()['nombre_docente']

                    # Obtener notas del alumno
                    notas = db.collection("notas").where("nie", "==", alum_data['nie']).stream()
                    nm = {}
                    for doc in notas:
                        dd = doc.to_dict()
                        if dd['materia'] not in nm: nm[dd['materia']] = {}
                        nm[dd['materia']][dd['mes']] = dd['promedio_final']
                    
                    filas = []
                    for mat in materias_seleccionadas:
                        if mat in nm:
                            n = nm[mat]
                            t1 = redondear_mined((n.get("Febrero",0)+n.get("Marzo",0)+n.get("Abril",0))/3)
                            t2 = redondear_mined((n.get("Mayo",0)+n.get("Junio",0)+n.get("Julio",0))/3)
                            t3 = redondear_mined((n.get("Agosto",0)+n.get("Septiembre",0)+n.get("Octubre",0))/3)
                            fin = redondear_mined((t1+t2+t3)/3)
                            filas.append(f"<tr><td style='text-align:left'>{mat}</td><td>{n.get('Febrero','-')}</td><td>{n.get('Marzo','-')}</td><td>{n.get('Abril','-')}</td><td style='background:#eee'><b>{t1}</b></td><td>{n.get('Mayo','-')}</td><td>{n.get('Junio','-')}</td><td>{n.get('Julio','-')}</td><td style='background:#eee'><b>{t2}</b></td><td>{n.get('Agosto','-')}</td><td>{n.get('Septiembre','-')}</td><td>{n.get('Octubre','-')}</td><td style='background:#eee'><b>{t3}</b></td><td style='background:#333;color:white'><b>{fin}</b></td></tr>")
                        else:
                            # Si no hay notas registradas para esa materia todavía
                            filas.append(f"<tr><td style='text-align:left'>{mat}</td><td>-</td><td>-</td><td>-</td><td style='background:#eee'><b>0.0</b></td><td>-</td><td>-</td><td>-</td><td style='background:#eee'><b>0.0</b></td><td>-</td><td>-</td><td>-</td><td style='background:#eee'><b>0.0</b></td><td style='background:#333;color:white'><b>0.0</b></td></tr>")

                    logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="60">' if logo else ""
                    sello = get_base64("sello.png"); hs = f'<img src="{sello}" height="80">' if sello else ""
                    html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:20px'><h2>COLEGIO PROFA. BLANCA ELENA</h2><h4>INFORME DE NOTAS</h4></div></div><p><b>Alumno:</b> {nombre_alum} | <b>Grado:</b> {grado_sel} | <b>Guía:</b> {maestro_guia}</p><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#ddd;font-weight:bold;'><td>ASIGNATURA</td><td>F</td><td>M</td><td>A</td><td>T1</td><td>M</td><td>J</td><td>J</td><td>T2</td><td>A</td><td>S</td><td>O</td><td>T3</td><td>FIN</td></tr>{"".join(filas)}</table><br><br><br><div style='display:flex;justify-content:space-between;align-items:end;padding:0 50px;'><div style='text-align:center;width:30%'><div style='border-top:1px solid black;width:100%'>Orientador</div></div><div style='text-align:center;'>{hs}</div><div style='text-align:center;width:30%'><div style='border-top:1px solid black;width:100%'>Dirección</div></div></div></div>"""
                    components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR BOLETA</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)
        else:
            c2.warning("No hay alumnos inscritos en este grado.")
    
        