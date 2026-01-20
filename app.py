import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime, date
import base64
import time
import os
import streamlit.components.v1 as components
import math

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Gestión Escolar", 
    layout="wide", 
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# --- 1. CONEXIÓN Y SEGURIDAD ---
@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        try:
            cred = None
            if os.path.exists("credenciales.json"):
                cred = credentials.Certificate("credenciales.json")
            elif os.path.exists("credenciales"): 
                cred = credentials.Certificate("credenciales")
            elif "firebase_key" in st.secrets:
                key_dict = dict(st.secrets["firebase_key"])
                cred = credentials.Certificate(key_dict)
            else:
                st.error("🚨 ERROR: No se encuentra la llave de seguridad (credenciales.json).")
                return None
            firebase_admin.initialize_app(cred, {'storageBucket': 'gestioncbeh.firebasestorage.app'})
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            return None
    return firestore.client()

try:
    db = conectar_firebase()
    if db is None: st.stop()
    conexion_exitosa = True
except Exception as e:
    st.error(f"⚠️ Error crítico: {e}")
    st.stop()

# --- 2. CONFIGURACIÓN ACADÉMICA ---
MATERIAS_ESTANDAR = [
    "Lenguaje", 
    "Matemáticas", 
    "C.S y M. Ambiente", 
    "C. Sociales y Cívica", 
    "Inglés", 
    "Moral, U y C.", 
    "Educación Física", 
    "Educación Artística",
    "Informática",
    "Conducta"
]

MAPA_CURRICULAR = {
    "Kinder 4": ["Ámbitos de Desarrollo", "Conducta"],
    "Kinder 5": ["Ámbitos de Desarrollo", "Conducta"],
    "Preparatoria": ["Ámbitos de Desarrollo", "Conducta"],
    "Primer Grado": MATERIAS_ESTANDAR,
    "Segundo Grado": MATERIAS_ESTANDAR,
    "Tercer Grado": MATERIAS_ESTANDAR,
    "Cuarto Grado": MATERIAS_ESTANDAR,
    "Quinto Grado": MATERIAS_ESTANDAR,
    "Sexto Grado": MATERIAS_ESTANDAR,
    "Séptimo Grado": MATERIAS_ESTANDAR,
    "Octavo Grado": MATERIAS_ESTANDAR,
    "Noveno Grado": MATERIAS_ESTANDAR
}

LISTA_GRADOS_TODO = list(MAPA_CURRICULAR.keys())
LISTA_GRADOS_NOTAS = [g for g in LISTA_GRADOS_TODO if "Kinder" not in g and "Prepa" not in g]
LISTA_MESES = ["Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"]

# --- 3. FUNCIONES AUXILIARES ---
def subir_archivo(archivo, ruta_carpeta):
    if archivo is None: return None
    try:
        bucket = storage.bucket()
        nombre_limpio = archivo.name.replace(" ", "_")
        blob = bucket.blob(f"{ruta_carpeta}/{nombre_limpio}")
        blob.upload_from_file(archivo)
        blob.make_public()
        return blob.public_url
    except: return None

def get_image_base64(path):
    try:
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return "" 

def redondear_mined(valor):
    """ Regla MINED: >= 0.5 sube, < 0.5 baja """
    if valor is None: return 0.0
    parte_entera = int(valor)
    parte_decimal = valor - parte_entera
    if parte_decimal >= 0.5: return float(parte_entera + 1)
    else: return float(parte_entera)

# --- CSS PERSONALIZADO (Footer limpio y Copyright) ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .block-container {padding-top: 1rem;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- MENÚ LATERAL ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("⚠️ Falta 'logo.png'")
    
    st.markdown("---")
    opcion = st.radio("Menú Principal:", ["Inicio", "Inscripción Alumnos", "Gestión Maestros", "Consulta Alumnos", "Finanzas", "Notas (1º-9º)", "Configuración"])
    st.markdown("---")
    
    if conexion_exitosa: 
        st.success("🟢 Sistema Online")
    
    # --- COPYRIGHT (NUEVO) ---
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: grey; font-size: 11px;'>
            © 2026 Colegio Profa.<br>Blanca Elena de Hernández<br>
            Todos los derechos reservados.<br>
            v2.5 Release
        </div>
        """, unsafe_allow_html=True
    )

if not conexion_exitosa: st.stop() 

# ==========================================
# 1. INICIO
# ==========================================
if opcion == "Inicio":
    st.title("🍎 Panel de Control")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo Escolar", str(datetime.now().year))
    c2.metric("Modalidad", "Presencial")
    c3.metric("Estado", "Activo")

# ==========================================
# 2. INSCRIPCIÓN ALUMNOS
# ==========================================
elif opcion == "Inscripción Alumnos":
    st.title("📝 Nueva Inscripción")
    with st.form("ficha_alumno"):
        st.subheader("Datos del Estudiante")
        c1, c2 = st.columns(2)
        with c1:
            nie = st.text_input("NIE (Identificador)*")
            nombres = st.text_input("Nombres*")
            apellidos = st.text_input("Apellidos*")
            estado = st.selectbox("Estado", ["Activo", "Inactivo"]) 
        with c2:
            grado = st.selectbox("Grado a Matricular", LISTA_GRADOS_TODO)
            turno = st.selectbox("Turno*", ["Matutino", "Vespertino"])
            encargado = st.text_input("Nombre del Responsable")
            telefono = st.text_input("Teléfono")
            direccion = st.text_area("Dirección")
        
        st.markdown("---")
        col_doc1, col_doc2 = st.columns(2)
        with col_doc1: 
            foto = st.file_uploader("📸 Foto Carnet", type=["jpg", "png", "jpeg"])
        with col_doc2: 
            docs_pdf = st.file_uploader("📂 Documentos Legales", type=["pdf", "jpg", "png"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 Guardar Inscripción", type="primary"):
            if not nie or not nombres or not apellidos:
                st.error("⚠️ El NIE y los nombres son obligatorios.")
            else:
                with st.spinner("Procesando..."):
                    ruta = f"expedientes/{nie}"
                    lista_urls_docs = []
                    if docs_pdf:
                        for archivo in docs_pdf:
                            url = subir_archivo(archivo, ruta)
                            if url: lista_urls_docs.append(url)

                    datos = {
                        "nie": nie, "nombre_completo": f"{nombres} {apellidos}", 
                        "nombres": nombres, "apellidos": apellidos,
                        "grado_actual": grado, "turno": turno, "estado": estado,
                        "encargado": {"nombre": encargado, "telefono": telefono, "direccion": direccion},
                        "documentos": {"foto_url": subir_archivo(foto, ruta), "doc_urls": lista_urls_docs},
                        "fecha_registro": firestore.SERVER_TIMESTAMP
                    }
                    db.collection("alumnos").document(nie).set(datos)
                    st.success("✅ Alumno inscrito correctamente.")

# ==========================================
# 3. GESTIÓN DE MAESTROS
# ==========================================
elif opcion == "Gestión Maestros":
    st.title("👩‍🏫 Gestión Docente")
    t1, t2, t3, t4, t5 = st.tabs(["1️⃣ Registro", "2️⃣ Asignar Carga", "3️⃣ Admin. Cargas", "✏️ Admin. Docentes", "📋 Ver Planilla"])
    
    with t1:
        with st.form("form_nuevo_docente"):
            c1, c2 = st.columns(2)
            codigo_emp = c1.text_input("Código Empleado*", placeholder="Ej: DOC-001")
            nombre_m = c2.text_input("Nombre Completo*")
            telefono_m = c1.text_input("Teléfono")
            email_m = c2.text_input("Email")
            turno_base = c1.selectbox("Turno", ["Matutino", "Vespertino", "Tiempo Completo"])
            if st.form_submit_button("💾 Guardar Perfil"):
                if nombre_m and codigo_emp:
                    db.collection("maestros_perfil").add({"codigo": codigo_emp, "nombre": nombre_m, "contacto": {"tel": telefono_m, "email": email_m}, "turno_base": turno_base, "activo": True})
                    st.success("✅ Perfil creado.")
                else: st.error("Faltan datos obligatorios.")

    with t2:
        docs_m = db.collection("maestros_perfil").stream()
        lista_profes = {f"{d.to_dict().get('codigo', 'S/C')} - {d.to_dict()['nombre']}": d.id for d in docs_m}
        if lista_profes:
            with st.form("form_carga"):
                c1, c2 = st.columns(2)
                nombre_sel = c1.selectbox("Docente", list(lista_profes.keys()))
                grado_sel = c2.selectbox("Grado", LISTA_GRADOS_TODO)
                
                # Materias dinámicas
                materias_sel = st.multiselect("Materias", MATERIAS_ESTANDAR)
                
                nota = st.text_input("Nota / Observación")
                es_guia = st.checkbox("¿Es el Maestro Guía de este grado?")
                
                if st.form_submit_button("🔗 Asignar Carga"):
                    if materias_sel:
                        nombre_limpio = nombre_sel.split(" - ")[1] if " - " in nombre_sel else nombre_sel
                        db.collection("carga_academica").add({
                            "id_docente": lista_profes[nombre_sel], 
                            "nombre_docente": nombre_limpio, 
                            "grado": grado_sel, 
                            "materias": materias_sel, 
                            "nota": nota,
                            "es_guia": es_guia
                        })
                        st.success("Carga asignada.")
                    else: st.error("Seleccione materias.")
        else: st.warning("No hay docentes registrados.")

    with t3: 
        docs_c = db.collection("carga_academica").stream()
        cargas = [{"id": d.id, **d.to_dict()} for d in docs_c]
        if cargas:
            df_c = pd.DataFrame(cargas)
            if 'es_guia' not in df_c.columns: df_c['es_guia'] = False
            
            c1, c2 = st.columns(2)
            f_grad = c1.selectbox("Filtrar Grado:", ["Todos"] + sorted(df_c['grado'].unique().tolist()))
            
            df_show = df_c.copy()
            if f_grad != "Todos": df_show = df_show[df_show['grado'] == f_grad]
            
            st.dataframe(df_show[['nombre_docente', 'grado', 'materias', 'es_guia']], use_container_width=True)
            
            if not df_show.empty:
                opcs = {f"{r['nombre_docente']} - {r['grado']}": r['id'] for i, r in df_show.iterrows()}
                sel_id = st.selectbox("Gestionar Carga:", ["Seleccionar..."] + list(opcs.keys()))
                if sel_id != "Seleccionar...":
                    cid = opcs[sel_id]
                    c_obj = next((x for x in cargas if x['id'] == cid), None)
                    with st.form("edit_carga_real"):
                        st.info(f"Editando: {c_obj['nombre_docente']} - {c_obj['grado']}")
                        es_guia_edit = st.checkbox("¿Es Maestro Guía?", value=c_obj.get('es_guia', False))
                        materias_edit = st.multiselect("Materias", MATERIAS_ESTANDAR, default=[m for m in c_obj['materias'] if m in MATERIAS_ESTANDAR])
                        
                        c_a, c_b = st.columns(2)
                        if c_a.form_submit_button("💾 Actualizar"):
                            db.collection("carga_academica").document(cid).update({"es_guia": es_guia_edit, "materias": materias_edit})
                            st.success("Actualizado"); time.sleep(1); st.rerun()
                        if c_b.form_submit_button("🗑️ Eliminar"):
                            db.collection("carga_academica").document(cid).delete()
                            st.success("Eliminado"); time.sleep(1); st.rerun()

    with t5:
        docs_p = db.collection("maestros_perfil").stream()
        lista_p = [d.to_dict() for d in docs_p]
        if lista_p: st.dataframe(pd.DataFrame(lista_p)[['codigo', 'nombre', 'turno_base']], use_container_width=True)

# ==========================================
# 4. CONSULTA ALUMNOS
# ==========================================
elif opcion == "Consulta Alumnos":
    st.title("🔎 Consulta de Estudiantes")
    modo = st.radio("Método de Búsqueda:", ["Por NIE", "Por Grado"], horizontal=True)
    alum = None
    
    if modo == "Por NIE":
        n = st.text_input("Ingrese NIE:")
        if st.button("Buscar") and n:
            d = db.collection("alumnos").document(n).get()
            if d.exists: alum = d.to_dict()
            else: st.error("Alumno no encontrado.")
    else:
        g = st.selectbox("Seleccione Grado", ["Todos"] + LISTA_GRADOS_TODO)
        q = db.collection("alumnos")
        if g != "Todos": q = q.where("grado_actual", "==", g)
        l = [d.to_dict() for d in q.stream()]
        opcs = {f"{a['nie']} - {a['nombre_completo']}": a for a in l}
        sel = st.selectbox("Seleccione Alumno", ["Seleccionar..."] + list(opcs.keys()))
        if sel != "Seleccionar...": alum = opcs[sel]

    if alum:
        st.markdown("---")
        c1, c2 = st.columns([1, 4])
        with c1: st.image(alum.get('documentos',{}).get('foto_url', "https://via.placeholder.com/150"), width=150)
        with c2: 
            st.title(alum['nombre_completo'])
            st.markdown(f"**NIE:** {alum['nie']} | **Grado:** {alum['grado_actual']} | **Turno:** {alum.get('turno')}")
            st.info(f"Responsable: {alum.get('encargado',{}).get('nombre')} - Tel: {alum.get('encargado',{}).get('telefono')}")

        t1, t2, t3, t4 = st.tabs(["📂 Documentos", "👨‍🏫 Maestros", "💰 Pagos & Recibos", "🖨️ Boleta de Notas"])
        
        with t1:
            docs = alum.get('documentos',{}).get('doc_urls', [])
            if alum.get('documentos',{}).get('doc_url'): docs.append(alum.get('documentos',{}).get('doc_url'))
            if docs:
                st.success(f"{len(set(docs))} Archivos disponibles")
                for u in list(set(docs)): st.link_button("📄 Abrir Documento", u)
            else: st.info("No hay documentos digitales adjuntos.")

        with t2:
            st.write(f"**Docentes asignados a {alum['grado_actual']}:**")
            cargas = db.collection("carga_academica").where("grado", "==", alum['grado_actual']).stream()
            lc = [c.to_dict() for c in cargas]
            if lc:
                for c in lc:
                    with st.container(border=True):
                        col_a, col_b = st.columns([2,3])
                        col_a.markdown(f"**{c['nombre_docente']}**")
                        if c.get('es_guia'): col_a.markdown("🌟 *Maestro Guía*")
                        col_b.caption(", ".join(c['materias']))
            else: st.warning("Aún no se han asignado maestros a este grado.")

        with t3:
            # HISTORIAL DE PAGOS
            pagos = db.collection("finanzas").where("alumno_nie", "==", alum['nie']).where("tipo", "==", "ingreso").stream()
            lp = [{"id":p.id, **p.to_dict()} for p in pagos]
            if lp:
                df = pd.DataFrame(lp).sort_values(by="fecha_legible", ascending=False)
                if "observaciones" not in df: df["observaciones"] = ""
                st.dataframe(df[['fecha_legible', 'descripcion', 'monto', 'observaciones']], use_container_width=True)
                
                st.markdown("#### 📄 Reimprimir Comprobante")
                sel_p = st.selectbox("Seleccione transacción:", ["Seleccionar..."] + [f"{p['fecha_legible']} - ${p['monto']}" for p in lp])
                if sel_p != "Seleccionar...":
                    if st.button("Ver Vista Previa de Recibo"):
                        p_obj = next(p for p in lp if f"{p['fecha_legible']} - ${p['monto']}" == sel_p)
                        color = "#2e7d32"
                        img = get_image_base64("logo.png"); img_h = f'<img src="{img}" style="height:70px;">' if img else ""
                        html_ticket = f"""
                        <div style="border:1px solid #ccc; padding:0; margin-top:20px; background:white; color:black; font-family:Arial, sans-serif; max-width:800px; margin-left:auto; margin-right:auto;">
                            <div style="background-color:{color}; color:white !important; padding:20px; display:flex; justify-content:space-between; align-items:center;">
                                <div style="display:flex; align-items:center; gap:15px;">
                                    <div style="background:white; padding:5px; border-radius:4px;">{img_h}</div>
                                    <div><h3 style="margin:0; color:white;">COLEGIO PROFA. BLANCA ELENA</h3><p style="margin:0; font-size:12px; opacity:0.9; color:white;">San Felipe, El Salvador</p></div>
                                </div>
                                <div style="text-align:right;"><h4 style="margin:0; color:white;">COPIA DE RECIBO</h4><p style="margin:0; font-size:12px; color:white;">Ref: {p_obj['id'][-6:]}</p></div>
                            </div>
                            <div style="padding:30px;">
                                <table style="width:100%; border-collapse:collapse; font-size:14px; color:black;">
                                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px; font-weight:bold; width:30%;">Alumno:</td><td style="padding:10px">{p_obj.get('nombre_persona')}</td></tr>
                                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px; font-weight:bold;">Fecha de Pago:</td><td style="padding:10px">{p_obj['fecha_legible']}</td></tr>
                                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px; font-weight:bold;">Concepto:</td><td style="padding:10px">{p_obj['descripcion']}</td></tr>
                                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px; font-weight:bold;">Observaciones:</td><td style="padding:10px; font-style:italic;">{p_obj.get('observaciones','-')}</td></tr>
                                </table>
                                <div style="margin-top:30px; text-align:right;">
                                    <p style="font-size:12px; color:#666;">Total Pagado</p>
                                    <h1 style="margin:0; color:{color}; font-size:32px;">${p_obj['monto']:.2f}</h1>
                                </div>
                            </div>
                            <div style="background:#f9f9f9; padding:10px; text-align:center; font-size:10px; color:#999; border-top:1px solid #eee;">Documento generado electrónicamente</div>
                        </div>
                        """
                        st.markdown(html_ticket, unsafe_allow_html=True)
                        components.html(f"""<script>function p(){{window.print()}}</script><div style="text-align:center; margin-top:20px;"><button onclick="p()" style="background:#2e7d32; color:white; padding:12px 24px; border:none; border-radius:5px; cursor:pointer; font-size:16px;">🖨️ Imprimir Copia Oficial</button></div>""", height=80)
            else: st.info("No se encontraron registros financieros.")

        with t4: 
            # --- BOLETA DE NOTAS OFICIAL ---
            year_actual = datetime.now().year
            st.subheader(f"Boleta de Calificaciones {year_actual}")
            
            # Buscar Maestro Guía
            q_guia = db.collection("carga_academica").where("grado", "==", alum['grado_actual']).stream()
            maestro_guia = "No asignado"
            for d in q_guia:
                data = d.to_dict()
                if data.get('es_guia') is True:
                    maestro_guia = data['nombre_docente']
                    break
            
            # Recuperar Notas
            notas_ref = db.collection("notas").where("nie", "==", alum['nie']).stream()
            notas_map = {}
            for doc in notas_ref:
                d = doc.to_dict()
                if d['materia'] not in notas_map: notas_map[d['materia']] = {}
                notas_map[d['materia']][d['mes']] = d['promedio_final']
            
            if not notas_map:
                st.warning("⚠️ No hay calificaciones registradas para este alumno.")
            else:
                filas = []
                # CARGAR MATERIAS EXACTAS DEL GRADO
                materias_del_grado = MAPA_CURRICULAR.get(alum['grado_actual'], MATERIAS_ESTANDAR)
                
                for mat in materias_del_grado:
                    if mat in notas_map:
                        n = notas_map[mat]
                        
                        f, m, a = n.get("Febrero", 0), n.get("Marzo", 0), n.get("Abril", 0)
                        t1 = redondear_mined((f + m + a) / 3)
                        
                        may, jun, jul = n.get("Mayo", 0), n.get("Junio", 0), n.get("Julio", 0)
                        t2 = redondear_mined((may + jun + jul) / 3)
                        
                        ago, sep, oct_ = n.get("Agosto", 0), n.get("Septiembre", 0), n.get("Octubre", 0)
                        t3 = redondear_mined((ago + sep + oct_) / 3)
                        
                        fin = redondear_mined((t1 + t2 + t3) / 3)
                        
                        filas.append({
                            "Asignatura": mat,
                            "F": n.get("Febrero", "-"), "M": n.get("Marzo", "-"), "A": n.get("Abril", "-"), "TI": t1,
                            "M.": n.get("Mayo", "-"), "J": n.get("Junio", "-"), "J.": n.get("Julio", "-"), "TII": t2,
                            "A.": n.get("Agosto", "-"), "S": n.get("Septiembre", "-"), "O": n.get("Octubre", "-"), "TIII": t3,
                            "FINAL": fin
                        })
                
                df_b = pd.DataFrame(filas)
                st.dataframe(df_b, use_container_width=True, hide_index=True)
                
                # Generar HTML Boleta
                html_rows = ""
                for _, r in df_b.iterrows():
                    html_rows += f"<tr><td style='text-align:left; padding:5px;'>{r['Asignatura']}</td><td>{r['F']}</td><td>{r['M']}</td><td>{r['A']}</td><td style='background:#f0f0f0; font-weight:bold;'>{r['TI']}</td><td>{r['M.']}</td><td>{r['J']}</td><td>{r['J.']}</td><td style='background:#f0f0f0; font-weight:bold;'>{r['TII']}</td><td>{r['A.']}</td><td>{r['S']}</td><td>{r['O']}</td><td style='background:#f0f0f0; font-weight:bold;'>{r['TIII']}</td><td style='background:#333;color:white;font-weight:bold;'>{r['FINAL']}</td></tr>"
                
                logo = get_image_base64("logo.png"); h_img = f'<img src="{logo}" height="70">' if logo else ""
                
                html_boleta = f"""
                <div style="font-family:Arial, sans-serif; font-size:12px; color:black; padding:20px;">
                    <div style="display:flex; align-items:center; margin-bottom:20px; border-bottom: 2px solid #000; padding-bottom:10px;">
                        {h_img}
                        <div style="margin-left:20px;">
                            <h2 style="margin:0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2>
                            <h4 style="margin:0; font-weight:normal;">INFORME DE CALIFICACIONES - AÑO {year_actual}</h4>
                        </div>
                    </div>
                    <div style="border:1px solid #000; padding:10px; margin-bottom:20px; background:#f9f9f9;">
                        <table style="width:100%;">
                            <tr>
                                <td><b>Alumno:</b> {alum['nombre_completo']}</td>
                                <td><b>NIE:</b> {alum['nie']}</td>
                            </tr>
                            <tr>
                                <td><b>Grado:</b> {alum['grado_actual']}</td>
                                <td><b>Maestro Guía:</b> {maestro_guia}</td>
                            </tr>
                        </table>
                    </div>
                    <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
                        <tr style="background:#ddd; font-weight:bold;">
                            <td style="padding:8px;">ASIGNATURA</td>
                            <td>FEB</td><td>MAR</td><td>ABR</td><td>T1</td>
                            <td>MAY</td><td>JUN</td><td>JUL</td><td>T2</td>
                            <td>AGO</td><td>SEP</td><td>OCT</td><td>T3</td>
                            <td>FINAL</td>
                        </tr>
                        {html_rows}
                    </table>
                    <br><br><br><br>
                    <div style="display:flex; justify-content:space-between; text-align:center; padding:0 50px;">
                        <div style="width:30%;">
                            <div style="border-top:1px solid #000; padding-top:5px;">Orientador(a)</div>
                        </div>
                        <div style="width:30%;">
                            <div style="border-top:1px solid #000; padding-top:5px;">Subdirección</div>
                        </div>
                        <div style="width:30%;">
                            <div style="border-top:1px solid #000; padding-top:5px;">Dirección</div>
                        </div>
                    </div>
                </div>
                """
                components.html(f"""<html><body>{html_boleta}<div style="text-align:center; margin-top:20px;"><button onclick="window.print()" style="padding:10px 20px; background:black; color:white; border:none; cursor:pointer;">🖨️ IMPRIMIR BOLETA OFICIAL</button></div><style>@media print{{button{{display:none;}} body{{margin:0;}}}}</style></body></html>""", height=800, scrolling=True)

# ==========================================
# 5. FINANZAS
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Gestión Financiera")
    if 'recibo_temp' not in st.session_state: st.session_state.recibo_temp = None
    if 'reporte_html' not in st.session_state: st.session_state.reporte_html = None

    if st.session_state.recibo_temp:
        # VISTA DE IMPRESIÓN DEL RECIBO RECIÉN CREADO
        r = st.session_state.recibo_temp
        es_ingreso = r.get('tipo') == 'ingreso'
        color_tema = "#2e7d32" if es_ingreso else "#c62828"
        titulo_doc = "RECIBO DE INGRESO" if es_ingreso else "COMPROBANTE DE EGRESO"
        img = get_image_base64("logo.png"); img_h = f'<img src="{img}" style="height:70px;">' if img else ""
        
        # CSS PARA IMPRESIÓN LIMPIA
        st.markdown("""
        <style>
        @media print {
            body * { visibility: hidden; }
            [data-testid="stSidebar"], header, footer { display: none !important; }
            .ticket-container, .ticket-container * { visibility: visible !important; }
            .ticket-container { position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0; }
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.success("✅ Transacción registrada exitosamente.")
        
        # HTML PROFESIONAL
        html_ticket = f"""
        <div class="ticket-container" style="font-family:Arial,sans-serif;color:black;background:white;border:1px solid #ccc; max-width:800px; margin:auto;">
            <div style="background-color:{color_tema};color:white !important;padding:20px;display:flex;justify-content:space-between;align-items:center;">
                <div style="display:flex;align-items:center;gap:15px;">
                    <div style="background:white;padding:5px;border-radius:4px;">{img_h}</div>
                    <div><h3 style="margin:0;color:white;">COLEGIO PROFA. BLANCA ELENA</h3><p style="margin:0;font-size:12px;opacity:0.9;color:white;">San Felipe, El Salvador</p></div>
                </div>
                <div style="text-align:right;"><h4 style="margin:0;color:white;">{titulo_doc}</h4><p style="margin:0;font-size:12px;color:white;">Folio: #{str(int(datetime.now().timestamp()))[-6:]}</p></div>
            </div>
            <div style="padding:30px;">
                <table style="width:100%;border-collapse:collapse;font-size:14px;color:black;">
                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;width:30%;">Persona/Alumno:</td><td style="padding:10px">{r.get('nombre_persona')}</td></tr>
                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;">Fecha:</td><td style="padding:10px">{r['fecha_legible']}</td></tr>
                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;">Concepto:</td><td style="padding:10px">{r['descripcion']}</td></tr>
                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;">Observaciones:</td><td style="padding:10px;font-style:italic;">{r.get('observaciones','-')}</td></tr>
                </table>
                <div style="margin-top:30px;text-align:right;">
                    <p style="font-size:12px;color:#666;">Monto Total</p>
                    <h1 style="margin:0;color:{color_tema};font-size:36px;">${r['monto']:.2f}</h1>
                </div>
                <br><br>
                <div style="display:flex;justify-content:space-between;gap:40px;margin-top:20px;">
                    <div style="flex:1;border-top:1px solid #000;text-align:center;font-size:12px;padding-top:5px;">Firma y Sello Colegio</div>
                    <div style="flex:1;border-top:1px solid #000;text-align:center;font-size:12px;padding-top:5px;">Firma Conforme</div>
                </div>
            </div>
            <div style="background:#f5f5f5;padding:10px;text-align:center;font-size:10px;color:#999;border-top:1px solid #eee;">Comprobante generado por Sistema de Gestión CBEH</div>
        </div>
        """
        st.markdown(html_ticket, unsafe_allow_html=True)
        
        c1, c2 = st.columns([1,4])
        if c1.button("❌ Cerrar"): st.session_state.recibo_temp = None; st.rerun()
        with c2: components.html(f"""<script>function p(){{window.parent.print()}}</script><button onclick="p()" style="background:{color_tema};color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;font-size:16px;">🖨️ Imprimir Comprobante</button>""", height=60)
    
    elif st.session_state.reporte_html:
        st.markdown("""<style>@media print { body * { visibility: hidden; } .rep, .rep * { visibility: visible; } .rep { position: absolute; left: 0; top: 0; width: 100%; } }</style>""", unsafe_allow_html=True)
        st.markdown(st.session_state.reporte_html, unsafe_allow_html=True)
        if st.button("⬅️ Volver"): st.session_state.reporte_html = None; st.rerun()

    else:
        t1, t2, t3 = st.tabs(["Ingresos (Cobros)", "Gastos (Egresos)", "Reportes"])
        with t1:
            c1, c2 = st.columns([1,2])
            nie = c1.text_input("Buscar Alumno por NIE:")
            if c1.button("🔍 Buscar Alumno") and nie:
                d = db.collection("alumnos").document(nie).get()
                if d.exists: st.session_state.pago_alum = d.to_dict()
                else: st.error("Alumno no encontrado")
            
            if st.session_state.get("pago_alum"):
                a = st.session_state.pago_alum
                with c2.form("fi"):
                    st.success(f"Realizando cobro a: **{a['nombre_completo']}**")
                    con = st.selectbox("Concepto", ["Mensualidad", "Matrícula", "Uniforme", "Libros", "Otros"])
                    mes = st.selectbox("Mes Correspondiente", LISTA_MESES)
                    mon = st.number_input("Monto a Cobrar ($)", min_value=0.01, step=0.01)
                    obs = st.text_area("Detalle / Observaciones (Opcional)")
                    if st.form_submit_button("✅ Procesar Cobro"):
                        data = {
                            "tipo": "ingreso", 
                            "descripcion": f"{con} - {mes}", 
                            "monto": mon, 
                            "nombre_persona": a['nombre_completo'], 
                            "alumno_nie": a['nie'], 
                            "observaciones": obs, 
                            "fecha": firestore.SERVER_TIMESTAMP, 
                            "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        db.collection("finanzas").add(data)
                        st.session_state.recibo_temp = data
                        st.session_state.pago_alum = None
                        st.rerun()
        with t2:
            st.info("Registro de pagos a proveedores, maestros o servicios.")
            cat = st.selectbox("Categoría del Gasto", ["Pago de Planilla (Maestros)", "Servicios Básicos", "Mantenimiento", "Materiales", "Otros"])
            with st.form("fe"):
                c_a, c_b = st.columns(2)
                nom = c_a.text_input("Nombre de Persona / Proveedor")
                mon = c_b.number_input("Monto del Gasto ($)", min_value=0.01, step=0.01)
                obs = st.text_area("Descripción detallada del gasto")
                if st.form_submit_button("🔴 Registrar Salida de Dinero"):
                    data = {
                        "tipo": "egreso", 
                        "descripcion": cat, 
                        "monto": mon, 
                        "nombre_persona": nom, 
                        "observaciones": obs, 
                        "fecha": firestore.SERVER_TIMESTAMP, 
                        "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    db.collection("finanzas").add(data)
                    st.session_state.recibo_temp = data
                    st.rerun()
        with t3:
            st.subheader("Reportes Contables")
            c1, c2, c3 = st.columns(3)
            fi = c1.date_input("Fecha Inicio", value=date(datetime.now().year, 1, 1))
            ff = c2.date_input("Fecha Fin")
            filtro = c3.selectbox("Tipo de Movimiento", ["Todos", "Solo Ingresos", "Solo Egresos"])
            
            if st.button("📄 Generar Reporte PDF"):
                docs = db.collection("finanzas").order_by("fecha", direction=firestore.Query.DESCENDING).stream()
                rows = []
                for d in docs:
                    dd = d.to_dict()
                    raw_date = dd.get("fecha_dt") or dd.get("fecha")
                    f_obj = None
                    if raw_date:
                        try: f_obj = raw_date.date()
                        except: f_obj = datetime.now().date()
                    
                    if f_obj and (fi <= f_obj <= ff):
                        if filtro == "Solo Ingresos" and dd['tipo'] != 'ingreso': continue
                        if filtro == "Solo Egresos" and dd['tipo'] != 'egreso': continue
                        rows.append(dd)
                
                if rows:
                    df = pd.DataFrame(rows)
                    t_ing = df[df['tipo']=='ingreso']['monto'].sum()
                    t_egr = df[df['tipo']=='egreso']['monto'].sum()
                    bal = t_ing - t_egr
                    
                    html_rows = ""
                    for _, r in df.iterrows():
                        color = "green" if r['tipo'] == 'ingreso' else "red"
                        html_rows += f"<tr style='border-bottom:1px solid #eee;'><td>{r['fecha_legible']}</td><td style='color:{color};font-weight:bold;'>{r['tipo'].upper()}</td><td>{r.get('nombre_persona')}</td><td>{r['descripcion']}</td><td>{r.get('observaciones','-')}</td><td style='text-align:right;'>${r['monto']:.2f}</td></tr>"
                    
                    img = get_image_base64("logo.png"); h_img = f'<img src="{img}" height="60">' if img else ""
                    html_rep = f"""
                    <div class="rep" style="font-family:Arial, sans-serif; padding:20px; color:black;">
                        <div style="display:flex; align-items:center; border-bottom:2px solid #333; padding-bottom:10px;">
                            {h_img}
                            <div style="margin-left:15px;">
                                <h2 style="margin:0;">COLEGIO PROFA. BLANCA ELENA</h2>
                                <p style="margin:0; color:#666;">REPORTE FINANCIERO DETALLADO</p>
                            </div>
                        </div>
                        <p><b>Periodo:</b> {fi} al {ff}</p>
                        <div style="display:flex; gap:20px; margin:20px 0;">
                            <div style="background:#e8f5e9; padding:10px; border-radius:5px;"><b>INGRESOS:</b> ${t_ing:.2f}</div>
                            <div style="background:#ffebee; padding:10px; border-radius:5px;"><b>EGRESOS:</b> ${t_egr:.2f}</div>
                            <div style="background:#e3f2fd; padding:10px; border-radius:5px;"><b>BALANCE:</b> ${bal:.2f}</div>
                        </div>
                        <table style="width:100%; border-collapse:collapse; font-size:12px;">
                            <tr style="background:#f0f0f0; text-align:left;"><th style="padding:8px;">FECHA</th><th>TIPO</th><th>PERSONA</th><th>CONCEPTO</th><th>DETALLE</th><th style="text-align:right;">MONTO</th></tr>
                            {html_rows}
                        </table>
                    </div>
                    """
                    st.session_state.reporte_html = html_rep
                    st.rerun()
                else: st.warning("No hay datos en este rango de fechas.")

# ==========================================
# 6. NOTAS (1º A 9º)
# ==========================================
elif opcion == "Notas (1º-9º)":
    st.title("📊 Registro de Calificaciones")
    st.markdown("---")
    
    # 1. Selectores
    c1, c2, c3 = st.columns(3)
    grado = c1.selectbox("1. Seleccione Grado", ["Seleccionar..."] + LISTA_GRADOS_NOTAS)
    
    # Carga de materias basada en MAPA_CURRICULAR
    materias_posibles = MAPA_CURRICULAR.get(grado, []) if grado != "Seleccionar..." else []
    
    materia = c2.selectbox("2. Seleccione Materia", ["Seleccionar..."] + materias_posibles)
    mes = c3.selectbox("3. Mes a Calificar", LISTA_MESES)

    if grado != "Seleccionar..." and materia != "Seleccionar...":
        st.info(f"Editando notas de: **{materia}** - {grado} ({mes})")
        
        # 2. Buscar Alumnos
        docs = db.collection("alumnos").where("grado_actual", "==", grado).stream()
        lista = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
        
        if not lista:
            st.warning(f"⚠️ No hay alumnos inscritos en {grado}.")
        else:
            df = pd.DataFrame(lista).sort_values("Nombre")
            id_doc = f"{grado}_{materia}_{mes}".replace(" ","_")
            
            # 3. Definir Columnas (SI ES CONDUCTA, SOLO UNA NOTA)
            if materia == "Conducta":
                cols = ["Nota Conducta"]
            else:
                # Estructura del Excel: 25%, 25%, 10%, 10%, 30%
                cols = ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
            
            # 4. Cargar Datos Previos
            doc_ref = db.collection("notas_mensuales").document(id_doc).get()
            if doc_ref.exists:
                datos_db = doc_ref.to_dict().get('detalles', {})
                for c in cols: df[c] = df["NIE"].map(lambda x: datos_db.get(x, {}).get(c, 0.0))
            else:
                for c in cols: df[c] = 0.0
            
            # Añadir columna de Promedio (Visual - Calculada)
            df["Promedio Final"] = 0.0
            if doc_ref.exists:
                df["Promedio Final"] = df["NIE"].map(lambda x: datos_db.get(x, {}).get("Promedio", 0.0))

            # 5. Editor de Tabla
            config = {
                "NIE": st.column_config.TextColumn(disabled=True),
                "Nombre": st.column_config.TextColumn(disabled=True, width="medium"),
                "Promedio Final": st.column_config.NumberColumn(disabled=True, format="%.1f")
            }
            for c in cols: config[c] = st.column_config.NumberColumn(min_value=0, max_value=10, step=0.1, format="%.1f")
            
            edited = st.data_editor(df, column_config=config, hide_index=True, use_container_width=True, key=id_doc, num_rows="fixed")
            
            # 6. Guardado y Cálculo
            if st.button("💾 Guardar y Calcular Promedios", type="primary"):
                batch = db.batch()
                detalles = {}
                for _, row in edited.iterrows():
                    # Cálculo Matemático
                    if materia == "Conducta":
                        prom = row["Nota Conducta"]
                    else:
                        prom = (row["Act1 (25%)"]*0.25 + row["Act2 (25%)"]*0.25 + 
                                row["Alt1 (10%)"]*0.10 + row["Alt2 (10%)"]*0.10 + 
                                row["Examen (30%)"]*0.30)
                    
                    # Guardamos con 1 decimal
                    prom = round(prom, 1)
                    
                    detalles[row["NIE"]] = {c: row[c] for c in cols}
                    detalles[row["NIE"]]["Promedio"] = prom
                    
                    # Guardado Individual (Crucial para la Boleta)
                    ref = db.collection("notas").document(f"{row['NIE']}_{id_doc}")
                    batch.set(ref, {
                        "nie": row["NIE"], 
                        "grado": grado, 
                        "materia": materia, 
                        "mes": mes, 
                        "promedio_final": prom
                    })
                
                # Guardado Grupal (Para volver a cargar la tabla)
                db.collection("notas_mensuales").document(id_doc).set({
                    "grado": grado, 
                    "materia": materia, 
                    "mes": mes, 
                    "detalles": detalles,
                    "fecha_update": firestore.SERVER_TIMESTAMP
                })
                
                batch.commit()
                st.balloons()
                st.success("✅ Notas guardadas exitosamente.")
                time.sleep(1); st.rerun()

# 7. CONFIGURACIÓN
elif opcion == "Configuración":
    st.header("⚙️ Configuración")
    with st.expander("Zona de Peligro (Borrado)"):
        if st.button("Resetear Base de Datos") and st.text_input("Escriba BORRAR para confirmar") == "BORRAR":
            st.warning("Función desactivada temporalmente por seguridad.")