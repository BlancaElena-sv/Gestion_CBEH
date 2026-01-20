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

# --- CONSTANTES Y MAPA CURRICULAR (AGREGADO) ---
MATERIAS_ESTANDAR = [
    "Lenguaje", "Matemática", "Ciencia y Tecnología", "Estudios Sociales", 
    "Inglés", "Moral, Urbanidad y Cívica", "Educación Física", "Educación Artística", 
    "Informática", "Ortografía", "Caligrafía", "Conducta"
]

MAPA_MATERIAS = {
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

LISTA_GRADOS_TODO = list(MAPA_MATERIAS.keys())
LISTA_GRADOS_NOTAS = [g for g in LISTA_GRADOS_TODO if "Kinder" not in g and "Prepa" not in g]
LISTA_MESES = ["Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"]

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

def redondear_mined(valor):
    if valor is None: return 0.0
    parte_entera = int(valor)
    parte_decimal = valor - parte_entera
    if parte_decimal >= 0.5: return float(parte_entera + 1)
    else: return float(parte_entera)

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
        
        enviado = st.form_submit_button("💾 Guardar Inscripción", type="primary")

        if enviado:
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
                        "documentos": {
                            "foto_url": subir_archivo(foto, ruta),
                            "doc_urls": lista_urls_docs
                        },
                        "fecha_registro": firestore.SERVER_TIMESTAMP
                    }
                    db.collection("alumnos").document(nie).set(datos)
                    st.success(f"✅ ¡Alumno inscrito con {len(lista_urls_docs)} documentos!")

# ==========================================
# 3. GESTIÓN DE MAESTROS
# ==========================================
elif opcion == "Gestión Maestros":
    st.title("👩‍🏫 Plantilla Docente")
    
    tab_perfil, tab_carga, tab_admin_cargas, tab_admin_profes, tab_ver = st.tabs([
        "1️⃣ Registrar Docente", 
        "2️⃣ Asignar Carga", 
        "3️⃣ Administrar Cargas", 
        "✏️ Admin. Docentes", 
        "📋 Ver Planilla"
    ])
    
    # --- TAB 1: REGISTRO ---
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
                        "codigo": codigo_emp, "nombre": nombre_m,
                        "contacto": {"tel": telefono_m, "email": email_m},
                        "turno_base": turno_base, "activo": True
                    })
                    st.success(f"✅ Perfil de {nombre_m} ({codigo_emp}) creado correctamente.")
                else: st.error("El Código y el Nombre son obligatorios")

    # --- TAB 2: ASIGNACIÓN ---
    with tab_carga:
        st.markdown("##### Paso 2: Asignación de Materias y Grados")
        docs_m = db.collection("maestros_perfil").stream()
        lista_profes = {f"{d.to_dict().get('codigo', 'S/C')} - {d.to_dict()['nombre']}": d.id for d in docs_m}
        
        if lista_profes:
            with st.form("form_carga"):
                c1, c2 = st.columns(2)
                nombre_seleccionado = col_a.selectbox("Seleccione Docente", list(lista_profes.keys()))
                grado_destino = col_b.selectbox("Grado a impartir", LISTA_GRADOS_TODO)
                
                # Cargamos todas para dar libertad, aunque el sistema luego filtra en notas
                materias_imparte = st.multiselect("Materias para ESTE grado:", MATERIAS_ESTANDAR)
                
                nota_extra = st.text_input("Nota adicional (Opcional)", placeholder="Ej: Encargado de Aula")
                es_guia = st.checkbox("¿Es el Maestro Guía de este grado?") # CHECKBOX IMPORTANTE

                if st.form_submit_button("🔗 Vincular Carga"):
                    if materias_imparte:
                        nombre_limpio = nombre_seleccionado.split(" - ")[1] if " - " in nombre_seleccionado else nombre_seleccionado
                        datos_asignacion = {
                            "id_docente": lista_profes[nombre_seleccionado],
                            "nombre_docente": nombre_limpio,
                            "grado": grado_destino, "materias": materias_imparte, "nota": nota_extra,
                            "es_guia": es_guia
                        }
                        db.collection("carga_academica").add(datos_asignacion)
                        st.success(f"✅ Carga asignada a {nombre_limpio} para {grado_destino}.")
                    else: st.error("Seleccione materias.")
        else: st.warning("Primero registre docentes en la pestaña 1.")

    # --- TAB 3: ADMINISTRAR CARGAS ---
    with tab_admin_cargas:
        st.subheader("🛠️ Gestión de Cargas Académicas")
        docs_c = db.collection("carga_academica").stream()
        cargas_list = []
        for d in docs_c:
            c = d.to_dict()
            c['id'] = d.id
            cargas_list.append(c)
            
        if cargas_list:
            df_c = pd.DataFrame(cargas_list)
            if 'es_guia' not in df_c.columns: df_c['es_guia'] = False

            st.markdown("Filtrar visualización:")
            col_f1, col_f2 = st.columns(2)
            docentes_unicos = ["Todos"] + sorted(df_c['nombre_docente'].unique().tolist())
            filtro_docente = col_f1.selectbox("Filtrar por Maestro:", docentes_unicos)
            grados_unicos = ["Todos"] + sorted(df_c['grado'].unique().tolist())
            filtro_grado = col_f2.selectbox("Filtrar por Grado:", grados_unicos)
            
            df_filtered = df_c.copy()
            if filtro_docente != "Todos": df_filtered = df_filtered[df_filtered['nombre_docente'] == filtro_docente]
            if filtro_grado != "Todos": df_filtered = df_filtered[df_filtered['grado'] == filtro_grado]
                
            st.info(f"Mostrando {len(df_filtered)} registros.")
            st.dataframe(df_filtered[['nombre_docente', 'grado', 'materias', 'es_guia']], use_container_width=True)
            st.markdown("---")
            st.write("#### Modificar Carga")
            
            if not df_filtered.empty:
                opciones_c = {f"{row['nombre_docente']} - {row['grado']} ({len(row['materias'])} mats)": row['id'] for index, row in df_filtered.iterrows()}
                seleccion_c_id = st.selectbox("Seleccione carga:", ["Seleccionar..."] + list(opciones_c.keys()))
                
                if seleccion_c_id != "Seleccionar...":
                    id_carga_real = opciones_c[seleccion_c_id]
                    carga_obj = next((item for item in cargas_list if item["id"] == id_carga_real), None)
                    if carga_obj:
                        accion_c = st.radio("Acción:", ["✏️ Editar", "🗑️ Eliminar"], horizontal=True)
                        if accion_c == "✏️ Editar":
                            with st.form("form_edit_carga"):
                                st.info(f"Editando a: {carga_obj['nombre_docente']}")
                                idx_grado = LISTA_GRADOS_TODO.index(carga_obj['grado']) if carga_obj['grado'] in LISTA_GRADOS_TODO else 0
                                nuevo_grado = st.selectbox("Grado", LISTA_GRADOS_TODO, index=idx_grado)
                                default_mats = [m for m in carga_obj['materias'] if m in MATERIAS_ESTANDAR]
                                nuevas_mats = st.multiselect("Materias", MATERIAS_ESTANDAR, default=default_mats)
                                es_guia_edit = st.checkbox("¿Es Maestro Guía?", value=carga_obj.get('es_guia', False))
                                
                                if st.form_submit_button("✅ Guardar Cambios"):
                                    db.collection("carga_academica").document(id_carga_real).update({
                                        "grado": nuevo_grado, "materias": nuevas_mats, "es_guia": es_guia_edit
                                    })
                                    st.success("Actualizado."); time.sleep(1.5); st.rerun()
                        elif accion_c == "🗑️ Eliminar":
                            if st.button("🔴 Confirmar Eliminación"):
                                db.collection("carga_academica").document(id_carga_real).delete()
                                st.success("Eliminado."); time.sleep(1.5); st.rerun()

    # --- TAB 4: ADMIN DOCENTES ---
    with tab_admin_profes:
        st.subheader("🛠️ Mantenimiento de Docentes")
        docs_admin = db.collection("maestros_perfil").stream()
        profes_admin = [{"id": d.id, **d.to_dict()} for d in docs_admin]
        if profes_admin:
            opcs = {f"{p.get('codigo')} - {p['nombre']}": p for p in profes_admin}
            sel = st.selectbox("Editar Docente:", ["Seleccionar..."] + list(opcs.keys()))
            if sel != "Seleccionar...":
                p = opcs[sel]
                with st.form("ed_prof"):
                    nn = st.text_input("Nombre", p['nombre'])
                    nt = st.text_input("Tel", p.get('contacto',{}).get('tel',''))
                    if st.form_submit_button("Actualizar"):
                        db.collection("maestros_perfil").document(p['id']).update({"nombre": nn, "contacto.tel": nt})
                        st.success("Listo"); time.sleep(1); st.rerun()

    # --- TAB 5: VER PLANILLA ---
    with tab_ver:
        st.subheader("Directorio Docente")
        docs_p = db.collection("maestros_perfil").stream()
        lista_p = [d.to_dict() for d in docs_p]
        if lista_p:
            df_p = pd.DataFrame(lista_p)
            if 'codigo' not in df_p.columns: df_p['codigo'] = "Sin Código"
            st.dataframe(df_p[['codigo', 'nombre', 'turno_base']], use_container_width=True)

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
        grado_filtro = st.selectbox("Seleccione Grado:", ["Todos"] + LISTA_GRADOS_TODO)
        if grado_filtro == "Todos": docs = db.collection("alumnos").stream()
        else: docs = db.collection("alumnos").where("grado_actual", "==", grado_filtro).stream()
        lista_alumnos = [d.to_dict() for d in docs]
        if lista_alumnos:
            opciones = {f"{a['nie']} - {a['nombre_completo']}": a for a in lista_alumnos}
            seleccion = st.selectbox("Seleccione alumno:", ["Seleccionar..."] + list(opciones.keys()))
            if seleccion != "Seleccionar...": alumno_seleccionado = opciones[seleccion]

    if alumno_seleccionado:
        st.markdown("---")
        c1, c2 = st.columns([1, 4])
        with c1: st.image(alumno_seleccionado.get('documentos',{}).get('foto_url', "https://via.placeholder.com/150"), width=120)
        with c2: 
            st.title(alumno_seleccionado['nombre_completo'])
            st.markdown(f"#### 🎓 {alumno_seleccionado.get('grado_actual', 'Sin Grado')} | 🕒 {alumno_seleccionado.get('turno', 'Sin Turno')}")
            st.info(f"Responsable: {alumno_seleccionado.get('encargado',{}).get('nombre')}")

        tab_gral, tab_maestros, tab_fin, tab_notas = st.tabs(["📋 General", "👨‍🏫 Maestros", "💰 Finanzas", "🖨️ Boleta de Notas"])
        
        with tab_gral:
            enc = alumno_seleccionado.get('encargado', {})
            st.write(f"**Teléfono:** {enc.get('telefono', '-')}")
            st.write(f"**Dirección:** {enc.get('direccion', '-')}")
            docs = alumno_seleccionado.get('documentos',{}).get('doc_urls', [])
            if docs:
                for i, u in enumerate(docs): st.link_button(f"📄 Documento {i+1}", u)

        with tab_maestros:
            cargas = db.collection("carga_academica").where("grado", "==", alumno_seleccionado.get('grado_actual')).stream()
            lc = [c.to_dict() for c in cargas]
            if lc:
                for c in lc:
                    with st.container(border=True):
                        col_a, col_b = st.columns([2,3])
                        col_a.markdown(f"**{c['nombre_docente']}**")
                        if c.get('es_guia'): col_a.markdown("🌟 *Maestro Guía*")
                        col_b.caption(", ".join(c['materias']))
            else: st.warning("Sin asignaciones.")

        with tab_fin:
            # --- TABLA DE PAGOS (IGUAL AL CODIGO BASE PERO CON LINK A IMPRESION) ---
            pagos = db.collection("finanzas").where("alumno_nie", "==", alumno_seleccionado['nie']).where("tipo", "==", "ingreso").stream()
            lp = [{"id":p.id, **p.to_dict()} for p in pagos]
            if lp:
                df_p = pd.DataFrame(lp).sort_values(by="fecha_legible", ascending=False)
                if "observaciones" not in df_p.columns: df_p["observaciones"] = ""
                st.dataframe(df_p[['fecha_legible', 'descripcion', 'monto', 'observaciones']], use_container_width=True)
                
                # Reimpresión rápida
                sel_p = st.selectbox("Reimprimir Recibo:", ["Seleccionar..."] + [f"{p['fecha_legible']} - ${p['monto']}" for p in lp])
                if sel_p != "Seleccionar...":
                    if st.button("Ver Recibo"):
                        p_obj = next(p for p in lp if f"{p['fecha_legible']} - ${p['monto']}" == sel_p)
                        st.session_state.recibo_temp = p_obj
                        # Hacemos rerun para que el módulo Finanzas capture el recibo y lo muestre
                        st.info("Vaya a la pestaña 'Finanzas' del menú principal para imprimir este recibo con formato oficial.")
            else: st.info("Sin pagos.")

        with tab_notas:
            # --- BOLETA DE NOTAS AUTOMÁTICA ---
            year_actual = datetime.now().year
            st.subheader(f"Boleta de Calificaciones {year_actual}")
            
            # Buscar Guía
            q_guia = db.collection("carga_academica").where("grado", "==", alumno_seleccionado['grado_actual']).stream()
            maestro_guia = "No asignado"
            for d in q_guia:
                if d.to_dict().get('es_guia'): 
                    maestro_guia = d.to_dict()['nombre_docente']; break
            
            # Recuperar Notas
            notas_ref = db.collection("notas").where("nie", "==", alumno_seleccionado['nie']).stream()
            notas_map = {}
            for doc in notas_ref:
                d = doc.to_dict()
                if d['materia'] not in notas_map: notas_map[d['materia']] = {}
                notas_map[d['materia']][d['mes']] = d['promedio_final']
            
            if not notas_map:
                st.warning("No hay notas registradas.")
            else:
                filas = []
                materias_grado = MAPA_MATERIAS.get(alumno_seleccionado['grado_actual'], [])
                for mat in materias_grado:
                    if mat in notas_map:
                        n = notas_map[mat]
                        # Cálculo Trimestral
                        t1 = redondear_mined((n.get("Febrero",0)+n.get("Marzo",0)+n.get("Abril",0))/3)
                        t2 = redondear_mined((n.get("Mayo",0)+n.get("Junio",0)+n.get("Julio",0))/3)
                        t3 = redondear_mined((n.get("Agosto",0)+n.get("Septiembre",0)+n.get("Octubre",0))/3)
                        fin = redondear_mined((t1+t2+t3)/3)
                        
                        filas.append({
                            "Asignatura": mat, "TI": t1, "TII": t2, "TIII": t3, "FINAL": fin
                        })
                
                if filas:
                    df_b = pd.DataFrame(filas)
                    st.dataframe(df_b, use_container_width=True)
                    
                    # Generación HTML para impresión
                    html_rows = ""
                    for _, r in df_b.iterrows():
                        html_rows += f"<tr><td style='text-align:left;padding:5px'>{r['Asignatura']}</td><td>{r['TI']}</td><td>{r['TII']}</td><td>{r['TIII']}</td><td style='background:#ddd'><b>{r['FINAL']}</b></td></tr>"
                    
                    logo = get_image_base64("logo.png"); h_img = f'<img src="{logo}" height="60">' if logo else ""
                    html_boleta = f"""
                    <div style="font-family:Arial; font-size:12px; padding:20px;">
                        <div style="display:flex; align-items:center; border-bottom:2px solid #000; padding-bottom:10px;">
                            {h_img}<div style="margin-left:15px"><h3>COLEGIO PROFA. BLANCA ELENA</h3><p>INFORME DE NOTAS {year_actual}</p></div>
                        </div>
                        <div style="padding:10px; background:#f9f9f9; margin:10px 0; border:1px solid #ddd;">
                            <b>Alumno:</b> {alumno_seleccionado['nombre_completo']} <br>
                            <b>Grado:</b> {alumno_seleccionado['grado_actual']} | <b>Guía:</b> {maestro_guia}
                        </div>
                        <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
                            <tr style="background:#eee;"><td>ASIGNATURA</td><td>TRIM I</td><td>TRIM II</td><td>TRIM III</td><td>FINAL</td></tr>
                            {html_rows}
                        </table>
                        <br><br><br>
                        <div style="display:flex; justify-content:space-between; text-align:center; padding:0 50px;">
                            <div style="border-top:1px solid #000; width:30%">Orientador(a)</div><div style="border-top:1px solid #000; width:30%">Dirección</div>
                        </div>
                    </div>
                    """
                    components.html(f"""<html><body>{html_boleta}<div style="text-align:center;"><button onclick="window.print()" style="padding:10px;background:black;color:white;">🖨️ IMPRIMIR</button></div></body></html>""", height=600, scrolling=True)

# ==========================================
# 5. FINANZAS (MEJORADO CON RECIBOS Y SELLO)
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Finanzas del Colegio")
    if 'recibo_temp' not in st.session_state: st.session_state.recibo_temp = None
    if 'reporte_html' not in st.session_state: st.session_state.reporte_html = None

    if st.session_state.recibo_temp:
        # --- VISTA RECIBO PREMIUM ---
        r = st.session_state.recibo_temp
        color_tema = "#2e7d32" if r.get('tipo') == 'ingreso' else "#c62828"
        titulo_doc = "RECIBO DE INGRESO" if r.get('tipo') == 'ingreso' else "COMPROBANTE DE EGRESO"
        img = get_image_base64("logo.png"); img_h = f'<img src="{img}" style="height:70px;">' if img else ""
        
        # Intentar cargar sello, si no existe usa logo
        sello = get_image_base64("sello.png") 
        if not sello: sello = img 
        
        st.markdown("""<style>@media print { body * { visibility: hidden; } .ticket-container, .ticket-container * { visibility: visible; } .ticket-container { position: absolute; left: 0; top: 0; width: 100%; margin: 0; } }</style>""", unsafe_allow_html=True)
        
        html_ticket = f"""
        <div class="ticket-container" style="font-family:Arial,sans-serif;color:black;background:white;border:1px solid #ccc; max-width:800px; margin:auto; position:relative;">
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
                    <tr style="border-bottom:1px solid #eee"><td style="padding:10px;font-weight:bold;">Detalle:</td><td style="padding:10px;font-style:italic;">{r.get('observaciones','-')}</td></tr>
                </table>
                <div style="margin-top:30px;text-align:right;">
                    <p style="font-size:12px;color:#666;">Monto Total</p>
                    <h1 style="margin:0;color:{color_tema};font-size:36px;">${r['monto']:.2f}</h1>
                </div>
                <br><br>
                <div style="display:flex;justify-content:space-between;gap:40px;margin-top:40px; align-items:flex-end;">
                    <div style="flex:1;border-top:1px solid #000;text-align:center;font-size:12px;padding-top:5px;">Firma y Sello Colegio</div>
                    <div style="flex:1; text-align:center;">
                        <img src="{sello}" style="width:80px; opacity:0.7; margin-bottom:-20px;">
                    </div>
                    <div style="flex:1;border-top:1px solid #000;text-align:center;font-size:12px;padding-top:5px;">Firma Conforme</div>
                </div>
            </div>
        </div>
        """
        st.markdown(html_ticket, unsafe_allow_html=True)
        c1, c2 = st.columns([1, 4])
        if c1.button("❌ Cerrar"): st.session_state.recibo_temp = None; st.rerun()
        with c2: components.html(f"""<script>function p(){{window.parent.print()}}</script><button onclick="p()" style="background:{color_tema};color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;font-size:16px;">🖨️ Imprimir Comprobante</button>""", height=60)

    elif st.session_state.reporte_html:
        st.markdown("""<style>@media print { body * { visibility: hidden; } .rep, .rep * { visibility: visible; } .rep { position: absolute; left: 0; top: 0; width: 100%; } }</style>""", unsafe_allow_html=True)
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
                        mes = st.selectbox("Mes", LISTA_MESES)
                        monto = st.number_input("Monto $", min_value=0.01)
                        met = st.radio("Pago", ["Efectivo", "Banco"], horizontal=True)
                        obs = st.text_area("Notas")
                        if st.form_submit_button("✅ Cobrar"):
                            data = {
                                "tipo": "ingreso", "descripcion": f"{conc} - {mes}", "monto": monto,
                                "nombre_persona": alum['nombre_completo'], "alumno_nie": alum.get('nie', ''),
                                "fecha": firestore.SERVER_TIMESTAMP, "fecha_dt": datetime.now(),
                                "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M"), "observaciones": obs
                            }
                            db.collection("finanzas").add(data)
                            st.session_state.recibo_temp = data; st.session_state.alumno_pago = None; st.rerun()
        
        with tab2:
            st.subheader("Registrar Salida")
            cat = st.selectbox("Categoría", ["Pago de Planilla (Maestros)", "Servicios", "Mantenimiento", "Materiales", "Otros"])
            with st.form("f_gasto"):
                c1, c2 = st.columns(2)
                nom = c1.text_input("Persona/Proveedor")
                monto = c2.number_input("Monto $", min_value=0.01)
                obs = st.text_area("Detalle")
                if st.form_submit_button("🔴 Registrar"):
                    data = {"tipo": "egreso", "descripcion": cat, "monto": monto, "nombre_persona": nom, "observaciones": obs, "fecha": firestore.SERVER_TIMESTAMP, "fecha_dt": datetime.now(), "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")}
                    db.collection("finanzas").add(data)
                    st.session_state.recibo_temp = data; st.rerun()

        with tab3:
            st.subheader("Reportes")
            c1, c2, c3 = st.columns(3)
            fi = c1.date_input("Desde", value=date(datetime.now().year, 1, 1))
            ff = c2.date_input("Hasta", value=datetime.now())
            tf = c3.selectbox("Filtro", ["Todos", "Solo Ingresos", "Solo Egresos"])
            if st.button("📄 Generar Reporte"):
                docs = db.collection("finanzas").order_by("fecha", direction=firestore.Query.DESCENDING).stream()
                lista = []
                for d in docs:
                    dd = d.to_dict(); raw_date = dd.get("fecha_dt") or dd.get("fecha")
                    if raw_date:
                        try: f_obj = raw_date.date()
                        except: f_obj = datetime.now().date()
                        if fi <= f_obj <= ff:
                            if tf == "Solo Ingresos" and dd['tipo'] != 'ingreso': continue
                            if tf == "Solo Egresos" and dd['tipo'] != 'egreso': continue
                            lista.append(dd)
                
                if lista:
                    df = pd.DataFrame(lista)
                    ti = df[df['tipo']=='ingreso']['monto'].sum(); te = df[df['tipo']=='egreso']['monto'].sum(); bal = ti - te
                    h_rows = "".join([f"<tr><td>{r['fecha_legible']}</td><td>{r['tipo']}</td><td>{r.get('nombre_persona')}</td><td>{r['descripcion']}</td><td>{r.get('observaciones','')}</td><td>${r['monto']:.2f}</td></tr>" for _,r in df.iterrows()])
                    img = get_image_base64("logo.png"); h_img = f'<img src="{img}" height="50">' if img else ""
                    html = f"""
                    <div class="rep" style="font-family:Arial;padding:20px;color:black;">
                        <div style="display:flex;align-items:center;border-bottom:2px solid #333;padding-bottom:10px;">{h_img}<h2 style="margin-left:15px;">REPORTE FINANCIERO</h2></div>
                        <div style="display:flex;gap:20px;margin:20px 0;">
                            <div style="flex:1;background:#e8f5e9;padding:10px;text-align:center;"><b>INGRESOS:</b> ${ti:,.2f}</div>
                            <div style="flex:1;background:#ffebee;padding:10px;text-align:center;"><b>EGRESOS:</b> ${te:,.2f}</div>
                            <div style="flex:1;background:#e3f2fd;padding:10px;text-align:center;"><b>BALANCE:</b> ${bal:,.2f}</div>
                        </div>
                        <table border='1' style='width:100%;border-collapse:collapse;'><tr><th>FECHA</th><th>TIPO</th><th>PERSONA</th><th>CONCEPTO</th><th>DETALLE</th><th>MONTO</th></tr>{h_rows}</table>
                    </div>
                    """
                    st.session_state.reporte_html = html
                    st.rerun()
                else: st.warning("Sin datos.")

# ==========================================
# 6. NOTAS (IMPLEMENTADO CORRECTAMENTE)
# ==========================================
elif opcion == "Notas":
    st.title("📊 Registro de Notas")
    
    c1, c2, c3 = st.columns(3)
    grado = c1.selectbox("Grado", ["Seleccionar..."] + LISTA_GRADOS_NOTAS)
    
    # Materias dinámicas
    materias_posibles = MAPA_MATERIAS.get(grado, []) if grado != "Seleccionar..." else []
    materia = c2.selectbox("Materia", ["Seleccionar..."] + materias_posibles)
    mes = c3.selectbox("Mes", LISTA_MESES)

    if grado != "Seleccionar..." and materia != "Seleccionar...":
        # Cargar Alumnos
        docs = db.collection("alumnos").where("grado_actual", "==", grado).stream()
        lista = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
        
        if not lista:
            st.warning(f"No hay alumnos en {grado}.")
        else:
            df = pd.DataFrame(lista).sort_values("Nombre")
            id_doc = f"{grado}_{materia}_{mes}".replace(" ","_")
            
            # Columnas según Materia
            if materia == "Conducta":
                cols = ["Nota Mensual"]
            else:
                cols = ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
            
            # Cargar Notas
            doc_ref = db.collection("notas_mensuales").document(id_doc).get()
            if doc_ref.exists:
                datos_db = doc_ref.to_dict().get('detalles', {})
                for c in cols: df[c] = df["NIE"].map(lambda x: datos_db.get(x, {}).get(c, 0.0))
            else:
                for c in cols: df[c] = 0.0
            
            # Columna Promedio Visual
            df["Promedio"] = 0.0
            if doc_ref.exists:
                df["Promedio"] = df["NIE"].map(lambda x: datos_db.get(x, {}).get("Promedio", 0.0))

            # Editor
            config = {
                "NIE": st.column_config.TextColumn(disabled=True),
                "Nombre": st.column_config.TextColumn(disabled=True, width="medium"),
                "Promedio": st.column_config.NumberColumn(disabled=True, format="%.1f")
            }
            for c in cols: config[c] = st.column_config.NumberColumn(min_value=0, max_value=10, step=0.1, format="%.1f")
            
            st.info("Ingrese notas. Promedio se calcula al guardar.")
            edited = st.data_editor(df, column_config=config, hide_index=True, use_container_width=True, key=id_doc)
            
            if st.button("💾 Guardar Notas", type="primary"):
                batch = db.batch()
                detalles = {}
                for _, row in edited.iterrows():
                    if materia == "Conducta":
                        prom = row["Nota Mensual"]
                    else:
                        prom = (row["Act1 (25%)"]*0.25 + row["Act2 (25%)"]*0.25 + 
                                row["Alt1 (10%)"]*0.10 + row["Alt2 (10%)"]*0.10 + 
                                row["Examen (30%)"]*0.30)
                    
                    detalles[row["NIE"]] = {c: row[c] for c in cols}
                    detalles[row["NIE"]]["Promedio"] = round(prom, 1)
                    
                    # Individual para Boleta
                    ref = db.collection("notas").document(f"{row['NIE']}_{id_doc}")
                    batch.set(ref, {"nie": row["NIE"], "grado": grado, "materia": materia, "mes": mes, "promedio_final": round(prom, 1)})
                
                # Grupal para Editor
                db.collection("notas_mensuales").document(id_doc).set({"grado": grado, "materia": materia, "mes": mes, "detalles": detalles})
                batch.commit()
                st.success("✅ Guardado.")
                time.sleep(1); st.rerun()

# ==========================================
# 7. CONFIGURACIÓN (ZONA DE PELIGRO)
# ==========================================
elif opcion == "Configuración":
    st.header("⚙️ Configuración")
    with st.expander("🗑️ BORRAR TODA LA BASE DE DATOS"):
        st.error("¡CUIDADO!")
        if st.button("💣 Ejecutar Borrado") and st.text_input("Escribe BORRAR:") == "BORRAR":
            colls = ["alumnos", "maestros_perfil", "carga_academica", "finanzas", "notas", "notas_mensuales"]
            for c in colls:
                for d in db.collection(c).stream(): d.reference.delete()
            st.success("Sistema reiniciado.")