import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime, date
import base64
import time
import os
import streamlit.components.v1 as components

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión Escolar", layout="wide", page_icon="🎓")

# --- CONEXIÓN INTELIGENTE A FIREBASE ---
@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        try:
            # 1. PRIORIDAD LOCAL
            cred = None
            if os.path.exists("credenciales.json"):
                cred = credentials.Certificate("credenciales.json")
            elif os.path.exists("credenciales"): 
                cred = credentials.Certificate("credenciales")
            # 2. PRIORIDAD NUBE
            elif "firebase_key" in st.secrets:
                key_dict = dict(st.secrets["firebase_key"])
                cred = credentials.Certificate(key_dict)
            else:
                st.error("🚨 NO SE ENCUENTRA LA LLAVE DE ACCESO.")
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

# --- FUNCIONES AUXILIARES ---
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

# --- CONSTANTES ACADÉMICAS ---
LISTA_GRADOS_TODO = ["Kinder 4", "Kinder 5", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
# Solo grados que llevan notas numéricas
LISTA_GRADOS_NOTAS = ["Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]

LISTA_MATERIAS = [
    "Lenguaje", "Matemática", "Ciencia y Tecnología", "Estudios Sociales", 
    "Inglés", "Moral, Urbanidad y Cívica", "Educación Física", "Educación Artística", 
    "Informática", "Ortografía", "Caligrafía", "Conducta"
]

LISTA_MESES = ["Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"]

# --- MENÚ LATERAL ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("⚠️ Falta 'logo.png'")
    st.markdown("---")
    opcion = st.radio("Menú Principal:", ["Inicio", "Inscripción Alumnos", "Gestión Maestros", "Consulta Alumnos", "Finanzas", "Notas (1º-9º)", "Configuración"])
    st.markdown("---")
    if conexion_exitosa: st.success("🟢 Conectado")

if not conexion_exitosa: st.stop() 

# ==========================================
# 1. INICIO
# ==========================================
if opcion == "Inicio":
    st.title("🍎 Panel de Control")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo", "2026")
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
            nie = st.text_input("NIE (Identificador)*", placeholder="Ej: 1234567")
            nombres = st.text_input("Nombres*")
            apellidos = st.text_input("Apellidos*")
            estado = st.selectbox("Estado Actual", ["Activo", "Inactivo", "Retirado"]) 
        with c2:
            grado = st.selectbox("Grado a Matricular", LISTA_GRADOS_TODO)
            turno = st.selectbox("Turno*", ["Matutino", "Vespertino"])
            encargado = st.text_input("Nombre del Responsable")
            telefono = st.text_input("Teléfono de Contacto")
            direccion = st.text_area("Dirección de Residencia", height=100)
        
        st.markdown("---")
        st.subheader("Documentación Digital")
        col_doc1, col_doc2 = st.columns(2)
        with col_doc1: 
            foto = st.file_uploader("📸 Foto de Perfil (Carnet)", type=["jpg", "png", "jpeg"])
        with col_doc2: 
            docs_pdf = st.file_uploader("📂 Documentos (Partida, DUI, Cartilla)", type=["pdf", "jpg", "png"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 Guardar Inscripción", type="primary"):
            if not nie or not nombres or not apellidos:
                st.error("⚠️ El NIE y los nombres son obligatorios.")
            else:
                with st.spinner("Guardando expediente..."):
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
                    st.success(f"✅ ¡Alumno inscrito con {len(lista_urls_docs)} documentos!")

# ==========================================
# 3. GESTIÓN DE MAESTROS
# ==========================================
elif opcion == "Gestión Maestros":
    st.title("👩‍🏫 Plantilla Docente")
    t1, t2, t3, t4, t5 = st.tabs(["1️⃣ Registro", "2️⃣ Asignar Carga", "3️⃣ Admin. Cargas", "✏️ Admin. Docentes", "📋 Ver Planilla"])
    
    with t1:
        with st.form("form_nuevo_docente"):
            c1, c2 = st.columns(2)
            codigo_emp = c1.text_input("Código*", placeholder="Ej: DOC-001")
            nombre_m = c2.text_input("Nombre Completo*")
            telefono_m = c1.text_input("Teléfono")
            email_m = c2.text_input("Email")
            turno_base = c1.selectbox("Turno", ["Matutino", "Vespertino", "Tiempo Completo"])
            if st.form_submit_button("💾 Guardar"):
                if nombre_m and codigo_emp:
                    db.collection("maestros_perfil").add({"codigo": codigo_emp, "nombre": nombre_m, "contacto": {"tel": telefono_m, "email": email_m}, "turno_base": turno_base, "activo": True})
                    st.success("✅ Perfil creado.")
                else: st.error("Código y Nombre obligatorios")

    with t2:
        docs_m = db.collection("maestros_perfil").stream()
        lista_profes = {f"{d.to_dict().get('codigo', 'S/C')} - {d.to_dict()['nombre']}": d.id for d in docs_m}
        if lista_profes:
            with st.form("form_carga"):
                c1, c2 = st.columns(2)
                nombre_sel = c1.selectbox("Docente", list(lista_profes.keys()))
                grado_sel = c2.selectbox("Grado", LISTA_GRADOS_TODO)
                materias_sel = st.multiselect("Materias", LISTA_MATERIAS)
                nota = st.text_input("Nota")
                if st.form_submit_button("🔗 Vincular Carga"):
                    if materias_sel:
                        nombre_limpio = nombre_sel.split(" - ")[1] if " - " in nombre_sel else nombre_sel
                        db.collection("carga_academica").add({"id_docente": lista_profes[nombre_sel], "nombre_docente": nombre_limpio, "grado": grado_sel, "materias": materias_sel, "nota": nota})
                        st.success("Carga asignada.")
                    else: st.error("Seleccione materias.")
        else: st.warning("Registre docentes primero.")

    with t3: 
        docs_c = db.collection("carga_academica").stream()
        cargas = [{"id": d.id, **d.to_dict()} for d in docs_c]
        if cargas:
            df_c = pd.DataFrame(cargas)
            c1, c2 = st.columns(2)
            f_doc = c1.selectbox("Filtrar Docente:", ["Todos"] + sorted(df_c['nombre_docente'].unique().tolist()))
            f_grad = c2.selectbox("Filtrar Grado:", ["Todos"] + sorted(df_c['grado'].unique().tolist()))
            
            df_show = df_c.copy()
            if f_doc != "Todos": df_show = df_show[df_show['nombre_docente'] == f_doc]
            if f_grad != "Todos": df_show = df_show[df_show['grado'] == f_grad]
            st.dataframe(df_show[['nombre_docente', 'grado', 'materias', 'nota']], use_container_width=True)
            
            if not df_show.empty:
                opcs = {f"{r['nombre_docente']} - {r['grado']}": r['id'] for i, r in df_show.iterrows()}
                sel_id = st.selectbox("Editar/Eliminar Carga:", ["Seleccionar..."] + list(opcs.keys()))
                if sel_id != "Seleccionar...":
                    cid = opcs[sel_id]
                    c_obj = next((x for x in cargas if x['id'] == cid), None)
                    accion = st.radio("Acción:", ["Editar", "Eliminar"], horizontal=True)
                    if accion == "Eliminar":
                        if st.button("🔴 Confirmar Eliminar"):
                            db.collection("carga_academica").document(cid).delete()
                            st.success("Eliminado"); time.sleep(1); st.rerun()
                    elif accion == "Editar":
                        with st.form("edit_carga"):
                            nm = st.multiselect("Materias", LISTA_MATERIAS, default=[m for m in c_obj['materias'] if m in LISTA_MATERIAS])
                            ng = st.selectbox("Grado", LISTA_GRADOS_TODO, index=LISTA_GRADOS_TODO.index(c_obj['grado']) if c_obj['grado'] in LISTA_GRADOS_TODO else 0)
                            if st.form_submit_button("Actualizar"):
                                db.collection("carga_academica").document(cid).update({"materias": nm, "grado": ng})
                                st.success("Actualizado"); time.sleep(1); st.rerun()

    with t4:
        docs_admin = db.collection("maestros_perfil").stream()
        profes = [{"id": d.id, **d.to_dict()} for d in docs_admin]
        if profes:
            opcs_p = {f"{p.get('codigo','?')} - {p['nombre']}": p for p in profes}
            sel_p = st.selectbox("Editar Docente:", ["Seleccionar..."] + list(opcs_p.keys()))
            if sel_p != "Seleccionar...":
                p_obj = opcs_p[sel_p]
                with st.form("edit_prof"):
                    nc = st.text_input("Nombre", p_obj['nombre'])
                    nt = st.text_input("Tel", p_obj.get('contacto',{}).get('tel',''))
                    if st.form_submit_button("Actualizar Perfil"):
                        db.collection("maestros_perfil").document(p_obj['id']).update({"nombre": nc, "contacto.tel": nt})
                        st.success("Actualizado"); time.sleep(1); st.rerun()

    with t5:
        docs_p = db.collection("maestros_perfil").stream()
        lista_p = [d.to_dict() for d in docs_p]
        if lista_p:
            df_p = pd.DataFrame(lista_p)
            if 'codigo' not in df_p.columns: df_p['codigo'] = "S/C"
            st.dataframe(df_p[['codigo', 'nombre', 'turno_base']], use_container_width=True)

# ==========================================
# 4. CONSULTA ALUMNOS
# ==========================================
elif opcion == "Consulta Alumnos":
    st.title("🔎 Directorio de Estudiantes")
    modo = st.radio("Buscar por:", ["NIE", "Grado"], horizontal=True)
    alum = None
    
    if modo == "NIE":
        n = st.text_input("NIE:")
        if st.button("Buscar") and n:
            d = db.collection("alumnos").document(n).get()
            if d.exists: alum = d.to_dict()
            else: st.error("No encontrado")
    else:
        g = st.selectbox("Grado", ["Todos"] + LISTA_GRADOS_TODO)
        q = db.collection("alumnos")
        if g != "Todos": q = q.where("grado_actual", "==", g)
        l = [d.to_dict() for d in q.stream()]
        opcs = {f"{a['nie']} - {a['nombre_completo']}": a for a in l}
        sel = st.selectbox("Alumno:", ["Seleccionar..."] + list(opcs.keys()))
        if sel != "Seleccionar...": alum = opcs[sel]

    if alum:
        st.markdown("---")
        # --- DISEÑO LIMPIO Y FIJO ---
        c1, c2 = st.columns([1, 4])
        with c1: st.image(alum.get('documentos',{}).get('foto_url', "https://via.placeholder.com/150"), width=120)
        with c2: 
            st.title(alum['nombre_completo'])
            st.markdown(f"**NIE:** {alum['nie']} | **Grado:** {alum['grado_actual']} | **Turno:** {alum.get('turno')}")
            st.caption(f"Responsable: {alum.get('encargado',{}).get('nombre')}")

        t1, t2, t3, t4 = st.tabs(["General", "Carga", "Finanzas", "🖨️ Boleta de Notas"])
        
        with t1:
            st.write(f"**Dirección:** {alum.get('encargado',{}).get('direccion')}")
            st.write(f"**Teléfono:** {alum.get('encargado',{}).get('telefono')}")
            docs = alum.get('documentos',{}).get('doc_urls', [])
            if alum.get('documentos',{}).get('doc_url'): docs.append(alum.get('documentos',{}).get('doc_url'))
            docs = list(set(docs))
            if docs:
                st.success(f"{len(docs)} documentos adjuntos")
                for i, u in enumerate(docs): st.link_button(f"📄 Documento {i+1}", u)
            else: st.info("Sin documentos")

        with t2:
            cargas = db.collection("carga_academica").where("grado", "==", alum['grado_actual']).stream()
            lc = [c.to_dict() for c in cargas]
            if lc:
                for c in lc:
                    with st.container(border=True):
                        c1, c2 = st.columns([2,3])
                        c1.markdown(f"<b>{c['nombre_docente']}</b>", unsafe_allow_html=True)
                        c2.write(", ".join(c['materias']))
            else: st.warning("Sin carga asignada")

        with t3:
            pagos = db.collection("finanzas").where("alumno_nie", "==", alum['nie']).where("tipo", "==", "ingreso").stream()
            lp = [{"id":p.id, **p.to_dict()} for p in pagos]
            if lp:
                df = pd.DataFrame(lp).sort_values(by="fecha_legible", ascending=False)
                if "observaciones" not in df: df["observaciones"] = ""
                st.dataframe(df[['fecha_legible', 'descripcion', 'monto', 'observaciones']], use_container_width=True)
                # (Aquí iría la lógica de reimpresión si se desea, por simplicidad solo muestro la tabla)
            else: st.info("Sin pagos registrados")

        with t4: # --- BOLETA DE NOTAS AUTOMÁTICA ---
            st.subheader(f"Boleta de Calificaciones {datetime.now().year}")
            
            notas_ref = db.collection("notas").where("nie", "==", alum['nie']).stream()
            notas_map = {}
            for doc in notas_ref:
                d = doc.to_dict()
                if d['materia'] not in notas_map: notas_map[d['materia']] = {}
                notas_map[d['materia']][d['mes']] = d['promedio_final']
            
            if not notas_map:
                st.warning("No hay notas registradas.")
            else:
                filas = []
                for mat in LISTA_MATERIAS:
                    if mat in notas_map:
                        n = notas_map[mat]
                        # Cálculo Trimestral Simplificado (Promedio de lo existente)
                        t1_meses = [n.get("Febrero"), n.get("Marzo"), n.get("Abril")]
                        t1_vals = [x for x in t1_meses if x is not None]
                        t1 = sum(t1_vals)/len(t1_vals) if t1_vals else 0
                        
                        t2_meses = [n.get("Mayo"), n.get("Junio"), n.get("Julio")]
                        t2_vals = [x for x in t2_meses if x is not None]
                        t2 = sum(t2_vals)/len(t2_vals) if t2_vals else 0
                        
                        t3_meses = [n.get("Agosto"), n.get("Septiembre"), n.get("Octubre")]
                        t3_vals = [x for x in t3_meses if x is not None]
                        t3 = sum(t3_vals)/len(t3_vals) if t3_vals else 0
                        
                        fin_vals = [x for x in [t1, t2, t3] if x > 0]
                        fin = sum(fin_vals)/len(fin_vals) if fin_vals else 0
                        
                        filas.append({
                            "Asignatura": mat,
                            "F": n.get("Febrero", "-"), "M": n.get("Marzo", "-"), "A": n.get("Abril", "-"), "TI": round(t1,1) if t1 else "-",
                            "M.": n.get("Mayo", "-"), "J": n.get("Junio", "-"), "J.": n.get("Julio", "-"), "TII": round(t2,1) if t2 else "-",
                            "A.": n.get("Agosto", "-"), "S": n.get("Septiembre", "-"), "O": n.get("Octubre", "-"), "TIII": round(t3,1) if t3 else "-",
                            "FINAL": round(fin,1) if fin else "-"
                        })
                
                df_b = pd.DataFrame(filas)
                st.dataframe(df_b, use_container_width=True, hide_index=True)
                
                # HTML Reporte
                html_rows = ""
                for _, r in df_b.iterrows():
                    html_rows += f"<tr><td style='text-align:left'>{r['Asignatura']}</td><td>{r['F']}</td><td>{r['M']}</td><td>{r['A']}</td><td style='background:#eee'><b>{r['TI']}</b></td><td>{r['M.']}</td><td>{r['J']}</td><td>{r['J.']}</td><td style='background:#eee'><b>{r['TII']}</b></td><td>{r['A.']}</td><td>{r['S']}</td><td>{r['O']}</td><td style='background:#eee'><b>{r['TIII']}</b></td><td style='background:#333;color:white'><b>{r['FINAL']}</b></td></tr>"
                
                logo = get_image_base64("logo.png"); h_img = f'<img src="{logo}" height="60">' if logo else ""
                html = f"""
                <div style="font-family:Arial; font-size:12px;">
                    <div style="display:flex; align-items:center;">{h_img}<div style="margin-left:15px"><h3>COLEGIO PROFA. BLANCA ELENA</h3><p>BOLETA DE CALIFICACIONES</p></div></div>
                    <div style="border:1px solid #000; padding:5px; margin:10px 0;"><b>Alumno:</b> {alum['nombre_completo']} | <b>Grado:</b> {alum['grado_actual']}</div>
                    <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
                        <tr style="background:#ddd;"><td>ASIGNATURA</td><td>F</td><td>M</td><td>A</td><td>T1</td><td>M</td><td>J</td><td>J</td><td>T2</td><td>A</td><td>S</td><td>O</td><td>T3</td><td>FIN</td></tr>
                        {html_rows}
                    </table>
                    <br><br><div style="display:flex; justify-content:space-between; text-align:center;"><div style="border-top:1px solid #000; width:30%">Orientador</div><div style="border-top:1px solid #000; width:30%">Dirección</div></div>
                </div>
                """
                components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

# ==========================================
# 5. FINANZAS
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Finanzas")
    if 'recibo_temp' not in st.session_state: st.session_state.recibo_temp = None
    if 'reporte_html' not in st.session_state: st.session_state.reporte_html = None

    if st.session_state.recibo_temp:
        r = st.session_state.recibo_temp
        es_ingreso = r.get('tipo') == 'ingreso'
        color = "#2e7d32" if es_ingreso else "#c62828"
        titulo = "RECIBO DE INGRESO" if es_ingreso else "COMPROBANTE DE EGRESO"
        img = get_image_base64("logo.png"); h_img = f'<img src="{img}" height="70">' if img else ""
        
        st.markdown("""<style>@media print { body * { visibility: hidden; } .ticket, .ticket * { visibility: visible; } .ticket { position: absolute; left: 0; top: 0; width: 100%; margin: 0; } }</style>""", unsafe_allow_html=True)
        
        html = f"""
        <div class="ticket" style="font-family:Arial; border:1px solid #ccc; padding:20px; color:black; background:white;">
            <div style="display:flex; justify-content:space-between; background:{color}; color:white; padding:15px;">
                <div style="display:flex; gap:10px;">{h_img}<div><h3 style="margin:0;color:white;">COLEGIO BLANCA ELENA</h3></div></div>
                <h4>{titulo}</h4>
            </div>
            <div style="padding:20px;">
                <p><b>Fecha:</b> {r['fecha_legible']}</p>
                <p><b>Persona:</b> {r.get('nombre_persona')}</p>
                <p><b>Concepto:</b> {r['descripcion']}</p>
                <p><b>Detalle:</b> {r.get('observaciones','')}</p>
                <h1 style="text-align:right; color:{color};">${r['monto']:.2f}</h1>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        c1, c2 = st.columns([1,4])
        if c1.button("❌ Cerrar"): st.session_state.recibo_temp = None; st.rerun()
        with c2: components.html(f"""<script>function p(){{window.parent.print()}}</script><button onclick="p()" style="background:green;color:white;padding:10px;border:none;">🖨️ IMPRIMIR</button>""", height=50)
    
    elif st.session_state.reporte_html:
        st.markdown("""<style>@media print { body * { visibility: hidden; } .rep, .rep * { visibility: visible; } .rep { position: absolute; left: 0; top: 0; width: 100%; background: white; color: black !important; } }</style>""", unsafe_allow_html=True)
        st.markdown(st.session_state.reporte_html, unsafe_allow_html=True)
        if st.button("⬅️ Volver"): st.session_state.reporte_html = None; st.rerun()

    else:
        t1, t2, t3 = st.tabs(["Ingresos", "Gastos", "Reportes"])
        with t1:
            c1, c2 = st.columns([1,2])
            nie = c1.text_input("NIE Alumno:")
            if c1.button("🔍") and nie:
                d = db.collection("alumnos").document(nie).get()
                if d.exists: st.session_state.pago_alum = d.to_dict()
                else: st.error("No existe")
            if st.session_state.get("pago_alum"):
                a = st.session_state.pago_alum
                with c2.form("fi"):
                    st.info(f"Cobro a: {a['nombre_completo']}")
                    con = st.selectbox("Concepto", ["Mensualidad", "Matrícula", "Otros"])
                    mes = st.selectbox("Mes", LISTA_MESES)
                    mon = st.number_input("Monto", min_value=0.01)
                    obs = st.text_area("Detalle")
                    if st.form_submit_button("✅ Cobrar"):
                        data = {"tipo": "ingreso", "descripcion": f"{con} - {mes}", "monto": mon, "nombre_persona": a['nombre_completo'], "alumno_nie": a['nie'], "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": datetime.now().strftime("%d/%m/%Y")}
                        db.collection("finanzas").add(data)
                        st.session_state.recibo_temp = data; st.session_state.pago_alum = None; st.rerun()
        with t2:
            cat = st.selectbox("Categoría", ["Planilla", "Servicios", "Otros"])
            with st.form("fe"):
                nom = st.text_input("Persona/Proveedor")
                mon = st.number_input("Monto", min_value=0.01)
                obs = st.text_area("Detalle")
                if st.form_submit_button("Registrar Gasto"):
                    data = {"tipo": "egreso", "descripcion": cat, "monto": mon, "nombre_persona": nom, "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": datetime.now().strftime("%d/%m/%Y")}
                    db.collection("finanzas").add(data)
                    st.session_state.recibo_temp = data; st.rerun()
        with t3:
            if st.button("Generar Reporte PDF"):
                docs = db.collection("finanzas").order_by("fecha", direction=firestore.Query.DESCENDING).stream()
                rows = "".join([f"<tr><td>{d.to_dict()['fecha_legible']}</td><td>{d.to_dict()['tipo']}</td><td>{d.to_dict().get('nombre_persona')}</td><td>{d.to_dict()['descripcion']}</td><td>{d.to_dict().get('observaciones','')}</td><td>${d.to_dict()['monto']}</td></tr>" for d in docs])
                html = f"<table border='1' style='width:100%; border-collapse:collapse;'><tr><th>FECHA</th><th>TIPO</th><th>PERSONA</th><th>CONCEPTO</th><th>DETALLE</th><th>MONTO</th></tr>{rows}</table>"
                components.html(f"""<html><body><h2>REPORTE</h2>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

# ==========================================
# 6. NOTAS (1º A 9º)
# ==========================================
elif opcion == "Notas (1º-9º)":
    st.title("📊 Notas")
    
    # 1. Selectores
    c1, c2, c3 = st.columns(3)
    grado = c1.selectbox("Grado", ["Seleccionar..."] + LISTA_GRADOS_NOTAS)
    materia = c2.selectbox("Materia", ["Seleccionar..."] + LISTA_MATERIAS)
    mes = c3.selectbox("Mes", LISTA_MESES)

    if grado != "Seleccionar..." and materia != "Seleccionar...":
        # 2. Buscar Alumnos
        docs = db.collection("alumnos").where("grado_actual", "==", grado).stream()
        lista = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
        
        if not lista:
            st.warning(f"No hay alumnos en {grado}.")
        else:
            df = pd.DataFrame(lista).sort_values("Nombre")
            id_doc = f"{grado}_{materia}_{mes}".replace(" ","_")
            
            # 3. Definir Columnas según Materia
            if materia == "Conducta":
                cols = ["Nota Mensual"]
            else:
                cols = ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
            
            # 4. Cargar Datos Previos
            doc_ref = db.collection("notas_mensuales").document(id_doc).get()
            if doc_ref.exists:
                datos_db = doc_ref.to_dict().get('detalles', {})
                for c in cols: df[c] = df["NIE"].map(lambda x: datos_db.get(x, {}).get(c, 0.0))
            else:
                for c in cols: df[c] = 0.0
            
            # Añadir columna de Promedio (Visual)
            df["Promedio"] = 0.0
            if doc_ref.exists:
                df["Promedio"] = df["NIE"].map(lambda x: datos_db.get(x, {}).get("Promedio", 0.0))

            # 5. Editor
            config = {
                "NIE": st.column_config.TextColumn(disabled=True),
                "Nombre": st.column_config.TextColumn(disabled=True, width="medium"),
                "Promedio": st.column_config.NumberColumn(disabled=True, format="%.1f")
            }
            for c in cols: config[c] = st.column_config.NumberColumn(min_value=0, max_value=10, step=0.1, format="%.1f")
            
            st.info("Ingrese las notas. El promedio se calcula al Guardar.")
            edited = st.data_editor(df, column_config=config, hide_index=True, use_container_width=True, key=id_doc)
            
            # 6. Guardado
            if st.button("💾 Guardar Notas", type="primary"):
                batch = db.batch()
                detalles = {}
                for _, row in edited.iterrows():
                    # Cálculo
                    if materia == "Conducta":
                        prom = row["Nota Mensual"]
                    else:
                        prom = (row["Act1 (25%)"]*0.25 + row["Act2 (25%)"]*0.25 + 
                                row["Alt1 (10%)"]*0.10 + row["Alt2 (10%)"]*0.10 + 
                                row["Examen (30%)"]*0.30)
                    
                    detalles[row["NIE"]] = {c: row[c] for c in cols}
                    detalles[row["NIE"]]["Promedio"] = round(prom, 1)
                    
                    # Individual (Boleta)
                    ref = db.collection("notas").document(f"{row['NIE']}_{id_doc}")
                    batch.set(ref, {"nie": row["NIE"], "grado": grado, "materia": materia, "mes": mes, "promedio_final": round(prom, 1)})
                
                # Grupal (Editor)
                db.collection("notas_mensuales").document(id_doc).set({"grado": grado, "materia": materia, "mes": mes, "detalles": detalles})
                batch.commit()
                st.success("✅ Guardado y Calculado")
                time.sleep(1); st.rerun()

# 7. CONFIG
elif opcion == "Configuración":
    st.header("⚙️ Configuración")
    with st.expander("Borrar Todo"):
        if st.button("Resetear") and st.text_input("Confirmar:") == "BORRAR":
            st.warning("Desactivado")