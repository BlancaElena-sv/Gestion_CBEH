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
# 3. GESTIÓN DE MAESTROS (CORREGIDO ERROR KEYERROR)
# ==========================================
elif opcion == "Gestión Maestros":
    st.title("👩‍🏫 Plantilla Docente")
    
    tab_perfil, tab_carga, tab_ver = st.tabs(["1️⃣ Registrar Docente", "2️⃣ Asignar Carga", "📋 Ver Planilla"])
    
    LISTA_GRADOS = ["Kinder 4", "Kinder 5", "Kinder 6", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
    LISTA_MATERIAS = ["Matemáticas", "Lenguaje y Literatura", "Ciencias Salud y M.A.", "Estudios Sociales", "Inglés", "Educación Artística", "Educación Física", "Moral y Cívica", "Informática", "Ortografía", "Caligrafía"]

    # --- TAB 1: REGISTRO CON CÓDIGO ---
    with tab_perfil:
        st.markdown("##### Paso 1: Crear expediente del personal")
        with st.form("form_nuevo_docente"):
            c1, c2 = st.columns(2)
            codigo_emp = c1.text_input("Código de Empleado*", placeholder="Ej: DOC-001")
            nombre_m = c2.text_input("Nombre Completo*")
            telefono_m = c1.text_input("Teléfono de Contacto")
            email_m = c2.text_input("Correo Electrónico")
            turno_base = c1.selectbox("Turno Principal", ["Matutino", "Vespertino", "Tiempo Completo"])
            
            if st.form_submit_button("💾 Guardar Perfil Docente"):
                if nombre_m and codigo_emp:
                    db.collection("maestros_perfil").add({
                        "codigo": codigo_emp,
                        "nombre": nombre_m,
                        "contacto": {"tel": telefono_m, "email": email_m},
                        "turno_base": turno_base,
                        "activo": True
                    })
                    st.success(f"✅ Perfil de {nombre_m} ({codigo_emp}) creado correctamente.")
                else:
                    st.error("El Código y el Nombre son obligatorios")

    # --- TAB 2: ASIGNACIÓN ---
    with tab_carga:
        st.markdown("##### Paso 2: Asignación de Materias y Grados")
        docs_m = db.collection("maestros_perfil").stream()
        # Creamos diccionario seguro usando .get para evitar error si falta código
        lista_profes = {f"{d.to_dict().get('codigo', 'S/C')} - {d.to_dict()['nombre']}": d.id for d in docs_m}
        
        if lista_profes:
            with st.form("form_carga"):
                col_a, col_b = st.columns(2)
                nombre_seleccionado = col_a.selectbox("Seleccione Docente", list(lista_profes.keys()))
                grado_destino = col_b.selectbox("Grado a impartir", LISTA_GRADOS)
                materias_imparte = st.multiselect("Materias para ESTE grado:", LISTA_MATERIAS)
                nota_extra = st.text_input("Nota adicional (Opcional)", placeholder="Ej: Encargado de Aula")

                if st.form_submit_button("🔗 Vincular Carga"):
                    if materias_imparte:
                        nombre_limpio = nombre_seleccionado.split(" - ")[1] if " - " in nombre_seleccionado else nombre_seleccionado
                        datos_asignacion = {
                            "id_docente": lista_profes[nombre_seleccionado],
                            "nombre_docente": nombre_limpio,
                            "grado": grado_destino,
                            "materias": materias_imparte,
                            "nota": nota_extra
                        }
                        db.collection("carga_academica").add(datos_asignacion)
                        st.success(f"✅ Carga asignada a {nombre_limpio} para {grado_destino}.")
                    else: st.error("Seleccione materias.")
        else: st.warning("Primero registre docentes en la pestaña 1.")

    # --- TAB 3: VISUALIZACIÓN (CORREGIDA) ---
    with tab_ver:
        st.subheader("Directorio Docente")
        docs_p = db.collection("maestros_perfil").stream()
        lista_p = [d.to_dict() for d in docs_p]
        
        if lista_p:
            df_p = pd.DataFrame(lista_p)
            
            # --- BLINDAJE CONTRA KEYERROR ---
            # Si no existe la columna 'codigo' (por datos viejos), la creamos
            if 'codigo' not in df_p.columns:
                df_p['codigo'] = "Sin Código"
            
            # Rellenamos vacíos por si acaso
            df_p['codigo'] = df_p['codigo'].fillna("Sin Código")
            df_p['turno_base'] = df_p.get('turno_base', 'No definido') # Uso seguro de get

            st.dataframe(df_p[['codigo', 'nombre', 'turno_base']], use_container_width=True)
        else: st.info("Sin registros.")

# ==========================================
# 4. CONSULTA ALUMNOS
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

        tab_gral, tab_maestros, tab_fin, tab_acad = st.tabs(["📋 General", "👨‍🏫 Mis Maestros", "💰 Finanzas", "📊 Notas"])
        
        with tab_gral:
            enc = alumno_seleccionado.get('encargado', {})
            st.write(f"**NIE:** {alumno_seleccionado.get('nie')}")
            st.write(f"**Responsable:** {enc.get('nombre', '-')}")
            st.write(f"**Teléfono:** {enc.get('telefono', '-')}")
            st.write(f"**Dirección:** {enc.get('direccion', '-')}")

        with tab_maestros:
            st.subheader(f"Carga Académica: {alumno_seleccionado.get('grado_actual')}")
            grado_alumno = alumno_seleccionado.get('grado_actual')
            if grado_alumno:
                cargas = db.collection("carga_academica").where("grado", "==", grado_alumno).stream()
                lista_cargas = [c.to_dict() for c in cargas]
                if lista_cargas:
                    for carga in lista_cargas:
                        with st.container(border=True):
                            c1, c2 = st.columns([1, 3])
                            with c1: 
                                st.write(f"**{carga['nombre_docente']}**")
                                if carga.get('nota'): st.caption(carga['nota'])
                            with c2: 
                                st.write("**Imparte:**")
                                for m in carga['materias']: st.markdown(f"- {m}")
                else: st.warning(f"No hay carga académica asignada para {grado_alumno}.")
            else: st.error("El alumno no tiene grado asignado.")

        with tab_fin:
            pagos = db.collection("finanzas").where("alumno_nie", "==", alumno_seleccionado['nie']).where("tipo", "==", "ingreso").stream()
            lista_p = [p.to_dict() for p in pagos]
            if lista_p:
                df_p = pd.DataFrame(lista_p).sort_values(by="fecha_legible", ascending=False)
                st.dataframe(df_p[['fecha_legible', 'descripcion', 'monto']], use_container_width=True)
            else: st.info("Sin pagos registrados.")

        with tab_acad:
            notas_ref = db.collection("notas").where("nie", "==", alumno_seleccionado['nie']).stream()
            lista_notas = [n.to_dict() for n in notas_ref]
            if lista_notas:
                df_notas = pd.DataFrame(lista_notas)
                cols = ["materia", "p1", "p2", "p3", "promedio"]
                for c in cols: 
                    if c not in df_notas.columns: df_notas[c] = 0
                st.dataframe(df_notas[cols], use_container_width=True)
                prom = df_notas["promedio"].mean()
                if prom > 0: st.metric("Promedio Global", f"{prom:.1f}")
            else: st.info("Sin notas registradas.")

# ==========================================
# 5. FINANZAS
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
        
        linea_extra = ""
        if r.get('alumno_nie'):
            linea_extra = f"""<tr style="border-bottom:1px solid #eee"><td style="padding:8px;font-weight:bold">Alumno:</td><td style="padding:8px">{r.get('nombre_persona')}</td><td style="padding:8px;font-weight:bold">Grado:</td><td style="padding:8px">{r.get('alumno_grado')}</td></tr>"""
        elif r.get('codigo_maestro'):
            linea_extra = f"""<tr style="border-bottom:1px solid #eee"><td style="padding:8px;font-weight:bold">Docente:</td><td style="padding:8px">{r.get('nombre_persona')}</td><td style="padding:8px;font-weight:bold">Código:</td><td style="padding:8px">{r.get('codigo_maestro')}</td></tr>"""
        else:
            linea_extra = f"""<tr style="border-bottom:1px solid #eee"><td style="padding:8px;font-weight:bold">Beneficiario:</td><td style="padding:8px" colspan="3">{r.get('nombre_persona')}</td></tr>"""

        html = f"""<div class="tc"><div style="background:{color};padding:15px;color:white!important;display:flex;justify-content:space-between;"><div style="display:flex;gap:15px"><div style="background:white;padding:5px;border-radius:4px">{img_h}</div><div><h3 style="margin:0;color:white">COLEGIO PROFA. BLANCA ELENA</h3><p style="margin:0;font-size:12px;color:white">San Felipe</p></div></div><div style="text-align:right"><h4 style="margin:0;color:white">{titulo}</h4><p style="margin:0;font-size:14px;color:white">#{str(int(datetime.now().timestamp()))[-6:]}</p></div></div><div style="padding:20px"><table style="width:100%;border-collapse:collapse;font-size:14px;color:black">{linea_extra}<tr style="border-bottom:1px solid #eee"><td style="padding:8px;font-weight:bold">Fecha:</td><td style="padding:8px">{r['fecha_legible']}</td><td style="padding:8px;font-weight:bold">Pago:</td><td style="padding:8px">{r.get('metodo')}</td></tr></table><br><table style="width:100%;border:1px solid #ddd;border-collapse:collapse;font-size:14px;color:black"><thead style="background:#f9f9f9"><tr><th style="padding:10px;border-bottom:2px solid {color}">Concepto</th><th style="padding:10px;text-align:right;border-bottom:2px solid {color}">Monto</th></tr></thead><tbody><tr><td style="padding:15px">{r['descripcion']}</td><td style="padding:15px;text-align:right;font-weight:bold;font-size:16px">${r['monto']:.2f}</td></tr></tbody></table><div style="margin-top:20px;text-align:right"><h1 style="color:{color}">${r['monto']:.2f}</h1></div><br><br><div style="display:flex;justify-content:space-between;gap:40px"><div style="flex:1;border-top:1px solid #aaa;text-align:center;font-size:12px">Firma Colegio</div><div style="flex:1;border-top:1px solid #aaa;text-align:center;font-size:12px">Firma Conforme</div></div></div><div style="border-top:2px dashed #ccc;margin-top:20px;text-align:center;color:#ccc;font-size:10px">✂️ Corte</div></div>"""
        st.markdown(html, unsafe_allow_html=True)
        if st.button("❌ Cerrar"): st.session_state.recibo_temp = None; st.rerun()

    elif st.session_state.reporte_html:
        st.markdown("""<style>@media print { @page { margin: 10mm; size: landscape; } body * { visibility: hidden; } [data-testid="stSidebar"], header, footer { display: none !important; } .rp { visibility: visible !important; position: absolute; left: 0; top: 0; width: 100%; background: white; color: black !important; } }</style>""", unsafe_allow_html=True)
        st.markdown(st.session_state.reporte_html, unsafe_allow_html=True)
        if st.button("⬅️ Volver"): st.session_state.reporte_html = None; st.rerun()

    else:
        tab1, tab2, tab3 = st.tabs(["Ingresos", "Gastos", "Reporte"])
        with tab1:
            col_b, col_f = st.columns([1, 2])
            with col_b:
                nie_bus = st.text_input("Buscar NIE Alumno:")
                if st.button("🔍 Buscar"):
                    d = db.collection("alumnos").document(nie_bus).get()
                    if d.exists: st.session_state.alumno_pago = d.to_dict()
                    else: st.error("No existe"); st.session_state.alumno_pago = None
            if st.session_state.get("alumno_pago"):
                alum = st.session_state.alumno_pago
                with col_f:
                    st.info(f"Cobrando a: **{alum['nombre_completo']}**")
                    with st.form("f_ingreso"):
                        conc = st.selectbox("Concepto", ["Mensualidad", "Matrícula", "Uniforme", "Otros"])
                        mes = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"])
                        monto = st.number_input("Monto $", min_value=0.01)
                        met = st.radio("Pago", ["Efectivo", "Banco"], horizontal=True)
                        obs = st.text_area("Notas")
                        if st.form_submit_button("✅ Cobrar"):
                            data = {
                                "tipo": "ingreso", "descripcion": f"{conc} - {mes}", "monto": monto,
                                "nombre_persona": alum['nombre_completo'], "alumno_nie": alum.get('nie', ''),
                                "alumno_grado": alum.get('grado_actual', ''), "metodo": met, "observaciones": obs,
                                "fecha": firestore.SERVER_TIMESTAMP, "fecha_dt": datetime.now(),
                                "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
                            }
                            db.collection("finanzas").add(data)
                            st.session_state.recibo_temp = data
                            st.session_state.alumno_pago = None
                            st.rerun()
        with tab2:
            st.subheader("Registrar Salida de Dinero")
            with st.form("f_gasto"):
                c1, c2 = st.columns(2)
                cat = c1.selectbox("Categoría", ["Pago de Planilla (Maestros)", "Servicios", "Mantenimiento", "Materiales", "Otros"])
                
                # SELECCIÓN DINÁMICA DE MAESTRO
                maestro_obj = None
                prov_txt = ""
                if cat == "Pago de Planilla (Maestros)":
                    docs_m = db.collection("maestros_perfil").stream()
                    # Safe dict creation
                    lista_m = {f"{d.to_dict().get('nombre')} ({d.to_dict().get('codigo','S/C')})": d.to_dict() for d in docs_m}
                    if lista_m:
                        mk = c1.selectbox("Seleccione Docente", list(lista_m.keys()))
                        maestro_obj = lista_m[mk]
                    else: c1.warning("Sin maestros.")
                else:
                    prov_txt = c1.text_input("Pagar a:")

                monto = c2.number_input("Monto $", min_value=0.01)
                obs = st.text_area("Detalle")
                
                if st.form_submit_button("🔴 Registrar"):
                    if cat == "Pago de Planilla (Maestros)" and maestro_obj:
                        nom = maestro_obj['nombre']
                        cod = maestro_obj.get('codigo', '')
                    else:
                        nom = prov_txt
                        cod = ""

                    data = {
                        "tipo": "egreso", "descripcion": cat, "monto": monto,
                        "nombre_persona": nom, "codigo_maestro": cod,
                        "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_dt": datetime.now(),
                        "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    db.collection("finanzas").add(data)
                    st.session_state.recibo_temp = data
                    st.rerun()
        with tab3:
            st.subheader("Generación de Reportes PDF")
            col_fil1, col_fil2, col_fil3 = st.columns(3)
            fecha_ini = col_fil1.date_input("Desde", value=date(datetime.now().year, 1, 1))
            fecha_fin = col_fil2.date_input("Hasta", value=datetime.now())
            tipo_filtro = col_fil3.selectbox("Filtrar por", ["Todos los Movimientos", "Solo Ingresos", "Solo Egresos"])
            if st.button("📄 Generar Vista de Impresión (PDF)"):
                docs = db.collection("finanzas").order_by("fecha", direction=firestore.Query.DESCENDING).stream()
                lista_final = []
                for doc in docs:
                    d = doc.to_dict()
                    raw_date = d.get("fecha_dt") or d.get("fecha")
                    f_obj = None
                    if raw_date:
                        if hasattr(raw_date, "date"): f_obj = raw_date.date()
                        elif isinstance(raw_date, datetime): f_obj = raw_date.date()
                    if f_obj and (fecha_ini <= f_obj <= fecha_fin):
                        if tipo_filtro == "Solo Ingresos" and d.get("tipo") != "ingreso": continue
                        if tipo_filtro == "Solo Egresos" and d.get("tipo") != "egreso": continue
                        item = {"fecha": d.get("fecha_legible", "-"), "tipo": d.get("tipo", "Desconocido"), "persona": d.get("nombre_persona") or d.get("alumno_nombre") or d.get("proveedor") or "N/A", "nie": d.get("alumno_nie", "-"), "concepto": d.get("descripcion", "-"), "monto": d.get("monto", 0.0)}
                        lista_final.append(item)
                if not lista_final:
                    st.warning("No hay datos para generar el reporte con esos filtros.")
                else:
                    df = pd.DataFrame(lista_final)
                    t_ing = df[df['tipo']=='ingreso']['monto'].sum()
                    t_egr = df[df['tipo']=='egreso']['monto'].sum()
                    balance = t_ing - t_egr
                    logo_img = get_image_base64("logo.png")
                    logo_html = f'<img src="{logo_img}" style="height:60px;">' if logo_img else ""
                    filas_html = ""
                    for index, row in df.iterrows():
                        color_tipo = "green" if row['tipo'] == 'ingreso' else "red"
                        filas_html += f"""<tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px; color:#000;">{row['fecha']}</td><td style="padding: 8px; color: {color_tipo}; font-weight: bold;">{row['tipo'].upper()}</td><td style="padding: 8px; color:#000;">{row['persona']}</td><td style="padding: 8px; color:#000;">{row['concepto']}</td><td style="padding: 8px; text-align: right; color:#000;">${row['monto']:.2f}</td></tr>"""
                    html_reporte = f"""<div class="report-print" style="font-family: Arial, sans-serif; padding: 20px; color: black !important;"><div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #333; padding-bottom: 10px;"><div style="display: flex; align-items: center; gap: 15px;">{logo_html}<div><h2 style="margin: 0; color:black;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2><p style="margin: 0; color: gray;">Reporte Financiero Detallado</p></div></div><div style="text-align: right;"><p style="margin: 0; color:black;"><strong>Desde:</strong> {fecha_ini.strftime('%d/%m/%Y')}</p><p style="margin: 0; color:black;"><strong>Hasta:</strong> {fecha_fin.strftime('%d/%m/%Y')}</p></div></div><div style="display: flex; gap: 20px; margin: 20px 0;"><div style="flex: 1; background: #e8f5e9; padding: 15px; border-radius: 5px; text-align: center;"><h4 style="margin:0; color: #2e7d32;">INGRESOS</h4><h2 style="margin:5px 0; color: #2e7d32;">${t_ing:,.2f}</h2></div><div style="flex: 1; background: #ffebee; padding: 15px; border-radius: 5px; text-align: center;"><h4 style="margin:0; color: #c62828;">EGRESOS</h4><h2 style="margin:5px 0; color: #c62828;">${t_egr:,.2f}</h2></div><div style="flex: 1; background: #e3f2fd; padding: 15px; border-radius: 5px; text-align: center;"><h4 style="margin:0; color: #1565c0;">BALANCE</h4><h2 style="margin:5px 0; color: #1565c0;">${balance:,.2f}</h2></div></div><table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px;"><thead style="background-color: #f5f5f5;"><tr><th style="padding: 10px; text-align: left; color:black;">Fecha</th><th style="padding: 10px; text-align: left; color:black;">Tipo</th><th style="padding: 10px; text-align: left; color:black;">Responsable / Proveedor</th><th style="padding: 10px; text-align: left; color:black;">Concepto</th><th style="padding: 10px; text-align: right; color:black;">Monto</th></tr></thead><tbody>{filas_html}</tbody></table><br><p style="text-align: center; color: gray; font-size: 12px; margin-top: 30px;">Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p></div>"""
                    st.session_state.reporte_html = html_reporte
                    st.rerun()

# ==========================================
# 6. NOTAS
# ==========================================
elif opcion == "Notas":
    st.title("📊 Notas")
    if st.button("📥 Descargar Plantilla Excel (CSV)"):
        df_template = pd.DataFrame(columns=["NIE", "Materia", "Periodo 1", "Periodo 2", "Periodo 3"])
        df_template.loc[0] = ["1234567", "Matemáticas", 8.5, 9.0, 0.0]
        csv = df_template.to_csv(index=False).encode('utf-8')
        st.download_button("Guardar Plantilla", csv, "plantilla_notas.csv", "text/csv")
    st.markdown("---")
    archivo_notas = st.file_uploader("📂 Subir archivo de notas (CSV)", type=["csv"])
    if archivo_notas:
        try:
            df_upload = pd.read_csv(archivo_notas)
            st.write("Vista previa:")
            cols_p = ["Periodo 1", "Periodo 2", "Periodo 3"]
            for c in cols_p: df_upload[c] = pd.to_numeric(df_upload[c], errors='coerce').fillna(0)
            df_upload["Promedio Final"] = df_upload[cols_p].mean(axis=1).round(1)
            st.dataframe(df_upload, use_container_width=True)
            if st.button("💾 Guardar Notas", type="primary"):
                batch = db.batch()
                for i, row in df_upload.iterrows():
                    doc_id = f"{row['NIE']}_{row['Materia'].replace(' ', '')}"
                    batch.set(db.collection("notas").document(doc_id), {
                        "nie": str(row['NIE']), "materia": row['Materia'],
                        "p1": row['Periodo 1'], "p2": row['Periodo 2'], "p3": row['Periodo 3'],
                        "promedio": row['Promedio Final'], "fecha_act": firestore.SERVER_TIMESTAMP
                    })
                batch.commit()
                st.success("✅ Notas guardadas.")
        except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 7. CONFIGURACIÓN
# ==========================================
elif opcion == "Configuración":
    st.header("⚙️ Configuración")