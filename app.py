import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime
import json

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión Escolar", layout="wide", page_icon="🎓")

# --- CONEXIÓN INTELIGENTE (NUBE Y LOCAL) ---
@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        if "firebase_key" in st.secrets:
            key_dict = dict(st.secrets["firebase_key"])
            cred = credentials.Certificate(key_dict)
        else:
            cred = credentials.Certificate("credenciales.json") 
            
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'gestioncbeh.firebasestorage.app' 
        })
    return firestore.client()

try:
    db = conectar_firebase()
    conexion_exitosa = True
except Exception as e:
    st.error(f"⚠️ Error conectando a Firebase: {e}")
    conexion_exitosa = False

# --- FUNCIÓN AYUDANTE PARA SUBIR FOTOS ---
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

# --- BARRA LATERAL (MENÚ) ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("⚠️ Falta 'logo.png'")
    st.markdown("---")
    st.header("Menú Principal")
    opcion = st.radio("Navegación:", ["Inicio", "Inscripción Alumnos", "Consulta Alumnos", "Finanzas", "Notas", "Configuración"])
    st.markdown("---")
    if conexion_exitosa: st.success("🟢 Conectado a la Nube")

if not conexion_exitosa: st.stop() 

# ==========================================
# 1. PANTALLA DE INICIO
# ==========================================
if opcion == "Inicio":
    st.title("🍎 Panel de Control")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo Escolar", "2026")
    c2.metric("Sistema", "Online")
    c3.metric("Estado", "Activo")
    st.info("👈 Selecciona una opción del menú para comenzar.")

# ==========================================
# 2. PANTALLA DE INSCRIPCIÓN
# ==========================================
elif opcion == "Inscripción Alumnos":
    st.title("📝 Nueva Inscripción")
    with st.form("ficha_alumno"):
        st.subheader("Datos del Estudiante")
        c1, c2 = st.columns(2)
        with c1:
            nie = st.text_input("NIE (Identificador Único)*", placeholder="Ej: 1234567")
            nombres = st.text_input("Nombres*")
            apellidos = st.text_input("Apellidos*")
            fecha_nac = st.date_input("Fecha de Nacimiento", min_value=datetime(2010, 1, 1))
            estado = st.selectbox("Estado Actual", ["Activo", "Inactivo", "Expulsado"]) 
        with c2:
            lista_grados = ["Kinder 4", "Kinder 5", "Kinder 6", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
            grado = st.selectbox("Grado a Matricular", lista_grados)
            encargado = st.text_input("Nombre del Padre/Encargado")
            telefono = st.text_input("Teléfono de Contacto")
            direccion = st.text_area("Dirección")
        st.markdown("---")
        st.subheader("📂 Documentos Digitales")
        dc1, dc2, dc3 = st.columns(3)
        foto_perfil = dc1.file_uploader("Foto Alumno", type=["jpg", "png", "jpeg"])
        partida = dc2.file_uploader("Partida Nacimiento", type=["pdf", "jpg"])
        dui = dc3.file_uploader("DUI Responsable", type=["pdf", "jpg"])
        enviado = st.form_submit_button("💾 Guardar Inscripción", type="primary")

        if enviado:
            if not nie or not nombres or not apellidos:
                st.error("⚠️ Faltan datos obligatorios.")
            else:
                with st.spinner("Guardando..."):
                    ruta = f"expedientes/{nie}"
                    datos = {
                        "nie": nie, "nombres": nombres, "apellidos": apellidos, "nombre_completo": f"{nombres} {apellidos}",
                        "grado_actual": grado, "estado": estado,
                        "encargado": {"nombre": encargado, "telefono": telefono, "direccion": direccion},
                        "documentos": {"foto_url": subir_archivo(foto_perfil, ruta), "partida_url": subir_archivo(partida, ruta), "dui_url": subir_archivo(dui, ruta)},
                        "fecha_registro": firestore.SERVER_TIMESTAMP
                    }
                    db.collection("alumnos").document(nie).set(datos)
                    st.success(f"✅ ¡Alumno {nombres} registrado!")

# ==========================================
# 3. PANTALLA DE CONSULTA
# ==========================================
elif opcion == "Consulta Alumnos":
    st.title("🔎 Consulta de Expediente")
    col_search, _ = st.columns([1, 2])
    with col_search:
        nie_consulta = st.text_input("Ingrese NIE para buscar:", placeholder="Ej: 1234567")
        btn_consultar = st.button("Buscar Expediente")
    st.markdown("---")

    if nie_consulta and btn_consultar:
        doc = db.collection("alumnos").document(nie_consulta).get()
        if doc.exists:
            datos = doc.to_dict()
            col_foto, col_info_p = st.columns([1, 3])
            with col_foto:
                foto = datos.get("documentos", {}).get("foto_url")
                st.image(foto if foto else "https://via.placeholder.com/150", width=150)
            with col_info_p:
                st.title(f"{datos['nombres']} {datos['apellidos']}")
                st.subheader(f"Grado: {datos.get('grado_actual')}")
                st.info(f"Estado: {datos.get('estado', 'Activo')}")
            
            tab1, tab2 = st.tabs(["📋 Información Personal", "📞 Contacto y Documentos"])
            with tab1:
                st.write(f"**NIE:** {datos.get('nie')}")
                st.write(f"**Fecha Registro:** {datos.get('fecha_registro')}")
            with tab2:
                enc = datos.get("encargado", {})
                st.write(f"**Padre:** {enc.get('nombre')} | **Tel:** {enc.get('telefono')}")
                docs = datos.get("documentos", {})
                if docs.get("partida_url"): st.link_button("📄 Ver Partida", docs.get("partida_url"))
        else:
            st.warning("❌ Alumno no encontrado.")

# ==========================================
# 4. PANTALLA DE FINANZAS (ACTUALIZADA)
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Gestión Financiera")
    
    # --- SISTEMA DE GESTIÓN DE RECIBOS (EN SESIÓN) ---
    if 'recibo_imprimir' not in st.session_state:
        st.session_state.recibo_imprimir = None

    # Si hay un recibo pendiente, lo mostramos (bloqueando lo demás para evitar errores)
    if st.session_state.recibo_imprimir:
        recibo = st.session_state.recibo_imprimir
        
        # Configuración de colores según tipo
        es_ingreso = recibo['tipo'] == 'ingreso'
        color_tema = "#2e7d32" if es_ingreso else "#c62828" # Verde o Rojo
        titulo_doc = "RECIBO DE INGRESO" if es_ingreso else "COMPROBANTE DE EGRESO"
        
        # CSS MÁGICO PARA IMPRESIÓN (Corrige las 2 páginas)
        st.markdown("""
            <style>
            @media print {
                @page { margin: 0; size: auto; }
                body * { visibility: hidden; }
                [data-testid="stSidebar"], header, footer { display: none !important; }
                .ticket-impresion, .ticket-impresion * { visibility: visible !important; }
                .ticket-impresion { 
                    position: absolute; left: 0; top: 0; width: 100%; 
                    margin: 0; padding: 20px; background-color: white; 
                }
            }
            </style>
        """, unsafe_allow_html=True)

        st.success(f"✅ Transacción registrada. Listo para imprimir.")

        # HTML DEL RECIBO (UNIFICADO)
        html_recibo = f"""
        <div class="ticket-impresion" style="border: 2px solid {color_tema}; padding: 30px; border-radius: 10px; max-width: 700px; margin: auto; font-family: sans-serif;">
            <div style="text-align: center; border-bottom: 2px solid {color_tema}; padding-bottom: 10px;">
                <h2 style="margin: 0; color: {color_tema};">🏫 COLEGIO PROFA. BLANCA ELENA</h2>
                <p style="color: gray; margin: 5px;">{titulo_doc}</p>
            </div>
            
            <table style="width: 100%; margin-top: 20px; border-collapse: collapse;">
                <tr>
                    <td><strong>📅 Fecha:</strong> {recibo['fecha_legible']}</td>
                    <td style="text-align: right;"><strong>🧾 Folio:</strong> #{str(int(datetime.now().timestamp()))[-6:]}</td>
                </tr>
            </table>

            <div style="background-color: #f9f9f9; padding: 15px; margin-top: 20px; border-radius: 5px;">
                <p><strong>👤 Nombre:</strong> {recibo.get('alumno_nombre', recibo.get('proveedor', 'N/A'))}</p>
                <p><strong>📝 Concepto:</strong> {recibo['descripcion']}</p>
                <p><strong>📄 Detalle:</strong> {recibo.get('observaciones', 'Sin observaciones')}</p>
            </div>

            <div style="text-align: right; margin-top: 20px;">
                <p style="font-size: 0.9em;">Método de Pago: {recibo['metodo'] if 'metodo' in recibo else 'Efectivo'}</p>
                <h1 style="color: {color_tema}; margin: 0;">Total: ${recibo['monto']:.2f}</h1>
            </div>

            <br><br>
            <div style="display: flex; justify-content: space-between; margin-top: 40px;">
                <div style="text-align: center; width: 40%; border-top: 1px solid black; padding-top: 5px;">Firma y Sello Colegio</div>
                <div style="text-align: center; width: 40%; border-top: 1px solid black; padding-top: 5px;">Firma Recibido/Conforme</div>
            </div>
        </div>
        """
        st.markdown(html_recibo, unsafe_allow_html=True)

        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("❌ Cerrar y Continuar", type="primary"):
                st.session_state.recibo_imprimir = None
                st.rerun()
        with c2:
            st.info("🖨️ Presiona **Ctrl + P** para imprimir.")
            
    else:
        # --- SI NO HAY RECIBO, MOSTRAMOS LOS TABS NORMALES ---
        tab_ingresos, tab_gastos, tab_balance = st.tabs(["💵 Ingresos (Cobros)", "💸 Egresos (Gastos)", "📈 Reporte Financiero"])

        # 1. INGRESOS
        with tab_ingresos:
            st.subheader("Cobro de Mensualidades")
            TARIFAS = {"Parvularia": 12.00, "Primer Ciclo": 13.00, "Segundo Ciclo": 14.00, "Tercer Ciclo": 15.00}
            
            c_search, c_form = st.columns([1, 2])
            with c_search:
                nie_pagar = st.text_input("Buscar NIE Alumno:")
                if st.button("🔍 Buscar"):
                    doc = db.collection("alumnos").document(nie_pagar).get()
                    if doc.exists: st.session_state.pago_alumno = doc.to_dict()
                    else: st.error("No encontrado"); st.session_state.pago_alumno = None

            if st.session_state.get("pago_alumno"):
                d = st.session_state.pago_alumno
                with c_form:
                    st.info(f"Cobrando a: **{d['nombres']} {d['apellidos']}**")
                    with st.form("form_ingreso"):
                        c1, c2 = st.columns(2)
                        concepto = c1.selectbox("Concepto", ["Mensualidad", "Matrícula", "Uniforme", "Otros"])
                        mes = c1.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre"])
                        monto = c2.number_input("Monto ($)", min_value=0.01, step=0.01)
                        metodo = c2.radio("Método", ["Efectivo", "Banco"], horizontal=True)
                        obs = st.text_area("Observaciones")

                        if st.form_submit_button("✅ Registrar Ingreso"):
                            datos_recibo = {
                                "tipo": "ingreso",
                                "descripcion": f"{concepto} - {mes}",
                                "monto": monto,
                                "alumno_nombre": d['nombre_completo'],
                                "observaciones": obs,
                                "metodo": metodo,
                                "fecha": firestore.SERVER_TIMESTAMP,
                                "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
                            }
                            db.collection("finanzas").add(datos_recibo)
                            st.session_state.recibo_imprimir = datos_recibo
                            st.session_state.pago_alumno = None
                            st.rerun()

        # 2. GASTOS (NUEVO SISTEMA DE COMPROBANTE)
        with tab_gastos:
            st.subheader("Registro de Gastos")
            with st.form("form_gasto"):
                c1, c2 = st.columns(2)
                categoria = c1.selectbox("Categoría", ["Planilla Maestros", "Servicios (Luz/Agua)", "Mantenimiento", "Materiales", "Otros"])
                proveedor = c1.text_input("Pagado a (Nombre/Empresa):")
                monto = c2.number_input("Monto ($)", min_value=0.01, step=0.01)
                obs = st.text_area("Detalle del Gasto")
                
                if st.form_submit_button("🔴 Registrar Gasto"):
                    datos_gasto = {
                        "tipo": "egreso",
                        "descripcion": categoria,
                        "proveedor": proveedor,
                        "monto": monto,
                        "observaciones": obs,
                        "fecha": firestore.SERVER_TIMESTAMP,
                        "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    db.collection("finanzas").add(datos_gasto)
                    st.session_state.recibo_imprimir = datos_gasto # Esto activa la pantalla de impresión
                    st.rerun()

        # 3. REPORTE (INGRESOS VS EGRESOS)
        with tab_balance:
            st.subheader("Balance General")
            if st.button("🔄 Actualizar Tabla"): st.rerun()

            docs = db.collection("finanzas").stream()
            movimientos = []
            t_ing = 0.0
            t_egr = 0.0

            for doc in docs:
                data = doc.to_dict()
                if "fecha" in data: # Solo procesar si tiene fecha
                    movimientos.append(data)
                    if data.get("tipo") == "ingreso": t_ing += data.get("monto", 0)
                    elif data.get("tipo") == "egreso": t_egr += data.get("monto", 0)
            
            # Métricas
            balance = t_ing - t_egr
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Ingresos", f"${t_ing:,.2f}")
            m2.metric("Total Egresos", f"${t_egr:,.2f}")
            m3.metric("Balance Final", f"${balance:,.2f}", delta=balance)
            
            st.markdown("### 📊 Detalle de Movimientos")
            if movimientos:
                df = pd.DataFrame(movimientos)
                # Limpiar fechas
                df['fecha_str'] = df['fecha'].apply(lambda x: x.strftime("%d/%m/%Y") if x else "-")
                
                # Seleccionar columnas útiles
                cols = ["fecha_str", "tipo", "descripcion", "monto", "observaciones"]
                # Renombrar para que se vea bonito
                df_view = df[cols].rename(columns={"fecha_str": "Fecha", "tipo": "Tipo", "descripcion": "Concepto", "monto": "Monto", "observaciones": "Nota"})
                
                # Colorear fila según tipo (Truco visual)
                st.dataframe(df_view, use_container_width=True)

                # Botón descargar
                csv = df_view.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar Reporte (Excel)", csv, "reporte_finanzas.csv", "text/csv")
            else:
                st.info("No hay movimientos registrados.")

# ==========================================
# 5. PANTALLA DE NOTAS
# ==========================================
elif opcion == "Notas":
    st.title("📊 Notas")
    st.info("Próximamente: Carga de Excel para cálculo de promedios.")
    archivo = st.file_uploader("Subir Excel de Notas", type=["xlsx"])
    if archivo:
        df = pd.read_excel(archivo)
        st.dataframe(df)

# ==========================================
# 6. CONFIGURACIÓN
# ==========================================
elif opcion == "Configuración":
    st.header("⚙️ Configuración")
    st.write("Opciones del sistema.")