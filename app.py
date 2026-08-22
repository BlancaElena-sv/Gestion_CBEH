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
                if db:

                    try:
                        doc = db.collection("usuarios").document(user).get()

                        if doc.exists:
                            d = doc.to_dict()

                            password_valida = False

                            # ==========================================
                            # NUEVO SISTEMA: BCRYPT
                            # ==========================================
                            if d.get("password_hash"):

                                password_valida = verificar_password(
                                    password,
                                    d["password_hash"]
                                )

                            # ==========================================
                            # RESULTADO DEL LOGIN
                            # ==========================================
                            if password_valida:
                                st.session_state["logged_in"] = True
                                st.session_state["user_role"] = d["rol"]
                                st.session_state["user_name"] = d.get("nombre", user)
                                st.session_state["user_id"] = user
                                st.rerun()

                            else:
                                st.error("❌ Contraseña incorrecta")

                        else:
                            st.error("❌ Usuario no encontrado")

                    except Exception as e:
                        st.error(f"Error: {e}")

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
        
    # --- 7. FINANZAS ---
    elif opcion_seleccionada == "Finanzas":
        st.title("💰 Administración Financiera")
        t1, t2, t3, t4 = st.tabs(["📊 Corte de Caja", "➕ Cobros (Alumnos)", "➖ Gastos Operativos", "📜 Reportes & Reimpresión"])
        
        with t1:
            c_date, _ = st.columns([1, 2])
            fecha_corte = c_date.date_input("Fecha de Corte", obtener_fecha_hoy())
            fecha_str = fecha_corte.strftime("%d/%m/%Y")
            all_fin = db.collection("finanzas").stream()
            data_hoy = []
            ingreso_dia = 0.0
            egreso_dia = 0.0
            for doc in all_fin:
                d = doc.to_dict()
                if d.get('fecha_legible') == fecha_str:
                    data_hoy.append(d)
                    if d['tipo'] == 'ingreso': ingreso_dia += d['monto']
                    elif d['tipo'] == 'egreso': egreso_dia += d['monto']
            saldo_dia = ingreso_dia - egreso_dia
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Ingresos del Día", f"${ingreso_dia:.2f}", delta_color="normal")
            kpi2.metric("Gastos del Día", f"${egreso_dia:.2f}", delta_color="inverse")
            kpi3.metric("Saldo Neto", f"${saldo_dia:.2f}")
            st.divider()
            if data_hoy:
                df_hoy = pd.DataFrame(data_hoy)
                st.dataframe(df_hoy[['descripcion', 'tipo', 'monto', 'nombre_persona']], use_container_width=True)
                if st.button("🖨️ Imprimir Corte del Día"):
                    logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="40">' if logo else ""
                    html_corte = f"""<div style="font-family:monospace;width:300px;margin:auto;border:1px solid black;padding:10px;"><div style="text-align:center;">{hi}<br><b>COLEGIO BLANCA ELENA</b><br>CORTE DE CAJA</div><br><b>FECHA:</b> {fecha_str}<br><hr><table width="100%"><tr><td>(+) INGRESOS:</td><td align="right">${ingreso_dia:.2f}</td></tr><tr><td>(-) GASTOS:</td><td align="right">${egreso_dia:.2f}</td></tr><tr><td><b>(=) SALDO:</b></td><td align="right"><b>${saldo_dia:.2f}</b></td></tr></table><br><div style="text-align:center;margin-top:20px;">___________________<br>Firma Responsable</div></div>"""
                    components.html(f"""<html><body>{html_corte}<br><center><button onclick="window.print()">IMPRIMIR</button></center></body></html>""", height=400)
            else: st.info("No hay movimientos hoy.")

        with t2:
            st.subheader("Búsqueda de Alumno para Cobro")
            modo_busqueda = st.radio("Buscar por:", ["NIE", "Nombre", "Grado"], horizontal=True)
            nie_encontrado = None
            
            if modo_busqueda == "NIE":
                n_input = st.text_input("Ingrese NIE:")

                if st.button("Buscar por NIE") and n_input:
                    d = db.collection("alumnos").document(n_input).get()

                    if d.exists:
                        alumno_data = d.to_dict()

                        if alumno_data.get("estado", "Activo") != "Activo":
                            st.warning(
                                "⚠️ Este alumno está dado de baja y no puede recibir nuevos cobros."
                            )

                            if "pago_alum" in st.session_state:
                                del st.session_state["pago_alum"]
                            if pa.get("estado", "Activo") != "Activo":
                                st.warning(
                                    "⚠️ El alumno seleccionado está dado de baja. "
                                    "No se permiten nuevos cobros."
                            )

                            del st.session_state["pago_alum"]
                            st.rerun()
                    else:
                        st.session_state.pago_alum = alumno_data
                else:
                    st.error("No encontrado")
            
            elif modo_busqueda == "Nombre":
                alums_ref = (
                    db.collection("alumnos")
                    .where("estado", "==", "Activo")
                    .stream()
                )
                mapa_nombres = {f"{a.to_dict().get('apellidos', '')} {a.to_dict().get('nombres', '')}": a.id for a in alums_ref}
                sel_nom = st.selectbox("Seleccione Alumno:", [""] + sorted(list(mapa_nombres.keys())))
                if sel_nom:
                    nie_encontrado = mapa_nombres[sel_nom]
                    if st.button("Cargar Alumno"):
                        st.session_state.pago_alum = db.collection("alumnos").document(nie_encontrado).get().to_dict()

            elif modo_busqueda == "Grado":
                sel_grado = st.selectbox("Seleccione Grado:", LISTA_GRADOS_TODO)
                alums_g = (
                    db.collection("alumnos")
                    .where("grado_actual", "==", sel_grado)
                    .where("estado", "==", "Activo")
                    .stream()
                )
                mapa_grado = {f"{a.to_dict().get('apellidos', '')} {a.to_dict().get('nombres', '')}": a.id for a in alums_g}
                sel_nom_g = st.selectbox("Alumno del Grado:", [""] + sorted(list(mapa_grado.keys())))
                if sel_nom_g:
                    nie_encontrado = mapa_grado[sel_nom_g]
                    if st.button("Cargar Alumno Grado"):
                        st.session_state.pago_alum = db.collection("alumnos").document(nie_encontrado).get().to_dict()
            
            st.divider()

            if "pago_alum" in st.session_state:
                pa = st.session_state.pago_alum
                st.success(f"Cobrando a: **{pa.get('apellidos', '')} {pa.get('nombres', '')}** (NIE: {pa['nie']})")
                
                with st.form("form_cobro"):
                    tipo_c = st.selectbox("Tipo de Cobro", ["Colegiatura", "Matrícula", "Uniformes", "Otros"])
                    det_c = st.text_input("Detalle (Ej: Mes de Marzo)")
                    monto = st.number_input("Monto ($)", min_value=0.01)
                    obs = st.text_input("Observaciones")
                    if st.form_submit_button("✅ Registrar Ingreso"):
                        desc_full = f"{tipo_c} - {det_c}"
                        if existe_duplicado("finanzas", "alumno_nie", pa['nie'], desc_full):
                            st.error("⛔ Transacción duplicada (Mismo alumno, mismo concepto hoy).")
                        else:
                            recibo_data = {"tipo": "ingreso", "descripcion": desc_full, "monto": monto, "alumno_nie": pa['nie'], "nombre_persona": f"{pa.get('apellidos', '')} {pa.get('nombres', '')}", "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": obtener_hora_actual(), "id_short": str(int(time.time()))[-6:]}
                            db.collection("finanzas").add(recibo_data)
                            st.session_state.recibo_temp = recibo_data
                            st.success("Cobro registrado")
                            del st.session_state.pago_alum
                            st.rerun()
            if "recibo_temp" in st.session_state:
                r = st.session_state.recibo_temp
                logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="60">' if logo else ""
                html_recibo = f"""<div style="border: 2px solid #333; padding: 20px; font-family: 'Helvetica', sans-serif; max-width: 700px; margin: auto;"><table width="100%"><tr><td width="20%">{hi}</td><td width="60%" align="center"><h3 style="margin:0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h3><p style="margin:5px; font-size:12px;">San Felipe, San Bartolo, Ilopango</p><p style="margin:0; font-size:12px;"><b>COMPROBANTE DE INGRESO</b></p></td><td width="20%" align="right"><h4 style="margin:0; color: #d32f2f;">NO. {r.get('id_short','000')}</h4><p style="font-size:12px;">{r['fecha_legible']}</p></td></tr></table><hr><div style="padding: 10px;"><p><b>RECIBIMOS DE:</b> {r['nombre_persona']}</p><p><b>LA CANTIDAD DE:</b> <span style="font-size:18px; font-weight:bold;">${r['monto']:.2f}</span></p><p><b>POR CONCEPTO DE:</b> {r['descripcion']}</p></div><br><br><table width="100%"><tr><td align="center" style="border-top: 1px solid #000; width:40%;">Entregado Por</td><td width="20%"></td><td align="center" style="border-top: 1px solid #000; width:40%;">Recibido (Caja)</td></tr></table></div>"""
                components.html(f"""<html><body>{html_recibo}<br><center><button onclick="window.print()">🖨️ IMPRIMIR COMPROBANTE</button></center></body></html>""", height=500)
                if st.button("Cerrar Comprobante"): del st.session_state.recibo_temp; st.rerun()

        with t3:
            with st.form("fg"):
                tp = st.selectbox("Gasto", ["Salario", "Servicios", "Mantenimiento", "Otros"])
                maestro_seleccionado = None
                per = ""
                if tp == "Salario":
                    ms = (
                        db.collection("maestros_perfil")
                        .where("activo", "==", True)
                        .stream()
                    )
                    l_ms = {m.to_dict()['nombre']: m.id for m in ms}
                    nom_sel = st.selectbox("Seleccionar Maestro:", list(l_ms.keys()))
                    if nom_sel: maestro_seleccionado = l_ms[nom_sel]; per = nom_sel
                else:
                    per = st.text_input("Pagado a (Nombre/Empresa)")
                
                mt = st.number_input("Monto", min_value=0.01)
                det_g = st.text_input("Detalle")
                
                if st.form_submit_button("Registrar"):
                    desc_full = f"{tp} - {det_g}"
                    duplicado = False
                    if tp == "Salario" and maestro_seleccionado:
                        if verificar_pago_duplicado_hoy(maestro_seleccionado, "Salario"): duplicado = True
                    
                    if duplicado:
                        st.error("⛔ Pago duplicado detectado (Salario ya registrado hoy para este docente).")
                    else:
                        gasto_data = {"tipo": "egreso", "descripcion": desc_full, "monto": mt, "nombre_persona": per, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": obtener_hora_actual(), "id_short": str(int(time.time()))[-6:]}
                        if maestro_seleccionado: gasto_data["docente_id"] = maestro_seleccionado
                        db.collection("finanzas").add(gasto_data)
                        st.session_state.gasto_temp = gasto_data
                        st.success("Registrado"); time.sleep(1); st.rerun()

            if "gasto_temp" in st.session_state:
                r = st.session_state.gasto_temp
                logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="60">' if logo else ""
                html_gasto = f"""<div style="border: 2px solid #d32f2f; padding: 20px; font-family: 'Helvetica', sans-serif; max-width: 700px; margin: auto;"><table width="100%"><tr><td width="20%">{hi}</td><td width="60%" align="center"><h3 style="margin:0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h3><p style="margin:0; font-size:12px;"><b>COMPROBANTE DE EGRESO (GASTO)</b></p></td><td width="20%" align="right"><h4 style="margin:0; color: #d32f2f;">NO. {r.get('id_short','000')}</h4><p style="font-size:12px;">{r['fecha_legible']}</p></td></tr></table><hr><div style="padding: 10px;"><p><b>PAGADO A:</b> {r['nombre_persona']}</p><p><b>LA CANTIDAD DE:</b> <span style="font-size:18px; font-weight:bold;">${r['monto']:.2f}</span></p><p><b>POR CONCEPTO DE:</b> {r['descripcion']}</p></div><br><br><table width="100%"><tr><td align="center" style="border-top: 1px solid #000; width:40%;">Autorizado Por</td><td width="20%"></td><td align="center" style="border-top: 1px solid #000; width:40%;">Recibido Conforme</td></tr></table></div>"""
                components.html(f"""<html><body>{html_gasto}<br><center><button onclick="window.print()">🖨️ IMPRIMIR COMPROBANTE</button></center></body></html>""", height=500)
                if st.button("Cerrar Comprobante Gasto"): del st.session_state.gasto_temp; st.rerun()

        with t4:
            st.subheader("📜 Reportes Financieros")
            mapa_grados = {}
            try:
                alums_ref = db.collection("alumnos").stream()
                for al in alums_ref:
                    ad = al.to_dict()
                    mapa_grados[ad.get('nie', 'ns')] = ad.get('grado_actual', 'Sin Grado')
            except: pass

            c_f1, c_f2, c_f3 = st.columns(3)
            filtro_rango = c_f1.selectbox("Rango de Tiempo", ["Este Mes", "Mes Pasado", "Últimos 3 Meses", "Últimos 6 Meses", "Este Año", "Personalizado"])
            f_tipo = c_f2.multiselect("Tipo Transacción:", ["ingreso", "egreso"], default=["ingreso", "egreso"])
            lista_grados_filtro = ["Todos"] + LISTA_GRADOS_TODO
            filtro_grado = c_f3.selectbox("Filtrar Grado (Alumnos):", lista_grados_filtro)

            hoy = obtener_fecha_hoy()
            f_inicio = hoy
            f_fin = hoy

            if filtro_rango == "Personalizado":
                c_d1, c_d2 = st.columns(2)
                f_inicio = c_d1.date_input("Desde", hoy.replace(day=1))
                f_fin = c_d2.date_input("Hasta", hoy)
            elif filtro_rango == "Este Mes":
                f_inicio = hoy.replace(day=1)
                f_fin = hoy
            elif filtro_rango == "Mes Pasado":
                mes_anterior = hoy.replace(day=1) - timedelta(days=1)
                f_inicio = mes_anterior.replace(day=1)
                f_fin = mes_anterior
            elif filtro_rango == "Últimos 3 Meses":
                f_inicio = hoy - timedelta(days=90)
                f_fin = hoy
            elif filtro_rango == "Últimos 6 Meses":
                f_inicio = hoy - timedelta(days=180)
                f_fin = hoy
            elif filtro_rango == "Este Año":
                f_inicio = hoy.replace(month=1, day=1)
                f_fin = hoy
            
            dt_ini = datetime.combine(f_inicio, datetime.min.time())
            dt_fin = datetime.combine(f_fin, datetime.max.time())
            
            docs_hist = db.collection("finanzas").stream() 
            data_raw = []
            tot_ing = 0.0
            tot_egr = 0.0
            
            for doc in docs_hist:
                d = doc.to_dict()
                d_date = d.get("fecha")
                if not d_date: continue
                # Manejo Timestamp con TZ
                if isinstance(d_date, datetime): actual = d_date.astimezone(TZ_SV).replace(tzinfo=None)
                else: actual = datetime.fromtimestamp(d_date.timestamp(), TZ_SV).replace(tzinfo=None)
                
                if dt_ini <= actual <= dt_fin:
                    if d['tipo'] not in f_tipo: continue
                    grado_alumno = "-"
                    nie_transaccion = d.get('alumno_nie')
                    if nie_transaccion and nie_transaccion in mapa_grados:
                        grado_alumno = mapa_grados[nie_transaccion]
                    d['grado_reporte'] = grado_alumno 
                    if filtro_grado != "Todos":
                        if grado_alumno != filtro_grado: continue
                    data_raw.append(d)
                    if d['tipo'] == 'ingreso': tot_ing += d['monto']
                    elif d['tipo'] == 'egreso': tot_egr += d['monto']
            
            st.divider()
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Ingresos", f"${tot_ing:.2f}", border=True)
            k2.metric("Total Egresos", f"${tot_egr:.2f}", delta_color="inverse", border=True)
            k3.metric("Balance Periodo", f"${tot_ing - tot_egr:.2f}", border=True)
            st.divider()

            data_raw.sort(key=lambda x: x.get('fecha_legible', ''), reverse=True)
            if data_raw:
                df_rep = pd.DataFrame(data_raw)
                st.dataframe(df_rep[['fecha_legible','tipo', 'grado_reporte', 'nombre_persona','descripcion','monto']], use_container_width=True)
                
                if st.button("🖨️ Imprimir Reporte Generado"):
                    logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="50">' if logo else ""
                    rows_html = ""
                    for item in data_raw:
                        color_row = "#e8f5e9" if item['tipo'] == 'ingreso' else "#ffebee"
                        rows_html += f"<tr style='background:{color_row};'><td>{item['fecha_legible']}</td><td>{item.get('grado_reporte','-')}</td><td>{item['nombre_persona']}</td><td>{item['descripcion']}</td><td align='right'>${item['monto']:.2f}</td></tr>"
                    
                    titulo_reporte = f"REPORTE FINANCIERO ({filtro_rango})"
                    if filtro_grado != "Todos": titulo_reporte += f" - {filtro_grado.upper()}"

                    html_reporte = f"""<div style="font-family:Arial; padding:20px;"><div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #333; padding-bottom:10px;"><div style="display:flex; align-items:center; gap:15px;">{hi}<div><h2 style="margin:0;">COLEGIO BLANCA ELENA</h2><p style="margin:0;">{titulo_reporte}</p></div></div><div style="text-align:right;"><p><b>Desde:</b> {f_inicio.strftime('%d/%m/%Y')}<br><b>Hasta:</b> {f_fin.strftime('%d/%m/%Y')}</p></div></div><br><div style="display:flex; gap:20px; margin-bottom:20px;"><div style="background:#e8f5e9; padding:10px; border:1px solid #4caf50; border-radius:5px; flex:1; text-align:center;"><h4 style="margin:0; color:#2e7d32;">INGRESOS</h4><h2 style="margin:0;">${tot_ing:.2f}</h2></div><div style="background:#ffebee; padding:10px; border:1px solid #e57373; border-radius:5px; flex:1; text-align:center;"><h4 style="margin:0; color:#c62828;">EGRESOS</h4><h2 style="margin:0;">${tot_egr:.2f}</h2></div><div style="background:#f5f5f5; padding:10px; border:1px solid #999; border-radius:5px; flex:1; text-align:center;"><h4 style="margin:0;">BALANCE</h4><h2 style="margin:0;">${tot_ing - tot_egr:.2f}</h2></div></div><table style="width:100%; border-collapse:collapse; font-size:12px;" border="1" bordercolor="#ddd"><tr style="background:#333; color:white;"><th padding="5">Fecha</th><th>Grado</th><th>Persona/Entidad</th><th>Descripción</th><th>Monto</th></tr>{rows_html}</table><br><br><div style="text-align:center;">__________________________<br>Firma Dirección</div></div>"""
                    components.html(f"""<html><body>{html_reporte}<br><center><button onclick="window.print()" style="background:#333; color:white; padding:10px 20px; cursor:pointer;">🖨️ IMPRIMIR REPORTE PDF</button></center></body></html>""", height=600, scrolling=True)
            else: st.info("No hay registros en este rango.")

    elif opcion_seleccionada == "Promoción de Grado":
        mostrar_promocion(
            db=db,
            obtener_fecha_hoy=obtener_fecha_hoy,
            ciclo_origen=2026,
                ciclo_destino=2027,
        )

    # --- 8. CONFIGURACIÓN (USUARIOS) ---
    elif opcion_seleccionada == "Configuración (Usuarios)":
        st.header("⚙️ Configuración")
        t_usr, t_db = st.tabs(["👥 Usuarios", "⚠️ Base de Datos"])
        
        with t_usr:
            st.subheader("Crear / Editar Credenciales")
            ur = db.collection("usuarios").stream()
            lu = [u.to_dict() for u in ur]
            if st.session_state["user_id"] != "david":
                lu = [x for x in lu if x["usuario"] != "david"]
            st.dataframe(pd.DataFrame(lu), use_container_width=True)
            with st.form("add_user"):
                c1, c2 = st.columns(2)
                u_user = c1.text_input("Usuario (ID)")
                u_pass = c2.text_input("Contraseña", type="password")
                u_name = c1.text_input("Nombre Real")
                u_rol = c2.selectbox("Rol", ["docente", "admin"])
                if st.form_submit_button("Guardar"):
                    if u_user == "david" and st.session_state["user_id"] != "david":
                        st.error("No tienes permiso para modificar al Super Admin.")
                    else:
                        db.collection("usuarios").document(u_user).set({"usuario": u_user, "password_hash": generar_hash(u_pass), "rol": u_rol, "nombre": u_name})
                        st.success("Usuario creado/actualizado"); time.sleep(1); st.rerun()

        with t_db:
            if st.session_state["user_id"] == "david":
                st.warning("Zona de Peligro")
                if st.button("🔴 BORRAR TODO") and st.text_input("Confirmar:") == "BORRAR":
                    borrar_coleccion("alumnos"); borrar_coleccion("maestros_perfil"); borrar_coleccion("carga_academica"); borrar_coleccion("finanzas"); borrar_coleccion("notas")
                    borrar_coleccion("usuarios")
                    db.collection("usuarios").document("david").set({"usuario": "david", "pass": "admin123", "rol": "admin", "nombre": "David Fuentes (Dev)"})
                    st.success("Borrado completo.")
            else:
                st.info("Función reservada para el desarrollador.")

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
    
        