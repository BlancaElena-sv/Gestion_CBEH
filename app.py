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
import pytz

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="EduManager", 
    layout="wide", 
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# ==========================================
# 0. CONFIGURACIÓN DE ZONA HORARIA
# ==========================================
TZ_SV = pytz.timezone("America/El_Salvador")

def obtener_fecha_hoy():
    return datetime.now(TZ_SV).date()

def obtener_hora_actual():
    return datetime.now(TZ_SV).strftime("%d/%m/%Y %H:%M")

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
        st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>EduManager</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #555;'>Colegio Profa. Blanca Elena de Hernández</h4>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("INICIAR SESIÓN", type="primary", use_container_width=True)
            
            if submitted:
                if user == "admin" and password == "master2026":
                    st.session_state.update({"logged_in": True, "user_role": "admin", "user_name": "Super Admin", "user_id": "admin"})
                    st.rerun()
                elif db:
                    doc = db.collection("usuarios").document(user).get()
                    if doc.exists:
                        d = doc.to_dict()
                        if d["pass"] == password:
                            st.session_state.update({"logged_in": True, "user_role": d["rol"], "user_name": d.get("nombre", user), "user_id": user})
                            st.rerun()
                        else: st.error("❌ Contraseña incorrecta")
                    else: st.error("❌ Usuario no encontrado")

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
# 3. FUNCIONES AUXILIARES (MODIFICADAS)
# ==========================================
def subir_archivo(archivo, ruta):
    if not archivo or not db: return None
    try:
        b = storage.bucket()
        # Limpieza de nombre para evitar enlaces rotos
        ext = os.path.splitext(archivo.name)[1]
        nombre_seguro = f"{int(time.time())}{ext}"
        blob = b.blob(f"{ruta}/{nombre_seguro}")
        blob.upload_from_file(archivo, content_type=archivo.type)
        blob.make_public()
        # Se agrega timestamp para evitar caché de imagen vieja
        return f"{blob.public_url}?t={int(time.time())}"
    except: return None

def get_base64(path):
    try:
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

def redondear_mined(valor):
    if valor is None: return 0.0
    parte_entera = int(valor)
    parte_decimal = valor - parte_entera
    return float(parte_entera + 1) if parte_decimal >= 0.5 else float(parte_entera)

# ==========================================
# 4. BARRA LATERAL
# ==========================================
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("Falta logo.png")
    
    st.write(f"👤 **{limpiar_nombre(st.session_state.get('user_name', 'Usuario'))}**")
    
    menu = ["Inicio", "Inscripción", "Consulta Alumnos", "Maestros", "Asistencia Global", "Notas", "Finanzas", "Configuración (Usuarios)"] if st.session_state["user_role"] == "admin" else ["Inicio", "Mis Listados", "Tomar Asistencia", "Cargar Notas", "Ver Mis Cargas", "Expediente Alumnos"]
    opcion_seleccionada = st.radio("Menú:", menu, key="menu_v2026")

    if st.button("Cerrar Sesión"): logout()

# ==========================================
# 5. CONTENIDO PRINCIPAL
# ==========================================

# --- INICIO ---
if opcion_seleccionada == "Inicio":
    st.title("🍎 Tablero Institucional")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo Lectivo", "2026")
    c2.metric("Usuario", limpiar_nombre(st.session_state['user_name']))
    c3.metric("Rol", st.session_state['user_role'].upper())
    st.divider()
    st.info("Bienvenido al Sistema de Gestión Académica del Colegio Profa. Blanca Elena de Hernández.")

# --- INSCRIPCIÓN ---
elif opcion_seleccionada == "Inscripción":
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
        fot = st.file_uploader("Foto", ["jpg","png"])
        if st.form_submit_button("Guardar Inscripción"):
            if nie and nom and ape:
                doc_ref = db.collection("alumnos").document(nie)
                if not doc_ref.get().exists:
                    url_foto = subir_archivo(fot, f"expedientes/{nie}")
                    doc_ref.set({
                        "nie": nie, "nombre_completo": f"{nom} {ape}", "nombres": nom, "apellidos": ape,
                        "grado_actual": gra, "turno": tur, "estado": "Activo",
                        "encargado": {"nombre": enc, "telefono": tel, "direccion": dir},
                        "documentos": {"foto_url": url_foto},
                        "fecha_registro": firestore.SERVER_TIMESTAMP
                    })
                    st.success("✅ Alumno inscrito.")
                else: st.error("NIE ya existe.")
            else: st.error("Faltan campos obligatorios.")

# --- CONSULTA ALUMNOS (MODIFICADA CON SELECTOR DE MATERIAS) ---
elif opcion_seleccionada == "Consulta Alumnos":
    st.title("🔎 Expediente Electrónico")
    g_busq = st.selectbox("Filtrar por Grado", ["Seleccionar..."] + LISTA_GRADOS_TODO)
    if g_busq != "Seleccionar...":
        alums = db.collection("alumnos").where("grado_actual", "==", g_busq).stream()
        # MODIFICACIÓN: Ordenar por Apellidos y Nombres
        lista_alums = sorted([d.to_dict() for d in alums], key=lambda x: (x.get('apellidos',''), x.get('nombres','')))
        
        sel = st.selectbox("Seleccionar Alumno", ["Seleccionar..."] + [f"{r['nie']} - {r['apellidos']}, {r['nombres']}" for r in lista_alums])
        if sel != "Seleccionar...":
            nie_sel = sel.split(" - ")[0]
            a = db.collection("alumnos").document(nie_sel).get().to_dict()
            
            t1, t2, t3, t4 = st.tabs(["📋 Datos", "📊 Boleta de Notas", "⚙️ Editar", "📒 Bitácora"])
            
            with t1:
                c1, c2 = st.columns([1, 3])
                foto = a.get('documentos', {}).get('foto_url', "https://via.placeholder.com/150")
                c1.image(foto, width=150)
                c2.subheader(a['nombre_completo'])
                c2.write(f"**NIE:** {a['nie']} | **Estado:** {a.get('estado','Activo')}")
            
            with t2:
                st.subheader("Configuración de Boleta")
                malla_grado = MAPA_CURRICULAR.get(a['grado_actual'], [])
                # MODIFICACIÓN: Multiselect para elegir materias a imprimir
                mats_visibles = st.multiselect("Materias a incluir en reporte:", malla_grado, default=malla_grado)
                
                if st.button("Generar Vista de Impresión"):
                    notas_ref = db.collection("notas").where("nie", "==", a['nie']).stream()
                    nm = {}
                    for doc in notas_ref:
                        dd = doc.to_dict()
                        if dd['materia'] not in nm: nm[dd['materia']] = {}
                        nm[dd['materia']][dd['mes']] = dd['promedio_final']
                    
                    filas = ""
                    for mat in mats_visibles:
                        n = nm.get(mat, {})
                        v_f, v_m, v_a = n.get("Febrero",0), n.get("Marzo",0), n.get("Abril",0)
                        v_my, v_jn, v_jl = n.get("Mayo",0), n.get("Junio",0), n.get("Julio",0)
                        v_ag, v_se, v_oc = n.get("Agosto",0), n.get("Septiembre",0), n.get("Octubre",0)
                        
                        t1_v = redondear_mined((v_f+v_m+v_a)/3)
                        t2_v = redondear_mined((v_my+v_jn+v_jl)/3)
                        t3_v = redondear_mined((v_ag+v_se+v_oc)/3)
                        fin_v = redondear_mined((t1_v+t2_v+t3_v)/3)
                        
                        filas += f"<tr><td>{mat}</td><td>{v_f}</td><td>{v_m}</td><td>{v_a}</td><td><b>{t1_v}</b></td><td>{v_my}</td><td>{v_jn}</td><td>{v_jl}</td><td><b>{t2_v}</b></td><td>{v_ag}</td><td>{v_se}</td><td>{v_oc}</td><td><b>{t3_v}</b></td><td style='background:#333;color:white'>{fin_v}</td></tr>"
                    
                    logo = get_base64("logo.png")
                    html = f"""<div style='font-family:Arial;font-size:11px;'><center><img src='{logo}' height='60'><h3>COLEGIO BLANCA ELENA</h3><h4>INFORME DE NOTAS - {a['grado_actual']}</h4></center><p><b>Alumno:</b> {a['nombre_completo']}</p><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr><th>MATERIA</th><th>F</th><th>M</th><th>A</th><th>T1</th><th>M</th><th>J</th><th>J</th><th>T2</th><th>A</th><th>S</th><th>O</th><th>T3</th><th>FIN</th></tr>{filas}</table></div>"""
                    components.html(f"{html}<br><button onclick='window.print()'>🖨️ Imprimir</button>", height=500, scrolling=True)

# --- CARGAR NOTAS (MODIFICADA CON ORDEN POR APELLIDO) ---
elif opcion_seleccionada in ["Notas", "Cargar Notas"]:
    st.title("📊 Registro de Calificaciones")
    c1, c2, c3 = st.columns(3)
    g = c1.selectbox("Grado", ["Seleccionar..."] + LISTA_GRADOS_NOTAS)
    m = c2.selectbox("Materia", ["Seleccionar..."] + (MAPA_CURRICULAR.get(g, []) if g != "Seleccionar..." else []))
    mes = c3.selectbox("Mes", LISTA_MESES)
    
    if g != "Seleccionar..." and m != "Seleccionar...":
        al_ref = db.collection("alumnos").where("grado_actual", "==", g).stream()
        # MODIFICACIÓN: Lista ordenada por apellidos para el editor de datos
        lista_datos = sorted([{"NIE": d.to_dict()['nie'], "Nombre": f"{d.to_dict()['apellidos']}, {d.to_dict()['nombres']}"} for d in al_ref], key=lambda x: x['Nombre'])
        
        if lista_datos:
            df = pd.DataFrame(lista_datos)
            id_doc = f"{g}_{m}_{mes}".replace(" ","_")
            doc_existente = db.collection("notas_mensuales").document(id_doc).get()
            
            cols = ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
            for c in cols: df[c] = 0.0
            
            if doc_existente.exists:
                det = doc_existente.to_dict().get('detalles', {})
                for c in cols: df[c] = df["NIE"].map(lambda x: det.get(x, {}).get(c, 0.0))
            
            # Cálculo de promedio automático en la vista
            df["Promedio"] = (df[cols[0]]*0.25 + df[cols[1]]*0.25 + df[cols[2]]*0.1 + df[cols[3]]*0.1 + df[cols[4]]*0.3).apply(redondear_mined)
            
            ed = st.data_editor(df, hide_index=True, use_container_width=True)
            
            if st.button("💾 Guardar Notas"):
                batch = db.batch()
                detalles_final = {}
                for _, row in ed.iterrows():
                    p = redondear_mined(row[cols[0]]*0.25 + row[cols[1]]*0.25 + row[cols[2]]*0.1 + row[cols[3]]*0.1 + row[cols[4]]*0.3)
                    detalles_final[row["NIE"]] = {c: row[c] for c in cols}
                    detalles_final[row["NIE"]]["Promedio"] = p
                    
                    ref_individual = db.collection("notas").document(f"{row['NIE']}_{id_doc}")
                    batch.set(ref_individual, {"nie": row["NIE"], "grado": g, "materia": m, "mes": mes, "promedio_final": p})
                
                db.collection("notas_mensuales").document(id_doc).set({"grado": g, "materia": m, "mes": mes, "detalles": detalles_final})
                batch.commit()
                st.success("Notas guardadas exitosamente.")

# --- FINANZAS, MAESTROS, ASISTENCIA (CONTINÚAN IGUAL PERO CON MEJORAS DE CARGA) ---
# ... (El resto de tus módulos se mantienen, asegurando que uses obtener_fecha_hoy() para coherencia)