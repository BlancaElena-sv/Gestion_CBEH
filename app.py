import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime, date, timedelta
import base64
import time
import os
import streamlit.components.v1 as components
import re

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="EduManager", 
    layout="wide", 
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. SISTEMA DE SEGURIDAD Y CONEXIÓN
# ==========================================

db = None

@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        try:
            cred = None
            if os.path.exists("credenciales.json"): cred = credentials.Certificate("credenciales.json")
            elif os.path.exists("credenciales"): cred = credentials.Certificate("credenciales")
            elif "firebase_key" in st.secrets: cred = credentials.Certificate(dict(st.secrets["firebase_key"]))
            else: return None, "No se encontró el archivo de credenciales."
            
            firebase_admin.initialize_app(cred, {'storageBucket': 'gestioncbeh.firebasestorage.app'})
        except Exception as e: return None, str(e)
    
    try:
        return firestore.client(), None
    except Exception as e: return None, str(e)

db_conn, db_error = conectar_firebase()
if db_conn:
    db = db_conn
    try:
        users_ref = db.collection("usuarios").limit(1).stream()
        if not list(users_ref):
            db.collection("usuarios").document("david").set({
                "usuario": "david", "pass": "admin123", "rol": "admin", "nombre": "David Fuentes (Dev)"
            })
    except: pass

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
        except: 
            st.warning("⚠️")
            
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>EduManager</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #555;'>Colegio Profa. Blanca Elena de Hernández</h4>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("") 

        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("INICIAR SESIÓN", type="primary", use_container_width=True)
            
            if submitted:
                if user == "admin" and password == "master2026":
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = "admin"
                    st.session_state["user_name"] = "Super Admin"
                    st.session_state["user_id"] = "admin"
                    st.rerun()
                elif db:
                    try:
                        doc = db.collection("usuarios").document(user).get()
                        if doc.exists:
                            d = doc.to_dict()
                            if d["pass"] == password:
                                st.session_state["logged_in"] = True
                                st.session_state["user_role"] = d["rol"]
                                st.session_state["user_name"] = d.get("nombre", user)
                                st.session_state["user_id"] = user
                                st.rerun()
                            else: st.error("❌ Contraseña incorrecta")
                        else: st.error("❌ Usuario no encontrado")
                    except Exception as e: st.error(f"Error: {e}")
                else: st.error("⚠️ Sin conexión.")

        st.info("¿Olvidó su credencial? Solicite restablecimiento con la Administración.")
        st.markdown("<div style='text-align: center; color: grey; font-size: 11px; margin-top: 40px;'><p>© 2026 David Fuentes Development | Todos los derechos reservados.</p></div>", unsafe_allow_html=True)

def logout():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state["logged_in"] = False
    st.rerun()

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ==========================================
# 2. CONFIGURACIÓN ACADÉMICA
# ==========================================

MAT_KINDER = ["Relaciones Sociales y Afectivas", "Exploración y Experimentación con el Mundo", "Lenguaje y Comunicación", "Matemática", "Ciencia y Tecnología", "Cuerpo, Movimiento y Bienestar", "Conducta"]
MAT_I_CICLO = ["Comunicación", "Números y Formas", "Ciencia y Tecnología", "Ciudadanía y Valores", "Artes", "Desarrollo Corporal", "Ortografía", "Caligrafía", "Lectura", "Conducta"]
MAT_II_CICLO = ["Comunicación y Literatura", "Aritmética y Finanzas", "Ciencia y Tecnología", "Ciudadanía y Valores", "Artes", "Desarrollo Corporal", "Ortografía", "Caligrafía", "Lectura", "Conducta"]
MAT_III_CICLO = ["Lenguaje y Literatura", "Matemáticas y Datos", "Ciencia y Tecnología", "Ciudadanía y Valores", "Inglés", "Educación Física y Deportes", "Ortografía", "Caligrafía", "Lectura", "Conducta"]

MAPA_CURRICULAR = {
    "Kinder 4": MAT_KINDER, "Kinder 5": MAT_KINDER, "Preparatoria": MAT_KINDER,
    "Primer Grado": MAT_I_CICLO, "Segundo Grado": MAT_I_CICLO, "Tercer Grado": MAT_I_CICLO,
    "Cuarto Grado": MAT_II_CICLO, "Quinto Grado": MAT_II_CICLO, "Sexto Grado": MAT_II_CICLO,
    "Séptimo Grado": MAT_III_CICLO, "Octavo Grado": MAT_III_CICLO, "Noveno Grado": MAT_III_CICLO
}

LISTA_GRADOS_TODO = list(MAPA_CURRICULAR.keys())
LISTA_GRADOS_NOTAS = [g for g in LISTA_GRADOS_TODO if "Kinder" not in g and "Prepa" not in g]
LISTA_MESES = ["Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"]

# ==========================================
# 3. FUNCIONES AUXILIARES
# ==========================================
def subir_archivo(archivo, ruta):
    if not archivo or not db: return None
    try:
        b = storage.bucket()
        blob = b.blob(f"{ruta}/{archivo.name.replace(' ', '_')}")
        blob.upload_from_file(archivo)
        blob.make_public()
        return blob.public_url
    except: return None

def get_base64(path):
    try:
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except:
        return ""

def redondear_mined(valor):
    if valor is None: return 0.0
    parte_entera = int(valor)
    parte_decimal = valor - parte_entera
    if parte_decimal >= 0.5: return float(parte_entera + 1)
    else: return float(parte_entera)

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
    hoy = date.today()
    for d in docs:
        data = d.to_dict()
        fecha_db = data.get("fecha")
        if fecha_db:
            if isinstance(fecha_db, datetime): f_obj = fecha_db.date()
            else: f_obj = datetime.fromtimestamp(fecha_db.timestamp()).date()
            if f_obj == hoy and "Salario" in data.get("descripcion", "") and "Salario" in tipo_gasto:
                return True
    return False

def existe_duplicado(coleccion, campo_id, id_valor, descripcion):
    docs = db.collection(coleccion).where(campo_id, "==", id_valor).where("descripcion", "==", descripcion).stream()
    hoy = date.today()
    for d in docs:
        data = d.to_dict()
        fecha_db = data.get("fecha")
        if fecha_db:
            if isinstance(fecha_db, datetime): f_obj = fecha_db.date()
            else: f_obj = datetime.fromtimestamp(fecha_db.timestamp()).date()
            if f_obj == hoy: return True
    return False

# ==========================================
# 4. BARRA LATERAL
# ==========================================
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("Falta logo.png")
    
    nombre_mostrar = limpiar_nombre(st.session_state.get('user_name', 'Usuario'))
    st.write(f"👤 **{nombre_mostrar}**")
    
    if st.session_state["user_role"] == "admin":
        opcion_seleccionada = st.radio("Menú Admin:", ["Inicio", "Inscripción", "Consulta Alumnos", "Maestros", "Asistencia Global", "Notas", "Finanzas", "Configuración (Usuarios)"])
    else:
        opcion_seleccionada = st.radio("Menú Docente:", ["Inicio", "Mis Listados", "Tomar Asistencia", "Cargar Notas", "Ver Mis Cargas"])
    
    if "last_page" not in st.session_state: st.session_state.last_page = opcion_seleccionada
    if st.session_state.last_page != opcion_seleccionada:
        keys_to_clear = ["alum_view", "recibo", "pa", "recibo_temp", "pago_alum", "prof_view", "sel_prof_idx", "edit_prof_mode", "gasto_temp"]
        for key in keys_to_clear:
            if key in st.session_state: del st.session_state[key]
        st.session_state.last_page = opcion_seleccionada
        st.rerun()

    st.markdown("---")
    if st.button("Cerrar Sesión"): logout()
    st.markdown("---")
    st.caption("© 2026 David Fuentes | EduManager")

if not db and opcion_seleccionada != "Configuración (Usuarios)":
    st.error("⚠️ Base de Datos desconectada.")
    st.stop()

# ==========================================
# 5. CONTENIDO PRINCIPAL
# ==========================================

# --- INICIO ---
if opcion_seleccionada == "Inicio":
    st.title("🍎 Tablero Institucional")
    
    if st.session_state["user_role"] == "docente" and db:
        nombre_limpio = limpiar_nombre(st.session_state.get("user_name",""))
        found_prof = None
        try:
            q_prof = db.collection("maestros_perfil").where("nombre", "==", st.session_state["user_name"]).stream()
            for p in q_prof: found_prof = p.to_dict()
        except: pass
        if not found_prof:
            try:
                q_prof_clean = db.collection("maestros_perfil").where("nombre", "==", nombre_limpio).stream()
                for p in q_prof_clean: found_prof = p.to_dict()
            except: pass

        col_p1, col_p2 = st.columns([1, 4])
        with col_p1:
            if found_prof and found_prof.get('foto_url'): 
                st.image(found_prof['foto_url'], width=150)
            else: 
                st.markdown("<h1 style='text-align: center;'>👤</h1>", unsafe_allow_html=True)
        with col_p2:
            st.subheader(f"Bienvenido, {nombre_limpio}")
            st.info("Panel Docente - EduManager")
            if found_prof: st.write(f"📞 {found_prof.get('telefono','')} | 📧 {found_prof.get('email','')}")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Ciclo Lectivo", "2026")
        c2.metric("Usuario", limpiar_nombre(st.session_state['user_name']))
        c3.metric("Rol", st.session_state['user_role'].upper())

    st.markdown("---")
    st.subheader("📅 Agenda de Actividades")
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.info("**ESTADO: PERIODO DE INSCRIPCIÓN**")
        st.write("- Recepción de documentos.")
        st.write("- Actualización de datos.")
    with col_der:
        st.success("**PRÓXIMO: INICIO DE CLASES**")
        st.metric("Fecha", "26 de Enero", "2026")
    
    cronograma = [{"Fecha": "02 Ene - 18 Feb", "Actividad": "Matrícula Extraordinaria", "Estado": "En Curso"}, {"Fecha": "15 Ene", "Actividad": "Inicio de labores Docentes", "Estado": "Realizado"}, {"Fecha": "26 Ene", "Actividad": "Inicio de Clases (Oficial)", "Estado": "Programado"}, {"Fecha": "30 Ene", "Actividad": "Entrega Planificaciones", "Estado": "Pendiente"}]
    st.table(pd.DataFrame(cronograma))

# ==========================================
# MÓDULOS DE ADMINISTRADOR
# ==========================================
if st.session_state["user_role"] == "admin" and opcion_seleccionada != "Inicio":

    # --- INSCRIPCIÓN ---
    if opcion_seleccionada == "Inscripción":
        st.title("📝 Inscripción 2026")
        with st.form("fi"):
            c1, c2 = st.columns(2)
            nie = c1.text_input("NIE*")
            nom = c1.text_input("Nombres*")
            ape = c1.text_input("Apellidos*")
            gra = c2.selectbox("Grado", LISTA_GRADOS_TODO)
            tur = c2.selectbox("Turno", ["Matutino", "Vespertino"])
            enc = c2.text_input("Responsable")
            tel = c2.text_input("Teléfono")
            dir = st.text_area("Dirección")
            c3, c4 = st.columns(2)
            fot = c3.file_uploader("Foto", ["jpg","png"])
            doc = c4.file_uploader("Docs", ["pdf","jpg"], accept_multiple_files=True)
            if st.form_submit_button("Guardar"):
                try:
                    if nie and nom:
                        r = f"expedientes/{nie}"
                        urls = [subir_archivo(f, r) for f in (doc or [])]
                        db.collection("alumnos").document(nie).set({
                            "nie": nie, "nombre_completo": f"{nom} {ape}", "nombres": nom, "apellidos": ape,
                            "grado_actual": gra, "turno": tur, "estado": "Activo",
                            "encargado": {"nombre": enc, "telefono": tel, "direccion": dir},
                            "documentos": {"foto_url": subir_archivo(fot, r), "doc_urls": [u for u in urls if u]},
                            "fecha_registro": firestore.SERVER_TIMESTAMP
                        })
                        st.success("Guardado")
                    else: st.error("Faltan datos obligatorios.")
                except Exception as e: st.error(f"Error: {e}")

    # --- CONSULTA ALUMNOS ---
    elif opcion_seleccionada == "Consulta Alumnos":
        st.title("🔎 Expediente Electrónico")
        col_search, col_res = st.columns([1, 3])
        with col_search:
            st.markdown("### 🔍 Búsqueda")
            metodo = st.radio("Criterio:", ["NIE", "Grado"])
            if metodo == "NIE":
                val = st.text_input("Ingrese NIE:")
                if st.button("Buscar Expediente") and val:
                    d = db.collection("alumnos").document(val).get()
                    if d.exists: st.session_state.alum_view = d.to_dict()
                    else: st.error("No existe")
            else:
                g = st.selectbox("Filtrar Grado", ["Todos"] + LISTA_GRADOS_TODO)
                if g != "Todos":
                    res = [d.to_dict() for d in db.collection("alumnos").where("grado_actual", "==", g).stream()]
                else:
                    res = [d.to_dict() for d in db.collection("alumnos").limit(20).stream()]
                sel = st.selectbox("Seleccionar Alumno", ["Seleccionar..."] + [f"{r['nie']} - {r['nombre_completo']}" for r in res])
                if sel != "Seleccionar...":
                    nie_sel = sel.split(" - ")[0]
                    st.session_state.alum_view = db.collection("alumnos").document(nie_sel).get().to_dict()

        if "alum_view" in st.session_state:
            a = st.session_state.alum_view
            q_guia = db.collection("carga_academica").where("grado", "==", a['grado_actual']).where("es_guia", "==", True).stream()
            maestro_guia = "No Asignado"
            for d in q_guia: maestro_guia = d.to_dict()['nombre_docente']

            st.markdown("---")
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 3, 2])
                with c1: st.image(a.get('documentos',{}).get('foto_url', "https://via.placeholder.com/150"), width=130)
                with c2:
                    st.title(a['nombre_completo'])
                    st.markdown(f"#### **NIE:** {a['nie']}")
                    st.markdown(f"**Grado:** {a['grado_actual']} | **Turno:** {a.get('turno')}")
                    st.info(f"👨‍🏫 **Maestro Guía:** {maestro_guia}")
                with c3:
                    est = a.get('estado', 'Activo')
                    color = "green" if est == "Activo" else "red"
                    st.markdown(f"<h3 style='color:{color};text-align:center;border:2px solid {color};padding:5px;border-radius:10px;'>{est.upper()}</h3>", unsafe_allow_html=True)

            tabs = st.tabs(["📋 Datos y Documentos", "💰 Historial y Solvencia", "📊 Boleta de Notas", "⚙️ Edición Expediente"])
            
            with tabs[0]:
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.subheader("Datos Personales")
                    st.write(f"**Responsable:** {a.get('encargado',{}).get('nombre')}")
                    st.write(f"**Teléfono:** {a.get('encargado',{}).get('telefono')}")
                    st.write(f"**Dirección:** {a.get('encargado',{}).get('direccion')}")
                with col_d2:
                    st.subheader("📂 Documentos")
                    docs = a.get('documentos',{}).get('doc_urls', [])
                    if a.get('documentos',{}).get('doc_url'): docs.append(a.get('documentos',{}).get('doc_url'))
                    if docs:
                        for i, url in enumerate(list(set(docs))):
                            with st.expander(f"👁️ Visualizar Documento {i+1}"):
                                g_view = f"https://docs.google.com/gview?embedded=true&url={url}"
                                st.markdown(f'<iframe src="{g_view}" width="100%" height="500px" style="border:none;"></iframe>', unsafe_allow_html=True)
                                st.caption(f"[Enlace Directo]({url})")
                    else: st.info("Sin documentos.")

            with tabs[1]:
                col_fin1, col_fin2 = st.columns([2,1])
                with col_fin1:
                    st.subheader("Historial de Pagos")
                    pagos = db.collection("finanzas").where("alumno_nie", "==", a['nie']).where("tipo", "==", "ingreso").stream()
                    raw_pagos = [{"id": p.id, **p.to_dict()} for p in pagos]
                    if raw_pagos:
                        df_pagos = pd.DataFrame(raw_pagos)
                        st.dataframe(df_pagos[['fecha_legible', 'descripcion', 'monto']], use_container_width=True)
                        st.write("---")
                        st.write("**🖨️ Reimprimir Recibo Histórico**")
                        opciones_recibo = {f"{p['fecha_legible']} - {p['descripcion']} (${p['monto']})": p for p in raw_pagos}
                        sel_recibo = st.selectbox("Seleccione un pago:", ["Seleccionar..."] + list(opciones_recibo.keys()))
                        if sel_recibo != "Seleccionar...":
                            p_obj = opciones_recibo[sel_recibo]
                            if st.button("Visualizar Recibo"):
                                logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="60">' if logo else ""
                                html_recibo = f"""<div style="border: 2px solid #333; padding: 20px; font-family: 'Helvetica', sans-serif; max-width: 700px; margin: auto;"><table width="100%"><tr><td width="20%">{hi}</td><td width="60%" align="center"><h3 style="margin:0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h3><p style="margin:5px; font-size:12px;">San Felipe, San Bartolo, Ilopango</p><p style="margin:0; font-size:12px;"><b>COMPROBANTE DE INGRESO (COPIA)</b></p></td><td width="20%" align="right"><h4 style="margin:0; color: #d32f2f;">NO. {p_obj.get('id_short','000')}</h4><p style="font-size:12px;">{p_obj['fecha_legible']}</p></td></tr></table><hr><div style="padding: 10px;"><p><b>RECIBIMOS DE:</b> {p_obj.get('nombre_persona')}</p><p><b>LA CANTIDAD DE:</b> <span style="font-size:18px; font-weight:bold;">${p_obj['monto']:.2f}</span></p><p><b>POR CONCEPTO DE:</b> {p_obj['descripcion']}</p></div><br><br><table width="100%"><tr><td align="center" style="border-top: 1px solid #000; width:40%;">Entregado Por</td><td width="20%"></td><td align="center" style="border-top: 1px solid #000; width:40%;">Recibido (Caja)</td></tr></table></div>"""
                                components.html(f"""<html><body>{html_recibo}<br><center><button onclick="window.print()">🖨️ IMPRIMIR COPIA</button></center></body></html>""", height=400, scrolling=True)
                    else: st.info("Sin pagos registrados.")
                with col_fin2:
                    st.markdown("### 🎫 Solvencia")
                    periodo = st.selectbox("Examen:", ["I Trimestre", "II Trimestre", "III Trimestre", "Final"])
                    if st.button("Generar Taco"):
                        fecha = datetime.now().strftime("%d/%m/%Y")
                        logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="40">' if logo else ""
                        html = f"""<div style="font-family:monospace;width:300px;margin:auto;padding:10px;border:1px dashed black;text-align:center;"><div style="display:flex;align-items:center;justify-content:center;">{hi}<b>COLEGIO BLANCA ELENA</b></div><h4 style="background:black;color:white;margin:5px 0;">SOLVENCIA EXAMEN</h4><div style="text-align:left;font-size:11px;"><b>ALUMNO:</b> {a['nombre_completo']}<br><b>NIE:</b> {a['nie']}<br><b>PERIODO:</b> {periodo}<br><b>ESTADO:</b> SOLVENTE ✅</div><br><table border="1" style="width:100%;font-size:10px;border-collapse:collapse;text-align:center;"><tr><td>LUN</td><td>MAR</td><td>MIE</td><td>JUE</td><td>VIE</td></tr><tr><td height="30"></td><td></td><td></td><td></td><td></td></tr></table><br><span style="font-size:9px;">Fecha: {fecha}</span></div>"""
                        components.html(f"""<html><body>{html}<br><center><button onclick="window.print()">🖨️ IMPRIMIR</button></center></body></html>""", height=350)

            with tabs[2]:
                st.subheader("Boleta Oficial")
                notas = db.collection("notas").where("nie", "==", a['nie']).stream()
                nm = {}
                for doc in notas:
                    dd = doc.to_dict()
                    if dd['materia'] not in nm: nm[dd['materia']] = {}
                    nm[dd['materia']][dd['mes']] = dd['promedio_final']
                filas = []
                malla = MAPA_CURRICULAR.get(a['grado_actual'], [])
                for mat in malla:
                    if mat in nm:
                        n = nm[mat]
                        t1 = redondear_mined((n.get("Febrero",0)+n.get("Marzo",0)+n.get("Abril",0))/3)
                        t2 = redondear_mined((n.get("Mayo",0)+n.get("Junio",0)+n.get("Julio",0))/3)
                        t3 = redondear_mined((n.get("Agosto",0)+n.get("Septiembre",0)+n.get("Octubre",0))/3)
                        fin = redondear_mined((t1+t2+t3)/3)
                        filas.append(f"<tr><td style='text-align:left'>{mat}</td><td>{n.get('Febrero','-')}</td><td>{n.get('Marzo','-')}</td><td>{n.get('Abril','-')}</td><td style='background:#eee'><b>{t1}</b></td><td>{n.get('Mayo','-')}</td><td>{n.get('Junio','-')}</td><td>{n.get('Julio','-')}</td><td style='background:#eee'><b>{t2}</b></td><td>{n.get('Agosto','-')}</td><td>{n.get('Septiembre','-')}</td><td>{n.get('Octubre','-')}</td><td style='background:#eee'><b>{t3}</b></td><td style='background:#333;color:white'><b>{fin}</b></td></tr>")
                logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="60">' if logo else ""
                sello = get_base64("sello.png"); hs = f'<img src="{sello}" height="80">' if sello else ""
                html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:20px'><h2>COLEGIO PROFA. BLANCA ELENA</h2><h4>INFORME DE NOTAS</h4></div></div><p><b>Alumno:</b> {a['nombre_completo']} | <b>Grado:</b> {a['grado_actual']} | <b>Guía:</b> {maestro_guia}</p><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#ddd;font-weight:bold;'><td>ASIGNATURA</td><td>F</td><td>M</td><td>A</td><td>T1</td><td>M</td><td>J</td><td>J</td><td>T2</td><td>A</td><td>S</td><td>O</td><td>T3</td><td>FIN</td></tr>{"".join(filas)}</table><br><br><br><div style='display:flex;justify-content:space-between;align-items:end;padding:0 50px;'><div style='text-align:center;width:30%'><div style='border-top:1px solid black;width:100%'>Orientador</div></div><div style='text-align:center;'>{hs}</div><div style='text-align:center;width:30%'><div style='border-top:1px solid black;width:100%'>Dirección</div></div></div></div>"""
                components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR BOLETA</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

            with tabs[3]:
                st.subheader("Gestión del Expediente")
                with st.form("edit_full"):
                    c1, c2 = st.columns(2)
                    nn = c1.text_input("Nombres", a['nombres'])
                    na = c2.text_input("Apellidos", a['apellidos'])
                    ng = c1.selectbox("Grado", LISTA_GRADOS_TODO, index=LISTA_GRADOS_TODO.index(a['grado_actual']) if a['grado_actual'] in LISTA_GRADOS_TODO else 0)
                    nt = c2.selectbox("Turno", ["Matutino", "Vespertino"], index=0)
                    ne = c1.selectbox("Estado", ["Activo", "Inactivo", "Retirado"], index=["Activo", "Inactivo", "Retirado"].index(a.get('estado', 'Activo')))
                    nres = c2.text_input("Responsable", a.get('encargado',{}).get('nombre',''))
                    ntel = c1.text_input("Teléfono", a.get('encargado',{}).get('telefono',''))
                    ndir = c2.text_area("Dirección", a.get('encargado',{}).get('direccion',''))
                    st.markdown("---")
                    new_foto = st.file_uploader("Actualizar Foto", ["jpg", "png"], key="up_foto")
                    new_doc = st.file_uploader("Adjuntar Documento", ["pdf", "jpg", "png"], key="up_doc")
                    if st.form_submit_button("💾 Guardar Cambios"):
                        update_data = {"nombres": nn, "apellidos": na, "nombre_completo": f"{nn} {na}", "grado_actual": ng, "turno": nt, "estado": ne, "encargado": {"nombre": nres, "telefono": ntel, "direccion": ndir}}
                        if new_foto:
                            url = subir_archivo(new_foto, f"expedientes/{a['nie']}")
                            if url: update_data["documentos.foto_url"] = url
                        if new_doc:
                            url = subir_archivo(new_doc, f"expedientes/{a['nie']}")
                            if url:
                                cds = a.get('documentos',{}).get('doc_urls', [])
                                cds.append(url)
                                update_data["documentos.doc_urls"] = cds
                        db.collection("alumnos").document(a['nie']).update(update_data)
                        st.success("Expediente actualizado."); time.sleep(1); st.rerun()

    # --- 4. MAESTROS ---
    elif opcion_seleccionada == "Maestros":
        st.title("👩‍🏫 Gestión Plantel Docente")
        docs_m = db.collection("maestros_perfil").stream()
        lista_profes = []
        for d in docs_m:
            dd = d.to_dict()
            dd['id'] = d.id
            if 'nombre' not in dd: dd['nombre'] = "Desconocido"
            lista_profes.append(dd)
        
        # --- AQUÍ ESTÁ LA CORRECCIÓN: ELIMINAR DUPLICADOS EN LA LISTA ---
        # 1. Crear conjunto de nombres únicos
        nombres_unicos = sorted(list(set([f"{p.get('codigo','S/C')} - {p['nombre']}" for p in lista_profes])))
        opciones_prof = ["➕ Registrar Nuevo Maestro"] + nombres_unicos
        
        col_sel, _ = st.columns([2, 1])
        with col_sel:
            idx = st.session_state.get('sel_prof_idx', 0)
            sel_prof = st.selectbox("Seleccionar Docente:", opciones_prof, index=idx)
        st.markdown("---")

        if sel_prof == "➕ Registrar Nuevo Maestro":
            with st.form("new_prof"):
                c1, c2 = st.columns(2)
                cod = c1.text_input("Código")
                nom = c2.text_input("Nombre")
                tel = c1.text_input("Teléfono")
                email = c2.text_input("Email")
                dir = st.text_area("Dirección")
                foto = st.file_uploader("Foto")
                if st.form_submit_button("Guardar"):
                    if nom:
                        url = subir_archivo(foto, f"profesores/{cod}")
                        db.collection("maestros_perfil").add({"codigo": cod, "nombre": nom, "telefono": tel, "email": email, "direccion": dir, "foto_url": url, "fecha_ingreso": datetime.now().strftime("%d/%m/%Y"), "activo": True})
                        st.success("Guardado"); time.sleep(1); st.rerun()
                    else: st.error("Nombre requerido")
        else:
            if lista_profes:
                try:
                    # Búsqueda robusta por string coincidente
                    pid = next(p['id'] for p in lista_profes if f"{p.get('codigo','S/C')} - {p['nombre']}" == sel_prof)
                    prof_data = next(p for p in lista_profes if p['id'] == pid)
                    
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([1, 3, 1])
                        with c1: st.image(prof_data.get('foto_url', "https://via.placeholder.com/150"), width=120)
                        with c2:
                            st.title(prof_data.get('nombre', 'Sin Nombre'))
                            st.caption(f"Código: {prof_data.get('codigo','S/C')}")
                            st.write(f"📞 {prof_data.get('telefono','-')} | 📧 {prof_data.get('email','-')}")
                        with c3:
                            if st.button("✏️ Editar Perfil"): st.session_state.edit_prof_mode = True

                    if st.session_state.get("edit_prof_mode"):
                        with st.form("edit_prof_form"):
                            nc = st.text_input("Nombre", prof_data.get('nombre', ''))
                            nt = st.text_input("Teléfono", prof_data.get('telefono',''))
                            nf = st.file_uploader("Nueva Foto", ["jpg", "png"])
                            if st.form_submit_button("Guardar Cambios"):
                                upd = {"nombre": nc, "telefono": nt}
                                if nf:
                                    u = subir_archivo(nf, f"profesores/{prof_data.get('codigo','SN')}")
                                    if u: upd["foto_url"] = u
                                db.collection("maestros_perfil").document(pid).update(upd)
                                st.session_state.edit_prof_mode = False
                                st.success("Actualizado"); time.sleep(1); st.rerun()
                    
                    tabs_m = st.tabs(["📚 Carga Académica", "💰 Historial Financiero"])

                    with tabs_m[0]:
                        c_asig, c_tabla = st.columns([1, 2])
                        with c_asig:
                            st.markdown("#### Asignar Nueva Materia")
                            g_sel = st.selectbox("Grado", LISTA_GRADOS_TODO, key="g_prof")
                            mats_disp = MAPA_CURRICULAR.get(g_sel, [])
                            with st.form("add_carga_prof"):
                                m_sel = st.multiselect("Materias", mats_disp)
                                guia = st.checkbox("¿Es Guía?")
                                if st.form_submit_button("Guardar Carga"):
                                    db.collection("carga_academica").add({"id_docente": pid, "nombre_docente": prof_data.get('nombre','Desconocido'), "grado": g_sel, "materias": m_sel, "es_guia": guia})
                                    st.success("Asignado"); time.sleep(0.5); st.rerun()

                        with c_tabla:
                            st.markdown("#### Carga Actual")
                            cargas = db.collection("carga_academica").where("id_docente", "==", pid).stream()
                            for c in cargas:
                                cd = c.to_dict()
                                with st.expander(f"{cd.get('grado','?')} {'(GUIA)' if cd.get('es_guia') else ''}"):
                                    st.write(", ".join(cd.get('materias',[])))
                                    if st.button("Eliminar", key=c.id):
                                        db.collection("carga_academica").document(c.id).delete(); st.rerun()

                    with tabs_m[1]:
                        with st.expander("➕ Registrar Movimiento"):
                            with st.form("ffin"):
                                tipo = st.selectbox("Tipo", ["Pago Salario (Egreso)", "Préstamo (Deuda)", "Abono Deuda (Ingreso)"])
                                monto = st.number_input("Monto", min_value=0.01)
                                desc = st.text_input("Detalle")
                                if st.form_submit_button("Registrar"):
                                    # CHECK DUPLICADOS MAESTRO
                                    desc_full = f"{tipo} - {desc}"
                                    if verificar_pago_duplicado_hoy(pid, f"{tipo}") and "Salario" in tipo:
                                         st.error("⛔ Transacción duplicada (Salario hoy).")
                                    else:
                                        db.collection("finanzas").add({"tipo": "egreso" if "Salario" in tipo else ("ingreso" if "Abono" in tipo else "interno"), "categoria_persona": "docente", "docente_id": pid, "nombre_persona": prof_data.get('nombre',''), "descripcion": desc_full, "monto": monto, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": datetime.now().strftime("%d/%m/%Y")})
                                        st.success("Registrado")
                        movs = db.collection("finanzas").where("docente_id", "==", pid).stream()
                        lm = [m.to_dict() for m in movs]
                        lm.sort(key=lambda x: x.get('fecha_legible', ''), reverse=True)
                        if lm: st.dataframe(pd.DataFrame(lm)[['fecha_legible','descripcion','monto']], use_container_width=True)
                        else: st.info("Sin historial.")

                except Exception as e:
                    st.error(f"Error cargando docente (Datos incompletos): {e}")

    # --- 5. ASISTENCIA GLOBAL ---
    elif opcion_seleccionada == "Asistencia Global":
        st.title("📅 Reporte de Asistencia Global")
        c1, c2, c3 = st.columns(3)
        g = c1.selectbox("Grado", LISTA_GRADOS_TODO)
        f_ini = c2.date_input("Desde:", date.today())
        f_fin = c3.date_input("Hasta:", date.today())
        
        if st.button("Generar Reporte"):
            docs = db.collection("asistencia").where("grado", "==", g).stream()
            stats = {}
            alums = db.collection("alumnos").where("grado_actual", "==", g).stream()
            for a in alums: stats[a.to_dict()['nie']] = {"Nombre": a.to_dict()['nombre_completo'], "P": 0, "A": 0, "Obs": []}
            total_dias = 0
            
            for d in docs:
                data_doc = d.to_dict()
                fecha_doc = data_doc.get("fecha")
                if not fecha_doc: continue
                if isinstance(fecha_doc, datetime): f_obj = fecha_doc.date()
                else: f_obj = datetime.fromtimestamp(fecha_doc.timestamp()).date()
                
                if f_ini <= f_obj <= f_fin:
                    total_dias += 1
                    regs = data_doc.get('registros', {})
                    obs_regs = data_doc.get('observaciones', {})
                    for nie, est in regs.items():
                        if nie in stats: 
                            if est == "Presente": stats[nie]["P"] += 1
                            elif est == "Ausente": 
                                stats[nie]["A"] += 1
                                if obs_regs.get(nie): stats[nie]["Obs"].append(f"{f_obj.strftime('%d/%m')}: {obs_regs[nie]}")
            
            if total_dias > 0:
                data = [{"Alumno": v["Nombre"], "Asistencias": v["P"], "Faltas": v["A"], "% Asist": f"{(v['P']/total_dias)*100:.0f}%", "Observaciones": ", ".join(v["Obs"])} for v in stats.values()]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            else: st.info("No hay tomas de asistencia registradas para este periodo.")

    # --- 6. NOTAS (CALCULO AUTOMATICO) ---
    elif opcion_seleccionada == "Notas":
        st.title("📊 Admin Notas")
        c1, c2, c3 = st.columns(3)
        g = c1.selectbox("Grado", ["Select..."]+LISTA_GRADOS_NOTAS)
        mp = MAPA_CURRICULAR.get(g,[]) if g!="Select..." else []
        m = c2.selectbox("Materia", ["Select..."]+mp)
        mes = c3.selectbox("Mes", LISTA_MESES)
        
        if g!="Select..." and m!="Select...":
            docs = db.collection("alumnos").where("grado_actual", "==", g).stream()
            lista = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
            if not lista: st.warning("Sin alumnos")
            else:
                df = pd.DataFrame(lista).sort_values("Nombre")
                id_doc = f"{g}_{m}_{mes}".replace(" ","_")
                cols = ["Nota Conducta"] if m == "Conducta" else ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
                doc_ref = db.collection("notas_mensuales").document(id_doc).get()
                
                if doc_ref.exists:
                    dd = doc_ref.to_dict().get('detalles', {})
                    for c in cols: df[c] = df["NIE"].map(lambda x: dd.get(x, {}).get(c, 0.0))
                else:
                    for c in cols: df[c] = 0.0
                
                if m == "Conducta":
                    df["Promedio"] = df[cols[0]]
                else:
                    df["Promedio"] = (df["Act1 (25%)"]*0.25 + df["Act2 (25%)"]*0.25 + 
                                      df["Alt1 (10%)"]*0.10 + df["Alt2 (10%)"]*0.10 + 
                                      df["Examen (30%)"]*0.30).apply(redondear_mined)

                cfg = {"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True, width="medium"), "Promedio": st.column_config.NumberColumn(disabled=True)}
                for c in cols: cfg[c] = st.column_config.NumberColumn(min_value=0.0, max_value=10.0, step=0.01)
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
                        batch.set(ref, {"nie": r["NIE"], "grado": g, "materia": m, "mes": mes, "promedio_final": prom_r})
                    db.collection("notas_mensuales").document(id_doc).set({"grado": g, "materia": m, "mes": mes, "detalles": detalles})
                    batch.commit()
                    st.success("Guardado")
                    time.sleep(1); st.rerun()
                
                st.divider()
                st.subheader(f"📋 Registro Acumulado Detallado - {m}")
                rows_acumulados = []
                for mes_iter in LISTA_MESES:
                    id_history = f"{g}_{m}_{mes_iter}".replace(" ","_")
                    doc_h = db.collection("notas_mensuales").document(id_history).get()
                    if doc_h.exists:
                        data_h = doc_h.to_dict().get("detalles", {})
                        for nie_iter, notas_iter in data_h.items():
                            nom_alum = next((x['Nombre'] for x in lista if x['NIE'] == nie_iter), nie_iter)
                            if m == "Conducta":
                                rows_acumulados.append({"Mes": mes_iter, "NIE": nie_iter, "Nombre": nom_alum, "Nota Conducta": notas_iter.get("Nota Conducta", 0), "Promedio": notas_iter.get("Promedio", 0)})
                            else:
                                rows_acumulados.append({"Mes": mes_iter, "NIE": nie_iter, "Nombre": nom_alum, "Act1": notas_iter.get("Act1 (25%)", 0), "Act2": notas_iter.get("Act2 (25%)", 0), "Alt1": notas_iter.get("Alt1 (10%)", 0), "Alt2": notas_iter.get("Alt2 (10%)", 0), "Examen": notas_iter.get("Examen (30%)", 0), "Promedio": notas_iter.get("Promedio", 0)})
                if rows_acumulados:
                    df_ac = pd.DataFrame(rows_acumulados)
                    df_ac['Mes_Indice'] = df_ac['Mes'].apply(lambda x: LISTA_MESES.index(x))
                    df_ac = df_ac.sort_values(by=['Mes_Indice', 'Nombre']).drop(columns=['Mes_Indice'])
                    st.dataframe(df_ac, use_container_width=True, hide_index=True)

    # --- 7. FINANZAS ---
    elif opcion_seleccionada == "Finanzas":
        st.title("💰 Administración Financiera")
        t1, t2, t3, t4 = st.tabs(["📊 Corte de Caja", "➕ Cobros (Alumnos)", "➖ Gastos Operativos", "📜 Reportes & Reimpresión"])
        
        with t1:
            c_date, _ = st.columns([1, 2])
            fecha_corte = c_date.date_input("Fecha de Corte", date.today())
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
            n = st.text_input("Buscar NIE del Alumno para Cobro:")
            if st.button("Buscar Alumno") and n:
                d = db.collection("alumnos").document(n).get()
                if d.exists: st.session_state.pago_alum = d.to_dict()
                else: st.error("No encontrado")
            
            if "pago_alum" in st.session_state:
                pa = st.session_state.pago_alum
                st.info(f"Cobrando a: **{pa['nombre_completo']}**")
                with st.form("form_cobro"):
                    tipo_c = st.selectbox("Tipo de Cobro", ["Colegiatura", "Matrícula", "Uniformes", "Otros"])
                    det_c = st.text_input("Detalle (Ej: Mes de Marzo)")
                    monto = st.number_input("Monto ($)", min_value=0.01)
                    obs = st.text_input("Observaciones")
                    if st.form_submit_button("✅ Registrar Ingreso"):
                        desc_full = f"{tipo_c} - {det_c}"
                        if existe_duplicado("finanzas", "alumno_nie", n, desc_full):
                            st.error("⛔ Transacción duplicada (Mismo alumno, mismo concepto hoy).")
                        else:
                            recibo_data = {"tipo": "ingreso", "descripcion": desc_full, "monto": monto, "alumno_nie": n, "nombre_persona": pa['nombre_completo'], "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": datetime.now().strftime("%d/%m/%Y"), "id_short": str(int(time.time()))[-6:]}
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
                # LÓGICA VINCULACIÓN MAESTROS EN GASTOS
                maestro_seleccionado = None
                per = ""
                if tp == "Salario":
                    # Cargar maestros para vincular ID
                    ms = db.collection("maestros_perfil").stream()
                    l_ms = {m.to_dict()['nombre']: m.id for m in ms}
                    nom_sel = st.selectbox("Seleccionar Maestro:", list(l_ms.keys()))
                    if nom_sel: maestro_seleccionado = l_ms[nom_sel]; per = nom_sel
                else:
                    per = st.text_input("Pagado a (Nombre/Empresa)")
                
                mt = st.number_input("Monto", min_value=0.01)
                det_g = st.text_input("Detalle")
                
                if st.form_submit_button("Registrar"):
                    desc_full = f"{tp} - {det_g}"
                    # CHECK ANTI DUPLICADOS GASTO
                    duplicado = False
                    if tp == "Salario" and maestro_seleccionado:
                        if verificar_pago_duplicado_hoy(maestro_seleccionado, "Salario"): duplicado = True
                    
                    if duplicado:
                        st.error("⛔ Pago duplicado detectado (Salario ya registrado hoy para este docente).")
                    else:
                        gasto_data = {"tipo": "egreso", "descripcion": desc_full, "monto": mt, "nombre_persona": per, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": datetime.now().strftime("%d/%m/%Y"), "id_short": str(int(time.time()))[-6:]}
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
            c_f1, c_f2, c_f3, c_f4 = st.columns(4)
            # Filtro Rango Rápido
            filtro_rango = c_f1.selectbox("Rango de Tiempo", ["Este Mes", "Mes Pasado", "Últimos 3 Meses", "Últimos 6 Meses", "Este Año", "Personalizado"])
            
            # Lógica de fechas automática
            hoy = date.today()
            if filtro_rango == "Este Mes":
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
            else: # Personalizado
                f_inicio = c_f2.date_input("Desde", hoy.replace(day=1))
                f_fin = c_f3.date_input("Hasta", hoy)

            f_tipo = c_f4.multiselect("Tipo:", ["ingreso", "egreso"], default=["ingreso", "egreso"])
            
            # Filtro fecha en Python
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
                # Manejar tipos de fecha
                if isinstance(d_date, datetime): actual = d_date.replace(tzinfo=None)
                else: actual = datetime.fromtimestamp(d_date.timestamp())
                
                if dt_ini <= actual <= dt_fin:
                    c_typ = d['tipo'] in f_tipo
                    if c_typ:
                        data_raw.append(d)
                        if d['tipo'] == 'ingreso': tot_ing += d['monto']
                        elif d['tipo'] == 'egreso': tot_egr += d['monto']
            
            # Tarjetas Resumen
            st.divider()
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Ingresos", f"${tot_ing:.2f}", border=True)
            k2.metric("Total Egresos", f"${tot_egr:.2f}", delta_color="inverse", border=True)
            k3.metric("Balance Periodo", f"${tot_ing - tot_egr:.2f}", border=True)
            st.divider()

            data_raw.sort(key=lambda x: x.get('fecha_legible', ''), reverse=True)
            if data_raw:
                df_rep = pd.DataFrame(data_raw)
                st.dataframe(df_rep[['fecha_legible','tipo','nombre_persona','descripcion','monto']], use_container_width=True)
                
                # REPORTE IMPRESO CON FILTROS
                if st.button("🖨️ Imprimir Reporte Generado"):
                    logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="50">' if logo else ""
                    rows_html = ""
                    for item in data_raw:
                        color_row = "#e8f5e9" if item['tipo'] == 'ingreso' else "#ffebee"
                        rows_html += f"<tr style='background:{color_row};'><td>{item['fecha_legible']}</td><td>{item.get('id_short','-')}</td><td>{item['nombre_persona']}</td><td>{item['descripcion']}</td><td align='right'>${item['monto']:.2f}</td></tr>"
                    
                    html_reporte = f"""
                    <div style="font-family:Arial; padding:20px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #333; padding-bottom:10px;">
                            <div style="display:flex; align-items:center; gap:15px;">
                                {hi}
                                <div><h2 style="margin:0;">COLEGIO BLANCA ELENA</h2><p style="margin:0;">REPORTE FINANCIERO ({filtro_rango})</p></div>
                            </div>
                            <div style="text-align:right;"><p><b>Desde:</b> {f_inicio.strftime('%d/%m/%Y')}<br><b>Hasta:</b> {f_fin.strftime('%d/%m/%Y')}</p></div>
                        </div>
                        <br>
                        <div style="display:flex; gap:20px; margin-bottom:20px;">
                            <div style="background:#e8f5e9; padding:10px; border:1px solid #4caf50; border-radius:5px; flex:1; text-align:center;"><h4 style="margin:0; color:#2e7d32;">INGRESOS</h4><h2 style="margin:0;">${tot_ing:.2f}</h2></div>
                            <div style="background:#ffebee; padding:10px; border:1px solid #e57373; border-radius:5px; flex:1; text-align:center;"><h4 style="margin:0; color:#c62828;">EGRESOS</h4><h2 style="margin:0;">${tot_egr:.2f}</h2></div>
                            <div style="background:#f5f5f5; padding:10px; border:1px solid #999; border-radius:5px; flex:1; text-align:center;"><h4 style="margin:0;">BALANCE</h4><h2 style="margin:0;">${tot_ing - tot_egr:.2f}</h2></div>
                        </div>
                        <table style="width:100%; border-collapse:collapse; font-size:12px;" border="1" bordercolor="#ddd">
                            <tr style="background:#333; color:white;"><th padding="5">Fecha</th><th>Ref</th><th>Persona/Entidad</th><th>Descripción</th><th>Monto</th></tr>
                            {rows_html}
                        </table>
                        <br><br><div style="text-align:center;">__________________________<br>Firma Dirección</div>
                    </div>
                    """
                    components.html(f"""<html><body>{html_reporte}<br><center><button onclick="window.print()" style="background:#333; color:white; padding:10px 20px; cursor:pointer;">🖨️ IMPRIMIR REPORTE PDF</button></center></body></html>""", height=600, scrolling=True)

            else: st.info("No hay registros en este rango.")

    # --- 8. CONFIGURACIÓN (USUARIOS) (NUEVO MODULO) ---
    elif opcion_seleccionada == "Configuración (Usuarios)":
        st.header("⚙️ Configuración")
        t_usr, t_db = st.tabs(["👥 Usuarios", "⚠️ Base de Datos"])
        
        with t_usr:
            st.subheader("Crear / Editar Credenciales")
            ur = db.collection("usuarios").stream()
            lu = [u.to_dict() for u in ur]
            # PROTECCIÓN DE SUPER ADMIN (Solo david ve a david)
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
                        db.collection("usuarios").document(u_user).set({"usuario": u_user, "pass": u_pass, "rol": u_rol, "nombre": u_name})
                        st.success("Usuario creado/actualizado"); time.sleep(1); st.rerun()

        with t_db:
            if st.session_state["user_id"] == "david":
                st.warning("Zona de Peligro")
                if st.button("🔴 BORRAR TODO") and st.text_input("Confirmar:") == "BORRAR":
                    borrar_coleccion("alumnos"); borrar_coleccion("maestros_perfil"); borrar_coleccion("carga_academica"); borrar_coleccion("finanzas"); borrar_coleccion("notas")
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
            docs = db.collection("alumnos").where("grado_actual", "==", g).stream()
            lista = sorted([d.to_dict()['nombre_completo'] for d in docs])
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
        fecha_asist = c1.date_input("Fecha:", date.today())
        grado_asist = c2.selectbox("Grado:", LISTA_GRADOS_TODO)
        if grado_asist:
            id_asistencia = f"{fecha_asist}_{grado_asist}"
            doc_ref = db.collection("asistencia").document(id_asistencia)
            doc_snap = doc_ref.get()
            alumnos_ref = db.collection("alumnos").where("grado_actual", "==", grado_asist).stream()
            lista_alumnos = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in alumnos_ref]
            lista_alumnos.sort(key=lambda x: x["Nombre"])
            if lista_alumnos:
                datos = doc_snap.to_dict().get("registros", {}) if doc_snap.exists else {}
                observaciones = doc_snap.to_dict().get("observaciones", {}) if doc_snap.exists else {}
                
                data_editor = []
                for alum in lista_alumnos:
                    data_editor.append({
                        "NIE": alum["NIE"], 
                        "Nombre": alum["Nombre"], 
                        "Estado": datos.get(alum["NIE"], "Presente"),
                        "Observación": observaciones.get(alum["NIE"], "")
                    })
                
                df_asist = pd.DataFrame(data_editor)
                ed = st.data_editor(df_asist, column_config={
                    "NIE": st.column_config.TextColumn(disabled=True),
                    "Nombre": st.column_config.TextColumn(disabled=True),
                    "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente", "Tardanza", "Permiso"], required=True),
                    "Observación": st.column_config.TextColumn(width="medium")
                }, hide_index=True, use_container_width=True, key=id_asistencia)
                
                if st.button("💾 Guardar Asistencia"):
                    regs = {r["NIE"]: r["Estado"] for r in ed.to_dict(orient="records")}
                    obs_regs = {r["NIE"]: r["Observación"] for r in ed.to_dict(orient="records")}
                    doc_ref.set({
                        "fecha": datetime.combine(fecha_asist, datetime.min.time()), 
                        "grado": grado_asist, 
                        "registros": regs,
                        "observaciones": obs_regs
                    })
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
            docs = db.collection("alumnos").where("grado_actual", "==", g).stream()
            lista = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
            if not lista: st.warning("Sin alumnos")
            else:
                df = pd.DataFrame(lista).sort_values("Nombre")
                id_doc = f"{g}_{m}_{mes}".replace(" ","_")
                cols = ["Nota Conducta"] if m == "Conducta" else ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
                doc_ref = db.collection("notas_mensuales").document(id_doc).get()
                if doc_ref.exists:
                    dd = doc_ref.to_dict().get('detalles', {})
                    for c in cols: df[c] = df["NIE"].map(lambda x: dd.get(x, {}).get(c, 0.0))
                else:
                    for c in cols: df[c] = 0.0
                
                # CALCULO REAL TIME
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
                        batch.set(ref, {"nie": r["NIE"], "grado": g, "materia": m, "mes": mes, "promedio_final": prom_r})
                    db.collection("notas_mensuales").document(id_doc).set({"grado": g, "materia": m, "mes": mes, "detalles": detalles})
                    batch.commit()
                    st.success("Guardado")
                    time.sleep(1); st.rerun()
                
                st.divider()
                st.subheader(f"📋 Registro Acumulado Detallado - {m}")
                rows_acumulados = []
                for mes_iter in LISTA_MESES:
                    id_history = f"{g}_{m}_{mes_iter}".replace(" ","_")
                    doc_h = db.collection("notas_mensuales").document(id_history).get()
                    if doc_h.exists:
                        data_h = doc_h.to_dict().get("detalles", {})
                        for nie_iter, notas_iter in data_h.items():
                            nom_alum = next((x['Nombre'] for x in lista if x['NIE'] == nie_iter), nie_iter)
                            if m == "Conducta":
                                rows_acumulados.append({"Mes": mes_iter, "NIE": nie_iter, "Nombre": nom_alum, "Nota Conducta": notas_iter.get("Nota Conducta", 0), "Promedio": notas_iter.get("Promedio", 0)})
                            else:
                                rows_acumulados.append({"Mes": mes_iter, "NIE": nie_iter, "Nombre": nom_alum, "Act1": notas_iter.get("Act1 (25%)", 0), "Act2": notas_iter.get("Act2 (25%)", 0), "Alt1": notas_iter.get("Alt1 (10%)", 0), "Alt2": notas_iter.get("Alt2 (10%)", 0), "Examen": notas_iter.get("Examen (30%)", 0), "Promedio": notas_iter.get("Promedio", 0)})
                if rows_acumulados:
                    df_ac = pd.DataFrame(rows_acumulados)
                    df_ac['Mes_Indice'] = df_ac['Mes'].apply(lambda x: LISTA_MESES.index(x))
                    df_ac = df_ac.sort_values(by=['Mes_Indice', 'Nombre']).drop(columns=['Mes_Indice'])
                    st.dataframe(df_ac, use_container_width=True, hide_index=True)

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
        if not found:
            st.info("No se encontraron cargas asignadas a su nombre exacto. Contacte a Dirección.")