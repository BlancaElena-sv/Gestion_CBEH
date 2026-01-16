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
    opcion = st.radio("Menú Principal:", ["Inicio", "Inscripción Alumnos", "Consulta Alumnos", "Finanzas", "Notas", "Configuración"])
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
# 2. INSCRIPCIÓN
# ==========================================
elif opcion == "Inscripción Alumnos":
    st.title("📝 Nueva Inscripción")
    with st.form("ficha_alumno"):
        st.subheader("Datos del Estudiante")
        c1, c2 = st.columns(2)
        with c1:
            nie = st.text_input("NIE*", placeholder="Ej: 1234567")
            nombres = st.text_input("Nombres*")
            apellidos = st.text_input("Apellidos*")
            estado = st.selectbox("Estado", ["Activo", "Inactivo"]) 
        with c2:
            grados = ["Kinder 4", "Kinder 5", "Kinder 6", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
            grado = st.selectbox("Grado", grados)
            encargado = st.text_input("Encargado")
            telefono = st.text_input("Teléfono")
            direccion = st.text_area("Dirección")
        
        st.markdown("---")
        foto = st.file_uploader("Foto Alumno", type=["jpg", "png"])
        enviado = st.form_submit_button("💾 Guardar", type="primary")

        if enviado and nie and nombres:
            with st.spinner("Guardando..."):
                ruta = f"expedientes/{nie}"
                datos = {
                    "nie": nie, "nombre_completo": f"{nombres} {apellidos}", "nombres": nombres, "apellidos": apellidos,
                    "grado_actual": grado, "estado": estado,
                    "encargado": {"nombre": encargado, "telefono": telefono, "direccion": direccion},
                    "documentos": {"foto_url": subir_archivo(foto, ruta)},
                    "fecha_registro": firestore.SERVER_TIMESTAMP
                }
                db.collection("alumnos").document(nie).set(datos)
                st.success("✅ Alumno registrado")

# ==========================================
# 3. CONSULTA
# ==========================================
elif opcion == "Consulta Alumnos":
    st.title("🔎 Expediente")
    nie_bus = st.text_input("Buscar NIE:")
    if st.button("Buscar") and nie_bus:
        doc = db.collection("alumnos").document(nie_bus).get()
        if doc.exists:
            d = doc.to_dict()
            c1, c2 = st.columns([1, 3])
            with c1: st.image(d.get("documentos", {}).get("foto_url", "https://via.placeholder.com/150"))
            with c2:
                st.subheader(d['nombre_completo'])
                st.write(f"**Grado:** {d.get('grado_actual')} | **Estado:** {d.get('estado', 'Activo')}")
                enc = d.get('encargado', {})
                st.write(f"**Encargado:** {enc.get('nombre')} - {enc.get('telefono')}")
        else:
            st.warning("No encontrado")

# ==========================================
# 4. FINANZAS (REPORTE DE IMPRESIÓN MEJORADO)
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Finanzas del Colegio")
    
    # Inicializar estados
    if 'recibo_temp' not in st.session_state: st.session_state.recibo_temp = None
    if 'reporte_html' not in st.session_state: st.session_state.reporte_html = None

    # --- 1. MODO IMPRESIÓN DE RECIBO INDIVIDUAL ---
    if st.session_state.recibo_temp:
        r = st.session_state.recibo_temp
        es_ingreso = r['tipo'] == 'ingreso'
        color = "#2e7d32" if es_ingreso else "#c62828"
        titulo = "RECIBO DE INGRESO" if es_ingreso else "COMPROBANTE DE EGRESO"
        
        logo_img = get_image_base64("logo.png")
        img_html = f'<img src="{logo_img}" style="width: 80px; vertical-align: middle; margin-right: 15px;">' if logo_img else ""

        st.markdown("""<style>@media print { @page { margin: 0; size: auto; } body * { visibility: hidden; } [data-testid="stSidebar"], header, footer { display: none !important; } .ticket-print, .ticket-print * { visibility: visible !important; } .ticket-print { position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 40px; background-color: white; } }</style>""", unsafe_allow_html=True)
        st.success("✅ Guardado. Listo para imprimir.")

        html_extra = ""
        if r.get('alumno_nie'):
            html_extra = f"""<div style="margin: 5px 0; font-size: 14px;"><strong>🆔 NIE:</strong> {r.get('alumno_nie')} &nbsp;|&nbsp; <strong>🎓 Grado:</strong> {r.get('alumno_grado')}</div>"""

        html_ticket = f"""
        <div class="ticket-print" style="border: 2px solid {color}; padding: 30px; max-width: 800px; margin: auto; font-family: Arial, sans-serif; background: white;">
        <div style="text-align: center; border-bottom: 2px solid {color}; padding-bottom: 10px; display: flex; align-items: center; justify-content: center;">
        {img_html}
        <div><h2 style="margin: 0; color: {color};">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2><p style="color: gray; margin: 5px; font-size: 14px;">{titulo}</p></div>
        </div><br>
        <table style="width: 100%; border-collapse: collapse;"><tr><td><strong>Fecha:</strong> {r['fecha_legible']}</td><td style="text-align: right;"><strong>Folio:</strong> #{str(int(datetime.now().timestamp()))[-6:]}</td></tr></table>
        <div style="background-color: #f8f9fa; padding: 20px; margin-top: 20px; border-radius: 5px; border: 1px solid #eee;">
        <p style="margin: 5px 0;"><strong>👤 Nombre:</strong> {r.get('nombre_persona', 'N/A')}</p>
        {html_extra}
        <p style="margin: 5px 0;"><strong>📝 Concepto:</strong> {r['descripcion']}</p>
        <p style="margin: 5px 0;"><strong>ℹ️ Detalle:</strong> {r.get('observaciones', '-')}</p>
        </div>
        <div style="text-align: right; margin-top: 25px;">
        <p style="margin: 0; font-size: 14px; color: #666;">Método: {r.get('metodo', 'Efectivo')}</p>
        <h1 style="margin: 5px 0; color: {color};">Total: ${r['monto']:.2f}</h1>
        </div><br><br><br>
        <div style="display: flex; justify-content: space-between; margin-top: 50px;">
        <div style="text-align: center; width: 40%; border-top: 1px solid #333; padding-top: 5px; font-size: 12px;">Firma y Sello Colegio</div>
        <div style="text-align: center; width: 40%; border-top: 1px solid #333; padding-top: 5px; font-size: 12px;">Firma Conforme</div>
        </div></div>"""
        st.markdown(html_ticket, unsafe_allow_html=True)
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("❌ Cerrar Recibo", type="primary"):
                st.session_state.recibo_temp = None
                st.rerun()
        with c2: st.info("Presiona **Ctrl + P** para imprimir.")

    # --- 2. MODO REPORTE GENERAL (NUEVO) ---
    elif st.session_state.reporte_html:
        # ESTA ES LA VISTA DE IMPRESIÓN DEL REPORTE
        st.markdown("""<style>@media print { @page { margin: 10mm; size: landscape; } body * { visibility: hidden; } [data-testid="stSidebar"], header, footer { display: none !important; } .report-print, .report-print * { visibility: visible !important; } .report-print { position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 20px; background-color: white; } }</style>""", unsafe_allow_html=True)
        
        st.markdown(st.session_state.reporte_html, unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("⬅️ Volver a Finanzas", type="primary"):
                st.session_state.reporte_html = None
                st.rerun()
        with c2: st.info("🖨️ Presiona **Ctrl + P** y selecciona 'Guardar como PDF'.")

    else:
        # --- 3. PANTALLAS DE GESTIÓN (NORMAL) ---
        tab1, tab2, tab3 = st.tabs(["💵 Ingresos", "💸 Gastos", "📊 Reporte Formal"])
        
        # 1. INGRESOS
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

        # 2. GASTOS
        with tab2:
            st.subheader("Registrar Salida de Dinero")
            with st.form("f_gasto"):
                c1, c2 = st.columns(2)
                cat = c1.selectbox("Categoría", ["Planilla", "Servicios", "Mantenimiento", "Materiales", "Otros"])
                prov = c1.text_input("Pagar a (Nombre):")
                monto = c2.number_input("Monto $", min_value=0.01)
                obs = st.text_area("Detalle del gasto")
                if st.form_submit_button("🔴 Registrar Gasto"):
                    data = {
                        "tipo": "egreso", "descripcion": cat, "monto": monto,
                        "nombre_persona": prov, "observaciones": obs,
                        "fecha": firestore.SERVER_TIMESTAMP, "fecha_dt": datetime.now(),
                        "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    db.collection("finanzas").add(data)
                    st.session_state.recibo_temp = data
                    st.rerun()

        # 3. REPORTE FORMAL (TABLA BONITA)
        with tab3:
            st.subheader("Generación de Reportes PDF")
            
            # --- FILTROS ---
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
                    fecha_obj = None
                    if raw_date:
                        if hasattr(raw_date, "date"): fecha_obj = raw_date.date()
                        elif isinstance(raw_date, datetime): fecha_obj = raw_date.date()
                    
                    item = {
                        "fecha_obj": fecha_obj, 
                        "fecha": d.get("fecha_legible", "-"),
                        "tipo": d.get("tipo", "Desconocido"),
                        "persona": d.get("nombre_persona") or d.get("alumno_nombre") or d.get("proveedor") or "N/A",
                        "nie": d.get("alumno_nie", "-"),
                        "concepto": d.get("descripcion", "-"),
                        "monto": d.get("monto", 0.0)
                    }
                    lista_final.append(item)
                
                df = pd.DataFrame(lista_final)
                if not df.empty:
                    df = df.dropna(subset=['fecha_obj'])
                    df = df[(df['fecha_obj'] >= fecha_ini) & (df['fecha_obj'] <= fecha_fin)]
                    if tipo_filtro == "Solo Ingresos": df = df[df['tipo'] == 'ingreso']
                    elif tipo_filtro == "Solo Egresos": df = df[df['tipo'] == 'egreso']

                if df.empty:
                    st.warning("No hay datos para generar el reporte con esos filtros.")
                else:
                    # CONSTRUIR HTML DEL REPORTE
                    t_ing = df[df['tipo']=='ingreso']['monto'].sum()
                    t_egr = df[df['tipo']=='egreso']['monto'].sum()
                    balance = t_ing - t_egr
                    
                    logo_img = get_image_base64("logo.png")
                    logo_html = f'<img src="{logo_img}" style="height:60px;">' if logo_img else ""
                    
                    filas_html = ""
                    for index, row in df.iterrows():
                        color_tipo = "green" if row['tipo'] == 'ingreso' else "red"
                        filas_html += f"""
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px;">{row['fecha']}</td>
                            <td style="padding: 8px; color: {color_tipo}; font-weight: bold;">{row['tipo'].upper()}</td>
                            <td style="padding: 8px;">{row['persona']}</td>
                            <td style="padding: 8px;">{row['concepto']}</td>
                            <td style="padding: 8px; text-align: right;">${row['monto']:.2f}</td>
                        </tr>
                        """

                    html_reporte = f"""
                    <div class="report-print" style="font-family: Arial, sans-serif; padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #333; padding-bottom: 10px;">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                {logo_html}
                                <div>
                                    <h2 style="margin: 0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2>
                                    <p style="margin: 0; color: gray;">Reporte Financiero Detallado</p>
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <p style="margin: 0;"><strong>Desde:</strong> {fecha_ini.strftime('%d/%m/%Y')}</p>
                                <p style="margin: 0;"><strong>Hasta:</strong> {fecha_fin.strftime('%d/%m/%Y')}</p>
                            </div>
                        </div>

                        <div style="display: flex; gap: 20px; margin: 20px 0;">
                            <div style="flex: 1; background: #e8f5e9; padding: 15px; border-radius: 5px; text-align: center;">
                                <h4 style="margin:0; color: #2e7d32;">INGRESOS</h4>
                                <h2 style="margin:5px 0;">${t_ing:,.2f}</h2>
                            </div>
                            <div style="flex: 1; background: #ffebee; padding: 15px; border-radius: 5px; text-align: center;">
                                <h4 style="margin:0; color: #c62828;">EGRESOS</h4>
                                <h2 style="margin:5px 0;">${t_egr:,.2f}</h2>
                            </div>
                            <div style="flex: 1; background: #e3f2fd; padding: 15px; border-radius: 5px; text-align: center;">
                                <h4 style="margin:0; color: #1565c0;">BALANCE</h4>
                                <h2 style="margin:5px 0;">${balance:,.2f}</h2>
                            </div>
                        </div>

                        <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px;">
                            <thead style="background-color: #f5f5f5;">
                                <tr>
                                    <th style="padding: 10px; text-align: left;">Fecha</th>
                                    <th style="padding: 10px; text-align: left;">Tipo</th>
                                    <th style="padding: 10px; text-align: left;">Responsable / Proveedor</th>
                                    <th style="padding: 10px; text-align: left;">Concepto</th>
                                    <th style="padding: 10px; text-align: right;">Monto</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filas_html}
                            </tbody>
                        </table>
                        <br>
                        <p style="text-align: center; color: gray; font-size: 12px; margin-top: 30px;">Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
                    </div>
                    """
                    st.session_state.reporte_html = html_reporte
                    st.rerun()

# ==========================================
# 5. NOTAS
# ==========================================
elif opcion == "Notas":
    st.title("📊 Notas")
    st.write("Módulo en desarrollo.")

# ==========================================
# 6. CONFIGURACIÓN
# ==========================================
elif opcion == "Configuración":
    st.header("⚙️ Configuración")