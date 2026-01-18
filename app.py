import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime, date
import base64

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión Escolar", layout="wide", page_icon="🎓")

# --- CONEXIÓN INTELIGENTE ---
@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        if "firebase_key" in st.secrets:
            key_dict = dict(st.secrets["firebase_key"])
            cred = credentials.Certificate(key_dict)
        else:
            cred = credentials.Certificate("credenciales.json") 
        firebase_admin.initialize_app(cred, {'storageBucket': 'gestioncbeh.firebasestorage.app'})
    return firestore.client()

try:
    db = conectar_firebase()
    conexion_exitosa = True
except Exception as e:
    st.error(f"⚠️ Error conectando a Firebase: {e}")
    conexion_exitosa = False

# --- FUNCIONES AUXILIARES ---
def subir_archivo(archivo, ruta_carpeta):
    if archivo is None: return None
    try:
        bucket = storage.bucket()
        nombre_limpio = archivo.name.replace(" ", "_")
        ruta_completa = f"{ruta_carpeta}/{nombre_limpio}"
        blob = bucket.blob(ruta_completa)
        blob.upload_from_file(archivo)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"Error subiendo archivo: {e}")
        return None

def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded}"
    except:
        return "" 

# --- MENÚ LATERAL ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("⚠️ Falta 'logo.png'")
    st.markdown("---")
    opcion = st.radio("Menú Principal:", ["Inicio", "Inscripción Alumnos", "Gestión Maestros", "Consulta Alumnos", "Finanzas", "Notas", "Configuración"])
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
            grados = ["Kinder 4", "Kinder 5", "Kinder 6", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
            grado = st.selectbox("Grado a Matricular", grados)
            turno = st.selectbox("Turno*", ["Matutino", "Vespertino"])
            encargado = st.text_input("Nombre del Responsable")
            telefono = st.text_input("Teléfono de Contacto")
            direccion = st.text_area("Dirección de Residencia", height=100)
        
        st.markdown("---")
        st.subheader("Documentación Digital")
        col_doc1, col_doc2 = st.columns(2)
        with col_doc1: foto = st.file_uploader("📸 Foto de Perfil (Carnet)", type=["jpg", "png", "jpeg"])
        with col_doc2: doc_pdf = st.file_uploader("📂 Documentos (Partida/DUI) - Opcional", type=["pdf", "jpg"])
        
        enviado = st.form_submit_button("💾 Guardar Inscripción", type="primary")

        if enviado:
            if not nie or not nombres or not apellidos:
                st.error("⚠️ El NIE y los nombres son obligatorios.")
            else:
                with st.spinner("Guardando expediente..."):
                    ruta = f"expedientes/{nie}"
                    datos = {
                        "nie": nie, "nombre_completo": f"{nombres} {apellidos}", 
                        "nombres": nombres, "apellidos": apellidos,
                        "grado_actual": grado, "turno": turno, "estado": estado,
                        "encargado": {"nombre": encargado, "telefono": telefono, "direccion": direccion},
                        "documentos": {
                            "foto_url": subir_archivo(foto, ruta),
                            "doc_url": subir_archivo(doc_pdf, ruta)
                        },
                        "fecha_registro": firestore.SERVER_TIMESTAMP
                    }
                    db.collection("alumnos").document(nie).set(datos)
                    st.success(f"✅ ¡Alumno inscrito en el turno {turno}!")

# ==========================================
# 3. GESTIÓN DE MAESTROS (REDISEÑADO: PERFIL + CARGA)
# ==========================================
elif opcion == "Gestión Maestros":
    st.title("👩‍🏫 Plantilla Docente y Carga Académica")
    
    tab_perfil, tab_carga, tab_ver = st.tabs(["1️⃣ Registrar Docente", "2️⃣ Asignar Materias/Grados", "📋 Ver Planilla"])
    
    # Listas Maestras
    LISTA_GRADOS = ["Kinder 4", "Kinder 5", "Kinder 6", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
    LISTA_MATERIAS = ["Matemáticas", "Lenguaje y Literatura", "Ciencias Salud y M.A.", "Estudios Sociales", "Inglés", "Educación Artística", "Educación Física", "Moral y Cívica", "Informática", "Ortografía", "Caligrafía"]

    # --- TAB 1: CREAR EL PERFIL DEL MAESTRO (SOLO UNA VEZ POR PERSONA) ---
    with tab_perfil:
        st.markdown("##### Paso 1: Crear expediente del personal")
        with st.form("form_nuevo_docente"):
            c1, c2 = st.columns(2)
            nombre_m = c1.text_input("Nombre Completo*")
            telefono_m = c2.text_input("Teléfono de Contacto")
            email_m = c1.text_input("Correo Electrónico")
            turno_base = c2.selectbox("Turno Principal", ["Matutino", "Vespertino", "Tiempo Completo"])
            
            if st.form_submit_button("💾 Guardar Perfil Docente"):
                if nombre_m:
                    # Guardamos solo los datos personales
                    db.collection("maestros_perfil").add({
                        "nombre": nombre_m,
                        "contacto": {"tel": telefono_m, "email": email_m},
                        "turno_base": turno_base,
                        "activo": True
                    })
                    st.success(f"✅ Perfil de {nombre_m} creado. Ahora ve a la pestaña 'Asignar Materias'.")
                else:
                    st.error("El nombre es obligatorio")

    # --- TAB 2: ASIGNAR CLASES (AQUÍ ESTÁ LA MAGIA) ---
    with tab_carga:
        st.markdown("##### Paso 2: ¿Qué clases da cada maestro?")
        
        # 1. Buscamos los maestros registrados para llenar el selectbox
        docs_m = db.collection("maestros_perfil").stream()
        lista_profes = {d.to_dict()['nombre']: d.id for d in docs_m} # Diccionario Nombre -> ID
        
        if lista_profes:
            with st.form("form_carga"):
                col_a, col_b = st.columns(2)
                
                # Seleccionar al Humano
                nombre_seleccionado = col_a.selectbox("Seleccione Docente", list(lista_profes.keys()))
                
                # Seleccionar el Grado
                grado_destino = col_b.selectbox("Grado a impartir", LISTA_GRADOS)
                
                # Seleccionar Materias (Multiselect)
                materias_imparte = st.multiselect("Materias que imparte a ESTE grado específico:", LISTA_MATERIAS)
                
                # Nota extra (ej: "Solo los viernes")
                nota_extra = st.text_input("Nota adicional (Opcional)", placeholder="Ej: Solo refuerzo, Encargado de Aula, etc.")

                if st.form_submit_button("🔗 Vincular Carga Académica"):
                    if materias_imparte:
                        # Guardamos la ASIGNACIÓN en una colección separada pero vinculada
                        datos_asignacion = {
                            "id_docente": lista_profes[nombre_seleccionado],
                            "nombre_docente": nombre_seleccionado,
                            "grado": grado_destino,
                            "materias": materias_imparte,
                            "nota": nota_extra
                        }
                        db.collection("carga_academica").add(datos_asignacion)
                        st.success(f"✅ Asignado: {nombre_seleccionado} dará {len(materias_imparte)} materias a {grado_destino}.")
                    else:
                        st.error("Seleccione al menos una materia.")
        else:
            st.warning("Primero debe registrar docentes en la pestaña 1.")

    # --- TAB 3: VER RESUMEN ---
    with tab_ver:
        st.subheader("Planilla y Cargas")
        
        # Obtenemos las asignaciones
        docs_carga = db.collection("carga_academica").stream()
        data_carga = [d.to_dict() for d in docs_carga]
        
        if data_carga:
            df = pd.DataFrame(data_carga)
            # Ordenamos para que se vea bonito
            df = df.sort_values(by=["grado", "nombre_docente"])
            
            st.dataframe(
                df[['grado', 'nombre_docente', 'materias', 'nota']],
                column_config={
                    "grado": "Grado",
                    "nombre_docente": "Docente",
                    "materias": st.column_config.ListColumn("Materias Asignadas"),
                    "nota": "Observaciones"
                },
                use_container_width=True
            )
        else:
            st.info("No hay cargas académicas asignadas todavía.")

# ==========================================
# 4. CONSULTA ALUMNOS (CON BOLETA DE NOTAS)
# ==========================================
elif opcion == "Consulta Alumnos":
    st.title("🔎 Directorio de Estudiantes")
    
    tipo_busqueda = st.radio("Modo de Búsqueda:", ["Búsqueda por NIE", "Ver Listado por Grado"], horizontal=True)
    alumno_seleccionado = None

    if tipo_busqueda == "Búsqueda por NIE":
        nie_input = st.text_input("Ingrese NIE:", placeholder="Ej: 12345")
        if st.button("Buscar Expediente") and nie_input:
            doc = db.collection("alumnos").document(nie_input).get()
            if doc.exists: alumno_seleccionado = doc.to_dict()
            else: st.error("❌ No encontrado.")
    else:
        grados = ["Todos", "Kinder 4", "Kinder 5", "Kinder 6", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
        grado_filtro = st.selectbox("Seleccione Grado:", grados)
        
        if grado_filtro == "Todos": docs = db.collection("alumnos").stream()
        else: docs = db.collection("alumnos").where("grado_actual", "==", grado_filtro).stream()
        
        lista_alumnos = [d.to_dict() for d in docs]
        if lista_alumnos:
            opciones = {f"{a['nie']} - {a['nombre_completo']}": a for a in lista_alumnos}
            seleccion = st.selectbox("Seleccione alumno:", ["Seleccionar..."] + list(opciones.keys()))
            if seleccion != "Seleccionar...": alumno_seleccionado = opciones[seleccion]

    if alumno_seleccionado:
        st.markdown("---")
        col_foto, col_info = st.columns([1, 4])
        with col_foto:
            foto_url = alumno_seleccionado.get("documentos", {}).get("foto_url")
            st.image(foto_url if foto_url else "https://via.placeholder.com/150?text=Sin+Foto", width=100)
        
        with col_info:
            st.title(alumno_seleccionado['nombre_completo'])
            st.markdown(f"#### 🎓 {alumno_seleccionado.get('grado_actual', 'Sin Grado')} | 🕒 {alumno_seleccionado.get('turno', 'Sin Turno')}")
            est = alumno_seleccionado.get('estado', 'Activo')
            st.markdown(f"<span style='background-color:{'green' if est=='Activo' else 'red'}; color:white; padding:5px 10px; border-radius:5px;'>{est}</span>", unsafe_allow_html=True)

        tab_gral, tab_maestros, tab_fin, tab_acad = st.tabs(["📋 General", "👨‍🏫 Mis Maestros", "💰 Finanzas", "📊 Boleta de Notas"])
        
        with tab_gral:
            enc = alumno_seleccionado.get('encargado', {})
            st.write(f"**NIE:** {alumno_seleccionado.get('nie')}")
            st.write(f"**Responsable:** {enc.get('nombre', '-')}")
            st.write(f"**Teléfono:** {enc.get('telefono', '-')}")
            st.write(f"**Dirección:** {enc.get('direccion', '-')}")

        with tab_maestros:
            st.subheader(f"Docentes asignados")
            grado_alumno = alumno_seleccionado.get('grado_actual')
            if grado_alumno:
                docs_m = db.collection("maestros").stream()
                maestros_asignados = []
                for doc in docs_m:
                    m = doc.to_dict()
                    if grado_alumno in m.get('grados_asignados', []):
                        maestros_asignados.append(m)
                
                if maestros_asignados:
                    for profe in maestros_asignados:
                        with st.container(border=True):
                            c_a, c_b = st.columns([1, 3])
                            with c_a: st.write(f"**{profe['nombre']}**")
                            with c_b: st.caption(f"{profe['rol']} ({profe['turno']})"); st.write(f"📚 *{profe['materias']}*")
                else: st.warning("No hay docentes registrados para este grado.")

        with tab_fin:
            pagos = db.collection("finanzas").where("alumno_nie", "==", alumno_seleccionado['nie']).where("tipo", "==", "ingreso").stream()
            lista_p = [p.to_dict() for p in pagos]
            if lista_p:
                df_p = pd.DataFrame(lista_p).sort_values(by="fecha_legible", ascending=False)
                st.dataframe(df_p[['fecha_legible', 'descripcion', 'monto']], use_container_width=True)
            else: st.info("Sin pagos registrados.")

        # --- AQUÍ MOSTRAMOS LAS NOTAS ---
        with tab_acad:
            st.subheader("Historial Académico")
            # Buscar notas por NIE
            notas_ref = db.collection("notas").where("nie", "==", alumno_seleccionado['nie']).stream()
            lista_notas = [n.to_dict() for n in notas_ref]
            
            if lista_notas:
                df_notas = pd.DataFrame(lista_notas)
                # Ordenar columnas
                cols = ["materia", "p1", "p2", "p3", "promedio"]
                # Asegurar que existan las columnas para evitar error
                for c in cols: 
                    if c not in df_notas.columns: df_notas[c] = 0
                
                st.dataframe(
                    df_notas[cols],
                    column_config={
                        "materia": "Materia",
                        "p1": st.column_config.NumberColumn("Periodo 1", format="%.1f"),
                        "p2": st.column_config.NumberColumn("Periodo 2", format="%.1f"),
                        "p3": st.column_config.NumberColumn("Periodo 3", format="%.1f"),
                        "promedio": st.column_config.NumberColumn("Nota Final", format="%.1f")
                    },
                    use_container_width=True
                )
                
                prom_global = df_notas["promedio"].mean()
                if prom_global > 0:
                    st.metric("Promedio Global", f"{prom_global:.1f}")
            else:
                st.info("📭 Aún no se han cargado notas para este alumno.")

# ==========================================
# 5. FINANZAS (ROBUSTO)
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Finanzas del Colegio")
    if 'recibo_temp' not in st.session_state: st.session_state.recibo_temp = None
    if 'reporte_html' not in st.session_state: st.session_state.reporte_html = None

    if st.session_state.recibo_temp:
        r = st.session_state.recibo_temp
        es_ingreso = r['tipo'] == 'ingreso'
        color = "#2e7d32" if es_ingreso else "#c62828"
        titulo = "RECIBO DE INGRESO" if es_ingreso else "COMPROBANTE DE EGRESO"
        img = get_image_base64("logo.png"); img_h = f'<img src="{img}" style="height:70px;">' if img else ""
        
        st.markdown("""<style>@media print { @page { margin: 0; size: auto; } body * { visibility: hidden; } [data-testid="stSidebar"], header, footer { display: none !important; } .tc { visibility: visible !important; position: absolute; left: 0; top: 0; width: 100%; } } .tc { width: 100%; max-width: 850px; margin: auto; border: 1px solid #ddd; font-family: sans-serif; background: white; color: black !important; }</style>""", unsafe_allow_html=True)
        
        extra = f"""<tr style="border-bottom:1px solid #eee"><td style="padding:8px;font-weight:bold">Alumno:</td><td style="padding:8px">{r.get('nombre_persona')}</td><td style="padding:8px;font-weight:bold">Grado:</td><td style="padding:8px">{r.get('alumno_grado')}</td></tr>""" if r.get('alumno_nie') else f"""<tr style="border-bottom:1px solid #eee"><td style="padding:8px;font-weight:bold">Persona:</td><td style="padding:8px" colspan="3">{r.get('nombre_persona')}</td></tr>"""
        
        html = f"""<div class="tc"><div style="background:{color};padding:15px;color:white!important;display:flex;justify-content:space-between;"><div style="display:flex;gap:15px"><div style="background:white;padding:5px;border-radius:4px">{img_h}</div><div><h3 style="margin:0;color:white">COLEGIO PROFA. BLANCA ELENA</h3><p style="margin:0;font-size:12px;color:white">San Felipe</p></div></div><div style="text-align:right"><h4 style="margin:0;color:white">{titulo}</h4><p style="margin:0;font-size:14px;color:white">#{str(int(datetime.now().timestamp()))[-6:]}</p></div></div><div style="padding:20px"><table style="width:100%;border-collapse:collapse;font-size:14px;color:black">{extra}<tr style="border-bottom:1px solid #eee"><td style="padding:8px;font-weight:bold">Fecha:</td><td style="padding:8px">{r['fecha_legible']}</td><td style="padding:8px;font-weight:bold">Pago:</td><td style="padding:8px">{r.get('metodo')}</td></tr></table><br><table style="width:100%;border:1px solid #ddd;border-collapse:collapse;font-size:14px;color:black"><thead style="background:#f9f9f9"><tr><th style="padding:10px;border-bottom:2px solid {color}">Concepto</th><th style="padding:10px;text-align:right;border-bottom:2px solid {color}">Monto</th></tr></thead><tbody><tr><td style="padding:15px">{r['descripcion']}</td><td style="padding:15px;text-align:right;font-weight:bold;font-size:16px">${r['monto']:.2f}</td></tr></tbody></table><div style="margin-top:20px;text-align:right"><h1 style="color:{color}">${r['monto']:.2f}</h1></div><br><br><div style="display:flex;justify-content:space-between;gap:40px"><div style="flex:1;border-top:1px solid #aaa;text-align:center;font-size:12px">Firma Colegio</div><div style="flex:1;border-top:1px solid #aaa;text-align:center;font-size:12px">Firma Conforme</div></div></div><div style="border-top:2px dashed #ccc;margin-top:20px;text-align:center;color:#ccc;font-size:10px">✂️ Corte</div></div>"""
        st.markdown(html, unsafe_allow_html=True)
        if st.button("❌ Cerrar"): st.session_state.recibo_temp = None; st.rerun()

    elif st.session_state.reporte_html:
        st.markdown("""<style>@media print { @page { margin: 10mm; size: landscape; } body * { visibility: hidden; } [data-testid="stSidebar"], header, footer { display: none !important; } .rp { visibility: visible !important; position: absolute; left: 0; top: 0; width: 100%; background: white; color: black !important; } }</style>""", unsafe_allow_html=True)
        st.markdown(st.session_state.reporte_html, unsafe_allow_html=True)
        if st.button("⬅️ Volver"): st.session_state.reporte_html = None; st.rerun()

    else:
        t1, t2, t3 = st.tabs(["Ingresos", "Gastos", "Reporte"])
        with t1:
            c1, c2 = st.columns([1,2])
            with c1: 
                nb = st.text_input("Buscar NIE")
                if st.button("🔍"): 
                    d=db.collection("alumnos").document(nb).get()
                    if d.exists: st.session_state.ap = d.to_dict()
            if st.session_state.get("ap"):
                with c2:
                    st.info(f"Cobro a: {st.session_state.ap['nombre_completo']}")
                    with st.form("fi"):
                        con = st.selectbox("Concepto", ["Mensualidad", "Matrícula", "Uniforme", "Otros"])
                        mes = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril"])
                        m = st.number_input("Monto", min_value=0.01)
                        if st.form_submit_button("Cobrar"):
                            dat = {"tipo":"ingreso", "descripcion":f"{con}-{mes}", "monto":m, "nombre_persona":st.session_state.ap['nombre_completo'], "alumno_nie":st.session_state.ap['nie'], "alumno_grado":st.session_state.ap['grado_actual'], "fecha":firestore.SERVER_TIMESTAMP, "fecha_legible":datetime.now().strftime("%d/%m %H:%M")}
                            db.collection("finanzas").add(dat); st.session_state.recibo_temp = dat; st.rerun()
        with t2:
            with st.form("fg"):
                prov = st.text_input("Proveedor"); m = st.number_input("Monto", min_value=0.01); desc = st.text_input("Detalle")
                if st.form_submit_button("Registrar"):
                    dat = {"tipo":"egreso", "descripcion":desc, "monto":m, "nombre_persona":prov, "fecha":firestore.SERVER_TIMESTAMP, "fecha_legible":datetime.now().strftime("%d/%m %H:%M")}
                    db.collection("finanzas").add(dat); st.session_state.recibo_temp = dat; st.rerun()
        with t3:
            if st.button("Generar PDF"):
                # Simplificado para mantener código corto, se asume lógica de reporte PDF aquí
                st.session_state.reporte_html = "<div class='rp'><h1>Reporte PDF</h1><p>Visualización disponible en versión completa.</p></div>"
                st.rerun()

# ==========================================
# 6. NOTAS (NUEVO: CARGA MASIVA)
# ==========================================
elif opcion == "Notas":
    st.title("📊 Gestión de Calificaciones")
    
    st.info("ℹ️ Para registrar notas, descargue la plantilla, llénela en Excel y súbala aquí.")
    
    # 1. GENERAR PLANTILLA
    if st.button("📥 Descargar Plantilla Excel (CSV)"):
        df_template = pd.DataFrame(columns=["NIE", "Materia", "Periodo 1", "Periodo 2", "Periodo 3"])
        # Agregamos una fila de ejemplo
        df_template.loc[0] = ["1234567", "Matemáticas", 8.5, 9.0, 0.0]
        csv = df_template.to_csv(index=False).encode('utf-8')
        st.download_button("Guardar Plantilla", csv, "plantilla_notas.csv", "text/csv")
    
    st.markdown("---")
    
    # 2. SUBIR NOTAS
    archivo_notas = st.file_uploader("📂 Subir archivo de notas (CSV)", type=["csv"])
    
    if archivo_notas:
        try:
            df_upload = pd.read_csv(archivo_notas)
            st.write("Vista previa de notas a cargar:")
            
            # Cálculo automático de promedio
            # Convertimos a numérico por si acaso
            cols_p = ["Periodo 1", "Periodo 2", "Periodo 3"]
            for c in cols_p: df_upload[c] = pd.to_numeric(df_upload[c], errors='coerce').fillna(0)
            
            # Promedio simple (puedes ajustar la fórmula)
            df_upload["Promedio Final"] = df_upload[cols_p].mean(axis=1).round(1)
            
            st.dataframe(df_upload, use_container_width=True)
            
            if st.button("💾 Guardar Notas en Sistema", type="primary"):
                progress_text = "Guardando notas..."
                my_bar = st.progress(0, text=progress_text)
                total = len(df_upload)
                
                # Guardar en Firebase
                batch = db.batch()
                count = 0
                
                for index, row in df_upload.iterrows():
                    # Crear ID único para no duplicar (NIE_MATERIA)
                    doc_id = f"{row['NIE']}_{row['Materia'].replace(' ', '')}"
                    doc_ref = db.collection("notas").document(doc_id)
                    
                    datos_nota = {
                        "nie": str(row['NIE']),
                        "materia": row['Materia'],
                        "p1": row['Periodo 1'],
                        "p2": row['Periodo 2'],
                        "p3": row['Periodo 3'],
                        "promedio": row['Promedio Final'],
                        "fecha_act": firestore.SERVER_TIMESTAMP
                    }
                    batch.set(doc_ref, datos_nota)
                    count += 1
                    my_bar.progress(int((count / total) * 100), text=f"Procesando {count}/{total}")
                
                batch.commit()
                my_bar.empty()
                st.success(f"✅ Se han procesado {total} registros de notas correctamente.")
                
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

# ==========================================
# 7. CONFIGURACIÓN
# ==========================================
elif opcion == "Configuración":
    st.header("⚙️ Configuración")