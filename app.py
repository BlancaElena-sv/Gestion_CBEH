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
            cred = None
            # 1. Prioridad Local (Windows)
            if os.path.exists("credenciales.json"):
                cred = credentials.Certificate("credenciales.json")
            elif os.path.exists("credenciales"): 
                cred = credentials.Certificate("credenciales")
            # 2. Prioridad Nube (Streamlit Cloud)
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

    with t3: # ADMIN CARGAS (RECUPERADO)
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
            
            # Selector inteligente de edición
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

    with t4: # ADMIN DOCENTES (RECUPERADO)
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
# 4. CONSULTA ALUMNOS (CON BOLETA Y FINANZAS)
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
        # MODO EDICIÓN
        if st.toggle("✏️ Habilitar Edición"):
            with st.form("edit_alum"):
                c1, c2 = st.columns(2)
                nn = c1.text_input("Nombres", alum.get('nombres',''))
                na = c2.text_input("Apellidos", alum.get('apellidos',''))
                ng = c1.selectbox("Grado", LISTA_GRADOS_TODO, index=LISTA_GRADOS_TODO.index(alum.get('grado_actual')) if alum.get('grado_actual') in LISTA_GRADOS_TODO else 0)
                nt = c2.selectbox("Turno", ["Matutino", "Vespertino"])
                st.markdown("---")
                nf = st.file_uploader("Actualizar Foto", ["jpg","png"])
                nd = st.file_uploader("Agregar Documentos", ["pdf","jpg"], accept_multiple_files=True)
                if st.form_submit_button("Guardar Cambios"):
                    ruta = f"expedientes/{alum['nie']}"
                    docs_act = alum.get('documentos', {})
                    urls_ex = docs_act.get('doc_urls', [])
                    if docs_act.get('doc_url'): urls_ex.append(docs_act.get('doc_url'))
                    
                    if nd:
                        for f in nd: 
                            u = subir_archivo(f, ruta)
                            if u: urls_ex.append(u)
                    
                    uf = subir_archivo(nf, ruta) if nf else docs_act.get('foto_url')
                    
                    db.collection("alumnos").document(alum['nie']).update({
                        "nombres": nn, "apellidos": na, "nombre_completo": f"{nn} {na}",
                        "grado_actual": ng, "turno": nt,
                        "documentos": {"foto_url": uf, "doc_urls": urls_ex}
                    })
                    st.success("Actualizado"); time.sleep(1.5); st.rerun()

        # VISTA NORMAL
        c1, c2 = st.columns([1, 4])
        with c1: st.image(alum.get('documentos',{}).get('foto_url', "https://via.placeholder.com/150"), width=120)
        with c2: 
            st.title(alum['nombre_completo'])
            st.markdown(f"**NIE:** {alum['nie']} | **Grado:** {alum['grado_actual']} | **Turno:** {alum.get('turno')}")

        t1, t2, t3, t4 = st.tabs(["General", "Carga", "Finanzas", "🖨️ Boleta Notas"])
        
        with t1:
            st.write(f"**Responsable:** {alum.get('encargado',{}).get('nombre')}")
            st.write(f"**Teléfono:** {alum.get('encargado',{}).get('telefono')}")
            docs = alum.get('documentos',{}).get('doc_urls', [])
            if alum.get('documentos',{}).get('doc_url'): docs.append(alum.get('documentos',{}).get('doc_url'))
            docs = list(set(docs))
            if docs:
                st.success(f"{len(docs)} documentos adjuntos")
                for i, u in enumerate(docs): st.link_button(f"📄 Ver Documento {i+1}", u)
            else: st.info("Sin documentos")

        with t2:
            st.subheader(f"Carga: {alum.get('grado_actual')}")
            cargas = db.collection("carga_academica").where("grado", "==", alum.get('grado_actual')).stream()
            lc = [c.to_dict() for c in cargas]
            if lc:
                for c in lc:
                    with st.container(border=True):
                        c1, c2 = st.columns([2,3])
                        c1.markdown(f"<b>{c['nombre_docente']}</b>", unsafe_allow_html=True)
                        c2.write(", ".join(c['materias']))
            else: st.warning("Sin carga asignada")

        with t3: # FINANZAS EN CONSULTA (RECUPERADO)
            st.subheader("Historial de Pagos")
            pagos = db.collection("finanzas").where("alumno_nie", "==", alum['nie']).where("tipo", "==", "ingreso").stream()
            lp = [{"id": p.id, **p.to_dict()} for p in pagos]
            if lp:
                df_p = pd.DataFrame(lp).sort_values(by="fecha_legible", ascending=False)
                if "observaciones" not in df_p: df_p["observaciones"] = ""
                st.dataframe(df_p[['fecha_legible', 'descripcion', 'monto', 'observaciones']], use_container_width=True)
                
                # REIMPRESIÓN
                sel_p = st.selectbox("Reimprimir Recibo:", ["Seleccionar..."] + [f"{p['fecha_legible']} - ${p['monto']}" for p in lp])
                if sel_p != "Seleccionar...":
                    if st.button("📄 Generar Vista Previa"):
                        # Truco: usar el mismo HTML de recibos
                        p_obj = next(p for p in lp if f"{p['fecha_legible']} - ${p['monto']}" == sel_p)
                        color = "#2e7d32"
                        img = get_image_base64("logo.png"); img_h = f'<img src="{img}" style="height:60px;">' if img else ""
                        html = f"""
                        <div style="border:1px solid #ccc; padding:20px; background:white; color:black;">
                            <div style="background:{color}; color:white; padding:15px; display:flex; justify-content:space-between;">
                                <div style="display:flex; gap:15px;"><div>{img_h}</div><div><h3>COLEGIO PROFA. BLANCA ELENA</h3><p>COPIA DE RECIBO</p></div></div>
                                <div><h4>Ref: {p_obj['id'][-6:]}</h4></div>
                            </div>
                            <div style="padding:20px;">
                                <p><b>Fecha:</b> {p_obj['fecha_legible']}</p>
                                <p><b>Alumno:</b> {p_obj.get('nombre_persona')}</p>
                                <p><b>Concepto:</b> {p_obj['descripcion']}</p>
                                <p><b>Nota:</b> {p_obj.get('observaciones','')}</p>
                                <h2 style="text-align:right; color:{color};">${p_obj['monto']:.2f}</h2>
                            </div>
                        </div>
                        """
                        st.markdown(html, unsafe_allow_html=True)
                        components.html(f"""<script>function p(){{window.print()}}</script><button onclick="p()" style="background:green;color:white;padding:10px;border:none;border-radius:5px;">🖨️ Imprimir</button>""", height=50)

        with t4: # BOLETA AUTOMÁTICA (NUEVO)
            st.subheader(f"Boleta de Notas {datetime.now().year}")
            notas_ref = db.collection("notas").where("nie", "==", alum['nie']).stream()
            notas_map = {}
            for doc in notas_ref:
                d = doc.to_dict()
                if d['materia'] not in notas_map: notas_map[d['materia']] = {}
                notas_map[d['materia']][d['mes']] = d['promedio_final']
            
            if not notas_map: st.warning("Sin calificaciones registradas")
            else:
                filas = []
                for mat in LISTA_MATERIAS:
                    if mat in notas_map:
                        n = notas_map[mat]
                        # Trimestres
                        t1 = (n.get("Febrero",0) + n.get("Marzo",0) + n.get("Abril",0)) / 3
                        t2 = (n.get("Mayo",0) + n.get("Junio",0) + n.get("Julio",0)) / 3
                        t3 = (n.get("Agosto",0) + n.get("Septiembre",0) + n.get("Octubre",0)) / 3
                        fin = (t1+t2+t3)/3
                        filas.append({
                            "Asignatura": mat,
                            "F": n.get("Febrero",0), "M": n.get("Marzo",0), "A": n.get("Abril",0), "I.T": round(t1,1),
                            "M.": n.get("Mayo",0), "J": n.get("Junio",0), "J.": n.get("Julio",0), "II.T": round(t2,1),
                            "A.": n.get("Agosto",0), "S": n.get("Septiembre",0), "O": n.get("Octubre",0), "III.T": round(t3,1),
                            "FINAL": round(fin,1)
                        })
                
                df_b = pd.DataFrame(filas)
                st.dataframe(df_b, use_container_width=True, hide_index=True)
                
                # HTML Boleta
                html_tr = ""
                for _, r in df_b.iterrows():
                    html_tr += f"<tr><td style='text-align:left;'>{r['Asignatura']}</td><td>{r['F']}</td><td>{r['M']}</td><td>{r['A']}</td><td style='background:#eee;font-weight:bold;'>{r['I.T']}</td><td>{r['M.']}</td><td>{r['J']}</td><td>{r['J.']}</td><td style='background:#eee;font-weight:bold;'>{r['II.T']}</td><td>{r['A.']}</td><td>{r['S']}</td><td>{r['O']}</td><td style='background:#eee;font-weight:bold;'>{r['III.T']}</td><td style='background:#333;color:white;font-weight:bold;'>{r['FINAL']}</td></tr>"
                
                img = get_image_base64("logo.png"); h_img = f'<img src="{img}" height="60">' if img else ""
                html_bol = f"""
                <div style="font-family:Arial; font-size:12px;">
                    <div style="display:flex; align-items:center; margin-bottom:10px;">{h_img}<div style="margin-left:15px;"><h2>COLEGIO PROFA. BLANCA ELENA</h2><h4>BOLETA DE CALIFICACIONES</h4></div></div>
                    <div style="border:1px solid #000; padding:5px; margin-bottom:10px;"><b>Alumno:</b> {alum['nombre_completo']} | <b>Grado:</b> {alum['grado_actual']}</div>
                    <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
                        <tr style="background:#ddd; font-weight:bold;"><td>MATERIA</td><td>F</td><td>M</td><td>A</td><td>I.T</td><td>M</td><td>J</td><td>J</td><td>II.T</td><td>A</td><td>S</td><td>O</td><td>III.T</td><td>FIN</td></tr>
                        {html_tr}
                    </table>
                    <br><br><div style="display:flex; justify-content:space-between; text-align:center;"><div style="border-top:1px solid #000; width:30%;">Orientador</div><div style="border-top:1px solid #000; width:30%;">Dirección</div></div>
                </div>
                """
                components.html(f"""<html><body>{html_bol}<br><button onclick="window.print()">🖨️ IMPRIMIR</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

# ==========================================
# 5. FINANZAS (RECUPERADO FULL)
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Finanzas")
    if 'recibo_temp' not in st.session_state: st.session_state.recibo_temp = None
    if 'reporte_html' not in st.session_state: st.session_state.reporte_html = None

    if st.session_state.recibo_temp:
        # VISTA DE RECIBO GENERADO
        r = st.session_state.recibo_temp
        color = "#2e7d32" if r['tipo'] == 'ingreso' else "#c62828"
        titulo = "RECIBO DE INGRESO" if r['tipo'] == 'ingreso' else "COMPROBANTE EGRESO"
        img = get_image_base64("logo.png"); h_img = f'<img src="{img}" height="70">' if img else ""
        
        # CSS NUCLEAR
        st.markdown("""<style>@media print { body * { visibility: hidden; } .ticket, .ticket * { visibility: visible; } .ticket { position: absolute; left: 0; top: 0; width: 100%; background: white; color: black !important; } }</style>""", unsafe_allow_html=True)
        
        html = f"""
        <div class="ticket" style="font-family:Arial; color:black; background:white; border:1px solid #ccc; padding:20px;">
            <div style="background:{color}; color:white !important; padding:15px; display:flex; justify-content:space-between;">
                <div style="display:flex; gap:15px;"><div>{h_img}</div><div><h3 style="margin:0;color:white;">COLEGIO BLANCA ELENA</h3></div></div>
                <div><h4 style="margin:0;color:white;">{titulo}</h4></div>
            </div>
            <div style="padding:20px;">
                <p><b>Fecha:</b> {r['fecha_legible']}</p>
                <p><b>Persona:</b> {r.get('nombre_persona')}</p>
                <p><b>Concepto:</b> {r['descripcion']}</p>
                <p><b>Detalle:</b> {r.get('observaciones','')}</p>
                <h1 style="text-align:right; color:{color};">${r['monto']:.2f}</h1>
            </div>
            <div style="border-top:2px dashed #ccc; text-align:center; font-size:10px; margin-top:20px;">✂️ CORTE AQUÍ</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        c1, c2 = st.columns([1,4])
        if c1.button("❌ Cerrar"): st.session_state.recibo_temp = None; st.rerun()
        with c2: components.html(f"""<script>function p(){{window.parent.print()}}</script><button onclick="p()" style="background:green;color:white;padding:10px;border:none;border-radius:5px;">🖨️ IMPRIMIR</button>""", height=50)

    elif st.session_state.reporte_html:
        st.markdown("""<style>@media print { body * { visibility: hidden; } .rep, .rep * { visibility: visible; } .rep { position: absolute; left: 0; top: 0; width: 100%; background: white; color: black !important; } }</style>""", unsafe_allow_html=True)
        st.markdown(st.session_state.reporte_html, unsafe_allow_html=True)
        if st.button("⬅️ Volver"): st.session_state.reporte_html = None; st.rerun()

    else:
        # PESTAÑAS FINANZAS
        t1, t2, t3 = st.tabs(["Ingresos", "Gastos", "Reportes"])
        with t1:
            c1, c2 = st.columns([1,2])
            nie = c1.text_input("Buscar NIE:")
            if c1.button("🔍") and nie:
                d = db.collection("alumnos").document(nie).get()
                if d.exists: st.session_state.pago_alum = d.to_dict()
                else: st.error("No existe")
            
            if st.session_state.get("pago_alum"):
                a = st.session_state.pago_alum
                with c2.form("pago_in"):
                    st.info(f"Cobrando a: {a['nombre_completo']}")
                    con = st.selectbox("Concepto", ["Mensualidad", "Matrícula", "Otros"])
                    mes = st.selectbox("Mes", LISTA_MESES)
                    mon = st.number_input("Monto", min_value=0.01)
                    obs = st.text_area("Observaciones (Detalle)")
                    if st.form_submit_button("✅ Cobrar"):
                        data = {"tipo": "ingreso", "descripcion": f"{con} - {mes}", "monto": mon, "nombre_persona": a['nombre_completo'], "alumno_nie": a['nie'], "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")}
                        db.collection("finanzas").add(data)
                        st.session_state.recibo_temp = data
                        st.session_state.pago_alum = None
                        st.rerun()

        with t2:
            st.subheader("Registrar Gasto")
            cat = st.selectbox("Categoría", ["Planilla", "Servicios", "Materiales", "Otros"])
            with st.form("pago_out"):
                c1, c2 = st.columns(2)
                nom = ""
                if cat == "Planilla":
                    docs = db.collection("maestros_perfil").stream()
                    l = {d.to_dict()['nombre']: d.id for d in docs}
                    nom = c1.selectbox("Docente", list(l.keys()))
                else: nom = c1.text_input("Proveedor/Persona")
                mon = c2.number_input("Monto", min_value=0.01)
                obs = st.text_area("Detalle")
                if st.form_submit_button("🔴 Registrar Gasto"):
                    data = {"tipo": "egreso", "descripcion": cat, "monto": mon, "nombre_persona": nom, "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")}
                    db.collection("finanzas").add(data)
                    st.session_state.recibo_temp = data
                    st.rerun()

        with t3:
            st.subheader("Reportes")
            c1, c2 = st.columns(2)
            fi = c1.date_input("Desde", value=date(datetime.now().year, 1, 1))
            ff = c2.date_input("Hasta")
            if st.button("Generar Reporte PDF"):
                docs = db.collection("finanzas").order_by("fecha", direction=firestore.Query.DESCENDING).stream()
                rows = []
                for d in docs:
                    dd = d.to_dict()
                    dt = dd.get("fecha_dt") or dd.get("fecha")
                    if dt:
                        try: f_obj = dt.date()
                        except: f_obj = datetime.now().date()
                        if fi <= f_obj <= ff:
                            rows.append(dd)
                
                if rows:
                    df = pd.DataFrame(rows)
                    # HTML Reporte
                    h_rows = ""
                    for _, r in df.iterrows():
                        col = "green" if r['tipo'] == 'ingreso' else "red"
                        h_rows += f"<tr><td>{r['fecha_legible']}</td><td style='color:{col}'>{r['tipo'].upper()}</td><td>{r.get('nombre_persona')}</td><td>{r['descripcion']}</td><td>{r.get('observaciones','')}</td><td style='text-align:right'>${r['monto']:.2f}</td></tr>"
                    
                    img = get_image_base64("logo.png"); h_img = f'<img src="{img}" height="50">' if img else ""
                    html_rep = f"""
                    <div class="rep" style="font-family:Arial; padding:20px; color:black;">
                        <div style="display:flex; align-items:center; border-bottom:2px solid #333;">{h_img} <h2 style="margin-left:15px;">REPORTE FINANCIERO</h2></div>
                        <p>Del {fi} al {ff}</p>
                        <table style="width:100%; border-collapse:collapse; font-size:12px;">
                            <tr style="background:#eee; text-align:left;"><th>FECHA</th><th>TIPO</th><th>PERSONA</th><th>CONCEPTO</th><th>DETALLE</th><th>MONTO</th></tr>
                            {h_rows}
                        </table>
                    </div>
                    """
                    st.session_state.reporte_html = html_rep
                    st.rerun()
                else: st.warning("Sin datos en ese rango")

# ==========================================
# 6. NOTAS (NUEVO)
# ==========================================
elif opcion == "Notas (1º a 9º)":
    st.title("📊 Registro de Notas")
    c1, c2, c3 = st.columns(3)
    grado = c1.selectbox("Grado", ["Seleccionar..."] + LISTA_GRADOS_NOTAS)
    materia = c2.selectbox("Materia", ["Seleccionar..."] + LISTA_MATERIAS)
    mes = c3.selectbox("Mes", LISTA_MESES)
    
    if grado != "Seleccionar..." and materia != "Seleccionar...":
        docs = db.collection("alumnos").where("grado_actual", "==", grado).stream()
        alumnos = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
        
        if not alumnos: st.warning("Sin alumnos.")
        else:
            df = pd.DataFrame(alumnos).sort_values("Nombre")
            id_doc = f"{grado}_{materia}_{mes}".replace(" ","_")
            doc_ref = db.collection("notas_mensuales").document(id_doc).get()
            
            cols = ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
            if doc_ref.exists:
                dd = doc_ref.to_dict().get('detalles', {})
                for c in cols: df[c] = df["NIE"].map(lambda x: dd.get(x, {}).get(c, 0.0))
            else:
                for c in cols: df[c] = 0.0
            
            cfg = {"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True, width="medium")}
            for c in cols: cfg[c] = st.column_config.NumberColumn(min_value=0, max_value=10, step=0.1, format="%.1f")
            
            res = st.data_editor(df, column_config=cfg, hide_index=True, use_container_width=True, key=id_doc)
            
            if st.button("💾 Guardar Notas", type="primary"):
                batch = db.batch()
                detalles = {}
                for _, r in res.iterrows():
                    prom = (r[cols[0]]*0.25 + r[cols[1]]*0.25 + r[cols[2]]*0.10 + r[cols[3]]*0.10 + r[cols[4]]*0.30)
                    detalles[r["NIE"]] = {c: r[c] for c in cols}
                    detalles[r["NIE"]]["Promedio"] = round(prom, 1)
                    
                    # Guardar para boleta individual
                    ref = db.collection("notas").document(f"{r['NIE']}_{id_doc}")
                    batch.set(ref, {"nie": r["NIE"], "grado": grado, "materia": materia, "mes": mes, "promedio_final": round(prom, 1)})
                
                # Guardar grupo
                db.collection("notas_mensuales").document(id_doc).set({"grado": grado, "materia": materia, "mes": mes, "detalles": detalles})
                batch.commit()
                st.success("Guardado")

# ==========================================
# 7. CONFIGURACIÓN
# ==========================================
elif opcion == "Configuración":
    st.header("⚙️ Configuración")
    with st.expander("PELIGRO: BORRAR TODO"):
        if st.button("Resetear Base de Datos") and st.text_input("Confirmar:") == "BORRAR":
            colls = ["alumnos", "maestros_perfil", "carga_academica", "finanzas", "notas", "notas_mensuales"]
            for c in colls:
                for d in db.collection(c).stream(): d.reference.delete()
            st.success("Reseteado")