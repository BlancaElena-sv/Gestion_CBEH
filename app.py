import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestión Escolar", layout="wide", page_icon="🎓")

# --- CONEXIÓN CON FIREBASE ---
@st.cache_resource
def conectar_firebase():
    # Evitar reinicializar si ya existe la app
    if not firebase_admin._apps:
        # Asegúrate de que 'credenciales.json' esté en la misma carpeta
        cred = credentials.Certificate("credenciales.json") 
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'gestioncbeh.firebasestorage.app' 
        })
    return firestore.client()

# Intentamos conectar
try:
    db = conectar_firebase()
    conexion_exitosa = True
except Exception as e:
    st.error(f"⚠️ Error conectando a Firebase: {e}")
    st.info("Verifica que el archivo 'credenciales.json' esté en la carpeta.")
    conexion_exitosa = False

# --- FUNCIÓN AYUDANTE PARA SUBIR FOTOS ---
def subir_archivo(archivo, ruta_carpeta):
    if archivo is None:
        return None
    try:
        bucket = storage.bucket()
        # Limpieza básica del nombre
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
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.warning("⚠️ Falta 'logo.png'")
    
    st.markdown("---")
    st.header("Menú Principal")
    
    opcion = st.radio(
        "Navegación:",
        ["Inicio", "Inscripción Alumnos", "Consulta Alumnos", "Finanzas", "Notas", "Configuración"]
    )
    
    st.markdown("---")
    if conexion_exitosa:
        st.success("🟢 Conectado a la Nube")

# --- CONTROL DE ACCESO ---
if not conexion_exitosa:
    st.stop() 

# ==========================================
# 1. PANTALLA DE INICIO
# ==========================================
if opcion == "Inicio":
    st.title("🍎 Panel de Control")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ciclo Escolar", "2026")
    col2.metric("Sistema", "Online")
    col3.metric("Estado", "Activo")
    
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
            lista_grados = [
                "Kinder 4", "Kinder 5", "Kinder 6", "Preparatoria",
                "Primer Grado", "Segundo Grado", "Tercer Grado",
                "Cuarto Grado", "Quinto Grado", "Sexto Grado",
                "Séptimo Grado", "Octavo Grado", "Noveno Grado"
            ]
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
                with st.spinner("Guardando en la nube..."):
                    ruta_storage = f"expedientes/{nie}"
                    link_foto = subir_archivo(foto_perfil, ruta_storage)
                    link_partida = subir_archivo(partida, ruta_storage)
                    link_dui = subir_archivo(dui, ruta_storage)

                    datos = {
                        "nie": nie,
                        "nombres": nombres,
                        "apellidos": apellidos,
                        "nombre_completo": f"{nombres} {apellidos}",
                        "grado_actual": grado,
                        "estado": estado,
                        "encargado": {"nombre": encargado, "telefono": telefono, "direccion": direccion},
                        "documentos": {"foto_url": link_foto, "partida_url": link_partida, "dui_url": link_dui},
                        "fecha_registro": firestore.SERVER_TIMESTAMP
                    }
                    
                    db.collection("alumnos").document(nie).set(datos)
                    st.balloons()
                    st.success(f"✅ ¡Alumno {nombres} registrado exitosamente!")

# ==========================================
# 3. PANTALLA DE CONSULTA
# ==========================================
elif opcion == "Consulta Alumnos":
    st.title("🔎 Consulta de Expediente")
    
    col_search, col_spacer = st.columns([1, 2])
    with col_search:
        nie_consulta = st.text_input("Ingrese NIE para buscar:", placeholder="Ej: 1234567")
        btn_consultar = st.button("Buscar Expediente")
    
    st.markdown("---")

    if nie_consulta and btn_consultar:
        doc = db.collection("alumnos").document(nie_consulta).get()
        
        if doc.exists:
            datos = doc.to_dict()
            
            # --- ENCABEZADO ---
            col_foto, col_info_p = st.columns([1, 3])
            
            with col_foto:
                foto = datos.get("documentos", {}).get("foto_url")
                if foto:
                    st.image(foto, width=150, caption="Foto de Perfil")
                else:
                    st.image("https://via.placeholder.com/150", width=150, caption="Sin Foto")
            
            with col_info_p:
                st.title(f"{datos['nombres']} {datos['apellidos']}")
                st.subheader(f"Grado: {datos.get('grado_actual')}")
                
                est = datos.get("estado", "Activo")
                if est == "Activo": st.success(f"🟢 ALUMNO {est.upper()}")
                elif est == "Inactivo": st.warning(f"🟡 ALUMNO {est.upper()}")
                else: st.error(f"🔴 ALUMNO {est.upper()}")
            
            # --- TABS DE DETALLE ---
            tab1, tab2 = st.tabs(["📋 Información Personal", "📞 Contacto y Documentos"])
            
            with tab1:
                st.write(f"**NIE:** {datos.get('nie')}")
                st.write(f"**Fecha Registro:** {datos.get('fecha_registro')}")
            
            with tab2:
                encargado = datos.get("encargado", {})
                st.write(f"**Padre/Encargado:** {encargado.get('nombre', 'No registrado')}")
                st.write(f"**Teléfono:** {encargado.get('telefono', 'No registrado')}")
                st.write(f"**Dirección:** {encargado.get('direccion', 'No registrada')}")
                
                st.markdown("#### Documentos Adjuntos")
                docs = datos.get("documentos", {})
                if docs.get("partida_url"): st.link_button("📄 Ver Partida de Nacimiento", docs.get("partida_url"))
                if docs.get("dui_url"): st.link_button("🆔 Ver DUI Responsable", docs.get("dui_url"))

        else:
            st.warning(f"❌ No se encontró ningún alumno con el NIE: {nie_consulta}")

# ==========================================
# 4. PANTALLA DE FINANZAS (COMPLETA & CORREGIDA)
# ==========================================
elif opcion == "Finanzas":
    st.title("💰 Administración Financiera")
    
    # Navegación interna de finanzas
    tab_ingresos, tab_gastos, tab_balance = st.tabs(["💵 Cobros e Ingresos", "💸 Registrar Gastos", "📈 Balance y Reportes"])

    # --- TAB 1: INGRESOS (COBROS ALUMNOS) ---
    with tab_ingresos:
        st.subheader("Cobro de Mensualidades y Servicios")
        
        # Lógica de tarifas
        TARIFAS = {
            "Parvularia": 12.00, "Primer Ciclo": 13.00,
            "Segundo Ciclo": 14.00, "Tercer Ciclo": 15.00
        }
        def obtener_precio(grado):
            if not grado: return 0.0
            if any(x in grado for x in ["Kinder", "Preparatoria"]): return TARIFAS["Parvularia"]
            if any(x in grado for x in ["Primer", "Segundo", "Tercer"]): return TARIFAS["Primer Ciclo"]
            if any(x in grado for x in ["Cuarto", "Quinto", "Sexto"]): return TARIFAS["Segundo Ciclo"]
            return TARIFAS["Tercer Ciclo"]

        col_busqueda, col_form = st.columns([1, 2])
        with col_busqueda:
            nie_pagar = st.text_input("Buscar NIE del Alumno:")
            if st.button("Buscar Alumno"):
                doc = db.collection("alumnos").document(nie_pagar).get()
                if doc.exists:
                    st.session_state.pago_alumno = doc.to_dict()
                    # Limpiamos recibo anterior si existe
                    if 'recibo_exitoso' in st.session_state:
                        del st.session_state['recibo_exitoso']
                else:
                    st.error("Alumno no encontrado")
                    st.session_state.pago_alumno = None

        # Formulario de cobro
        if st.session_state.get("pago_alumno"):
            datos = st.session_state.pago_alumno
            with col_form:
                st.info(f"Cobrando a: **{datos['nombres']} {datos['apellidos']}** ({datos['grado_actual']})")
                
                with st.form("form_cobro"):
                    c_concepto, c_monto = st.columns(2)
                    with c_concepto:
                        concepto = st.selectbox("Concepto", ["Mensualidad", "Matrícula", "Uniforme", "Libros", "Constancia", "Otros"])
                        mes = st.selectbox("Mes Correspondiente", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
                    
                    with c_monto:
                        val_sugerido = obtener_precio(datos['grado_actual']) if concepto == "Mensualidad" else 0.0
                        monto = st.number_input("Monto ($)", value=val_sugerido, step=0.01)
                        metodo = st.radio("Método", ["Efectivo", "Transferencia/Banco"], horizontal=True)
                    
                    # Campo de observaciones
                    observaciones = st.text_area("Observaciones (Opcional)", placeholder="Ej: Pago adelantado, incluye mora, etc.")

                    if st.form_submit_button("✅ Procesar Pago"):
                        datos_recibo = {
                            "tipo": "ingreso",
                            "descripcion": f"{concepto} - {mes}",
                            "concepto_base": concepto,
                            "monto": monto,
                            "alumno_nie": datos['nie'],
                            "alumno_nombre": f"{datos['nombres']} {datos['apellidos']}",
                            "grado": datos['grado_actual'],
                            "metodo": metodo,
                            "observaciones": observaciones,
                            "fecha": firestore.SERVER_TIMESTAMP,
                            "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "mes_registro": datetime.now().strftime("%B") 
                        }
                        
                        # Guardar en BD
                        db.collection("finanzas").add(datos_recibo)
                        
                        # Guardar en sesión para mostrar el recibo
                        st.session_state.recibo_exitoso = datos_recibo
                        st.session_state.pago_alumno = None # Limpiar formulario
                        st.rerun()

    # --- SECCIÓN DE RECIBO (VISUALIZACIÓN E IMPRESIÓN) ---
    if st.session_state.get("recibo_exitoso"):
        recibo = st.session_state.recibo_exitoso
        
        # 1. ESTILOS CSS PARA "LIMPIAR" LA IMPRESIÓN
        st.markdown("""
            <style>
            @media print {
                /* Ocultar TODO el cuerpo de la aplicación por defecto */
                body * {
                    visibility: hidden;
                }
                /* Ocultar barra lateral, cabecera y footer explícitamente */
                [data-testid="stSidebar"], header, footer, .stDeployButton {
                    display: none !important;
                }
                
                /* Hacer visible SOLO el contenedor del recibo */
                .ticket-impresion, .ticket-impresion * {
                    visibility: visible !important;
                }
                
                /* Posicionar el recibo al inicio de la hoja en blanco */
                .ticket-impresion {
                    position: absolute !important;
                    left: 0;
                    top: 0;
                    width: 100%;
                    margin: 0;
                    padding: 20px;
                    background-color: white;
                    border: 2px solid black; 
                }
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.success("✅ ¡Pago registrado! Ahora puedes imprimir el recibo.")

        # 2. ESTRUCTURA DEL RECIBO EN HTML
        html_recibo = f"""
        <div class="ticket-impresion" style="
            border: 1px solid #ccc; 
            padding: 30px; 
            border-radius: 10px; 
            background-color: #f9f9f9; 
            max-width: 600px; 
            margin: auto;">
            
            <div style="text-align: center;">
                <h2 style="margin: 0;">🏫 COLEGIO PROFA. BLANCA ELENA</h2>
                <p style="color: gray; margin-top: 5px;">Comprobante de Ingreso</p>
            </div>
            
            <hr style="border-top: 2px dashed #bbb;">
            
            <div style="display: flex; justify-content: space-between;">
                <p><strong>📅 Fecha:</strong> {recibo['fecha_legible']}</p>
                <p><strong>🧾 Folio:</strong> #{str(int(datetime.now().timestamp()))[-6:]}</p>
            </div>
            
            <p><strong>👤 Alumno:</strong> {recibo['alumno_nombre']}</p>
            <p><strong>🆔 NIE:</strong> {recibo['alumno_nie']}</p>
            <p><strong>🎓 Grado:</strong> {recibo['grado']}</p>
            
            <div style="background-color: #fff; border: 1px solid #eee; padding: 15px; margin-top: 10px;">
                <p style="margin: 0;"><strong>Concepto:</strong> {recibo['descripcion']}</p>
                <p style="margin: 5px 0 0 0; font-size: 0.9em; color: #555;">
                    <em>{recibo.get('observaciones', '')}</em>
                </p>
            </div>
            
            <div style="text-align: right; margin-top: 20px;">
                <p>Método de Pago: {recibo['metodo']}</p>
                <h1 style="color: #2e7d32; margin: 0;">Total: ${recibo['monto']:.2f}</h1>
            </div>
            
            <hr style="margin-top: 30px;">
            <p style="text-align: center; font-size: 0.8em; color: gray;">
                Gracias por su pago puntual. Guarde este documento para cualquier reclamo.
            </p>
        </div>
        """
        
        st.markdown(html_recibo, unsafe_allow_html=True)
        
        # Botones de acción
        col_c1, col_c2 = st.columns([1, 4])
        with col_c1:
            if st.button("Cerrar Recibo"):
                del st.session_state['recibo_exitoso']
                st.rerun()
        with col_c2:
            st.info("🖨️ Presiona **Ctrl + P** (o Cmd + P en Mac) para imprimir. Verás que ahora solo sale el ticket.")

    # --- TAB 2: GASTOS (REGISTRO) ---
    with tab_gastos:
        st.subheader("Registro de Salidas de Dinero")
        
        with st.form("form_gasto"):
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                categoria = st.selectbox("Categoría del Gasto", [
                    "Pago de Planilla (Maestros)", 
                    "Pago Personal Administrativo",
                    "Servicios Básicos (Luz/Agua/Internet)",
                    "Mantenimiento e Infraestructura",
                    "Material Didáctico",
                    "Limpieza",
                    "Eventos y Celebraciones",
                    "Otros"
                ])
                proveedor = st.text_input("A nombre de quién (Proveedor/Maestro):")
            
            with col_g2:
                monto_gasto = st.number_input("Monto del Gasto ($)", min_value=0.01, step=0.01)
                fecha_gasto = st.date_input("Fecha del Gasto")
                nota = st.text_area("Detalles / Observaciones")

            if st.form_submit_button("🔴 Registrar Gasto"):
                fecha_dt = datetime(fecha_gasto.year, fecha_gasto.month, fecha_gasto.day)
                
                db.collection("finanzas").add({
                    "tipo": "egreso",
                    "categoria": categoria,
                    "descripcion": nota if nota else categoria,
                    "proveedor": proveedor,
                    "monto": monto_gasto,
                    "fecha": fecha_dt,
                    "mes_registro": datetime.now().strftime("%B")
                })
                st.success("Gasto registrado correctamente.")

    # --- TAB 3: BALANCE Y REPORTES ---
    with tab_balance:
        st.subheader("Estado Financiero y Reportes")
        
        if st.button("🔄 Actualizar Datos"):
            st.rerun()
            
        # Consultamos movimientos
        docs = db.collection("finanzas").stream()
        
        lista_movimientos = []
        total_ingresos = 0.0
        total_egresos = 0.0

        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            lista_movimientos.append(d)
            
            if d.get("tipo") == "ingreso":
                total_ingresos += d.get("monto", 0)
            elif d.get("tipo") == "egreso":
                total_egresos += d.get("monto", 0)
        
        balance = total_ingresos - total_egresos

        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Ingresos", f"${total_ingresos:,.2f}")
        m2.metric("Total Gastos", f"${total_egresos:,.2f}", delta_color="inverse")
        m3.metric("Balance Total", f"${balance:,.2f}", delta=f"{balance:,.2f}")
        
        st.markdown("---")
        st.write("📋 **Reporte Detallado**")
        
        if lista_movimientos:
            df_fin = pd.DataFrame(lista_movimientos)
            
            # Limpieza de fechas para el reporte
            def formatear_fecha(f):
                if isinstance(f, datetime): return f.strftime("%d/%m/%Y")
                return str(f)[:10]

            if "fecha" in df_fin.columns:
                df_fin['fecha_reporte'] = df_fin['fecha'].apply(formatear_fecha)
            
            # Seleccionar y renombrar columnas
            columnas_visibles = ["fecha_reporte", "tipo", "descripcion", "monto", "metodo", "alumno_nombre", "observaciones"]
            # Filtrar solo columnas existentes
            cols_final = [c for c in columnas_visibles if c in df_fin.columns]
            
            df_mostrar = df_fin[cols_final].sort_values(by="fecha_reporte", ascending=False)
            
            st.dataframe(df_mostrar, use_container_width=True)
            
            # --- BOTÓN DE DESCARGA (REPORTE) ---
            csv = df_mostrar.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Descargar Reporte Completo (Excel/CSV)",
                data=csv,
                file_name=f"reporte_finanzas_{datetime.now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
            )
        else:
            st.info("No hay movimientos registrados para generar reporte.")

# ==========================================
# 5. PANTALLA DE NOTAS
# ==========================================
elif opcion == "Notas":
    st.title("📊 Registro de Notas")
    st.info("⚠️ Sube tu Excel actualizado con las columnas correctas para activar el cálculo automático.")
    
    col1, col2 = st.columns(2)
    with col1:
        mes_sel = st.selectbox("Mes", ["Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"])
    with col2:
        materia_sel = st.selectbox("Materia", ["Matemáticas", "Lenguaje", "Ciencias", "Sociales", "Inglés"])
        
    archivo = st.file_uploader("Subir Excel", type=["xlsx", "csv"])
    
    if archivo:
        try:
            if archivo.name.endswith('csv'): df = pd.read_csv(archivo)
            else: df = pd.read_excel(archivo)
            
            # Mostramos el archivo cargado
            st.dataframe(df)
            
            if st.button("☁️ Guardar Notas (Básico)"):
                st.success("Función pendiente de configurar con tu nuevo Excel (cuando lo subas).")
                
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

# ==========================================
# 6. PANTALLA DE CONFIGURACIÓN
# ==========================================
elif opcion == "Configuración":
    st.header("⚙️ Configuración")
    st.write("Configuración del sistema.")