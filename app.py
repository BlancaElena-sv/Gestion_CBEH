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
st.set_page_config(
    page_title="Sistema de Gestión CBEH", 
    layout="wide", 
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. SISTEMA DE SEGURIDAD Y CONEXIÓN
# ==========================================

@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        try:
            cred = None
            if os.path.exists("credenciales.json"): cred = credentials.Certificate("credenciales.json")
            elif os.path.exists("credenciales"): cred = credentials.Certificate("credenciales")
            elif "firebase_key" in st.secrets: cred = credentials.Certificate(dict(st.secrets["firebase_key"]))
            else: return None
            firebase_admin.initialize_app(cred, {'storageBucket': 'gestioncbeh.firebasestorage.app'})
        except: return None
    return firestore.client()

try:
    db = conectar_firebase()
    if not db: st.stop()
    conexion_exitosa = True
except: st.stop()

# --- USUARIOS Y ROLES ---
USUARIOS = {
    "david": {"pass": "admin123", "rol": "admin", "nombre": "David Fuentes (Dev)"},
    "directora": {"pass": "dir2026", "rol": "admin", "nombre": "Dirección"},
    "profe": {"pass": "profe123", "rol": "docente", "nombre": "Panel Docente"}
}

def login():
    st.markdown("<br><br><h1 style='text-align: center;'>🔐 Acceso al Sistema</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Colegio Profa. Blanca Elena de Hernández</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("login_form"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", type="primary"):
                if user in USUARIOS and USUARIOS[user]["pass"] == password:
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = USUARIOS[user]["rol"]
                    st.session_state["user_name"] = USUARIOS[user]["nombre"]
                    st.rerun()
                else: st.error("Acceso Denegado")

def logout():
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.rerun()

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ==========================================
# 2. CONFIGURACIÓN ACADÉMICA (MALLA 2026)
# ==========================================

# Parvularia
MAT_KINDER = [
    "Relaciones Sociales y Afectivas", "Exploración y Experimentación con el Mundo", 
    "Lenguaje y Comunicación", "Matemática", "Ciencia y Tecnología", 
    "Cuerpo, Movimiento y Bienestar", "Conducta"
]

# I Ciclo (1, 2, 3)
MAT_I_CICLO = [
    "Comunicación", "Números y Formas", "Ciencia y Tecnología", 
    "Ciudadanía y Valores", "Artes", "Desarrollo Corporal", 
    "Ortografía", "Caligrafía", "Lectura", "Conducta"
]

# II Ciclo (4, 5, 6)
MAT_II_CICLO = [
    "Comunicación y Literatura", "Aritmética y Finanzas", "Ciencia y Tecnología", 
    "Ciudadanía y Valores", "Artes", "Desarrollo Corporal", 
    "Ortografía", "Caligrafía", "Lectura", "Conducta"
]

# III Ciclo (7, 8, 9)
MAT_III_CICLO = [
    "Lenguaje y Literatura", "Matemáticas y Datos", "Ciencia y Tecnología", 
    "Ciudadanía y Valores", "Inglés", "Educación Física y Deportes", 
    "Ortografía", "Caligrafía", "Lectura", "Conducta"
]

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
# 3. FUNCIONES AUXILIARES
# ==========================================
def subir_archivo(archivo, ruta):
    if not archivo: return None
    try:
        b = storage.bucket()
        blob = b.blob(f"{ruta}/{archivo.name.replace(' ', '_')}")
        blob.upload_from_file(archivo)
        blob.make_public()
        return blob.public_url
    except: return None

def get_base64(path):
    try: 
        with open(path, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except: return ""

def redondear_mined(valor):
    if valor is None: return 0.0
    parte_entera = int(valor)
    parte_decimal = valor - parte_entera
    if parte_decimal >= 0.5: return float(parte_entera + 1)
    else: return float(parte_entera)

# ==========================================
# 4. BARRA LATERAL (REORGANIZADA)
# ==========================================
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("Falta logo.png")
    
    st.info(f"👤 **{st.session_state['user_name']}**")
    
    if st.session_state["user_role"] == "admin":
        # NUEVO ORDEN SOLICITADO
        opcion = st.radio("Menú Admin:", [
            "Inicio", 
            "Inscripción", 
            "Consulta Alumnos", 
            "Maestros", 
            "Notas", 
            "Finanzas", 
            "Configuración"
        ])
    else:
        # Menú Docente (se mantiene igual)
        opcion = st.radio("Menú Docente:", ["Inicio", "Mis Listados", "Cargar Notas", "Ver Mis Cargas"])
        
    st.markdown("---")
    if st.button("Cerrar Sesión"): logout()
    
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 11px;'>
            <p style='margin-bottom: 5px;'>
                Desarrollado y Propiedad de:<br>
                <b style='font-size: 12px;'>David Fuentes</b>
            </p>
            <p style='margin-bottom: 5px;'>
                <i>Todos los derechos reservados © 2026</i>
            </p>
            <hr style='margin: 5px 0; border-color: #ddd;'>
            <p style='color: #888;'>
                Licencia de uso exclusivo para:<br>
                Colegio Profa. Blanca Elena de Hernández
            </p>
        </div>
        """, unsafe_allow_html=True
    )

# ==========================================
# 5. CONTENIDO PRINCIPAL
# ==========================================

# --- INICIO (DASHBOARD) ---
if opcion == "Inicio":
    st.title("🍎 Tablero Institucional 2026")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo Lectivo", "2026")
    c2.metric("Usuario Activo", st.session_state['user_name'])
    c3.metric("Rol", st.session_state['user_role'].upper())
    
    st.markdown("---")
    st.subheader("📅 Agenda de Actividades")
    
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.info("**ESTADO: PERIODO DE INSCRIPCIÓN**")
        st.write("- Recepción de documentos.")
        st.write("- Actualización de datos.")
    with col_der:
        st.success("**PRÓXIMO: INICIO DE CLASES**")
        st.metric("Fecha", "19 de Enero", "2026")
    
    cronograma = [
        {"Fecha": "02 Ene - 18 Ene", "Actividad": "Matrícula Extraordinaria", "Estado": "En Curso"},
        {"Fecha": "19 Ene", "Actividad": "Inauguración Año Escolar", "Estado": "Programado"},
        {"Fecha": "26 Ene", "Actividad": "Inicio de Clases (Oficial)", "Estado": "Programado"},
        {"Fecha": "30 Ene", "Actividad": "Entrega Planificaciones", "Estado": "Pendiente"}
    ]
    st.table(pd.DataFrame(cronograma))

# ==========================================
# MÓDULOS DE ADMINISTRADOR
# ==========================================
if st.session_state["user_role"] == "admin" and opcion != "Inicio":

    # --- 2. INSCRIPCIÓN ---
    if opcion == "Inscripción":
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
            c3, c4 = st.columns(2)
            fot = c3.file_uploader("Foto", ["jpg","png"])
            doc = c4.file_uploader("Docs", ["pdf","jpg"], accept_multiple_files=True)
            if st.form_submit_button("Guardar"):
                if nie and nom:
                    r = f"expedientes/{nie}"
                    urls = [subir_archivo(f, r) for f in (doc or [])]
                    db.collection("alumnos").document(nie).set({
                        "nie": nie, "nombre_completo": f"{nom} {ape}", "nombres": nom, "apellidos": ape,
                        "grado_actual": gra, "turno": tur, "estado": "Activo",
                        "encargado": {"nombre": enc, "telefono": tel, "direccion": dir},
                        "documentos": {"foto_url": subir_archivo(fot, r), "doc_urls": [u for u in urls if u]},
                        "fecha_registro": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Guardado")

    # --- 3. CONSULTA ALUMNOS ---
    elif opcion == "Consulta Alumnos":
        st.title("🔎 Consulta General")
        col_bus, _ = st.columns([1,2])
        n = col_bus.text_input("Buscar por NIE:")
        
        if col_bus.button("Buscar") and n:
            d = db.collection("alumnos").document(n).get()
            if d.exists: st.session_state.alum_view = d.to_dict()
            else: st.error("No encontrado")
        
        if "alum_view" in st.session_state:
            a = st.session_state.alum_view
            st.markdown("---")
            c1, c2 = st.columns([1,4])
            with c1: st.image(a.get('documentos',{}).get('foto_url', "https://via.placeholder.com/150"), width=120)
            with c2: 
                st.title(a['nombre_completo'])
                st.write(f"NIE: {a['nie']} | Grado: {a['grado_actual']}")
            
            t1, t2 = st.tabs(["Info General / Historial", "🖨️ Boleta de Notas"])
            
            with t1:
                st.info("Expediente digital, documentos y pagos.")
                # Aquí podrías poner botones para ver documentos si lo deseas
                docs = a.get('documentos',{}).get('doc_urls', [])
                if docs:
                    st.write("**Documentos Adjuntos:**")
                    for u in docs: st.markdown(f"- [Ver Documento]({u})")

            with t2:
                # BOLETA
                st.subheader(f"Boleta {datetime.now().year}")
                # Buscar Guía
                cg = db.collection("carga_academica").where("grado", "==", a['grado_actual']).where("es_guia", "==", True).stream()
                guia = "No asignado"
                for d in cg: guia = d.to_dict()['nombre_docente']
                
                notas = db.collection("notas").where("nie", "==", a['nie']).stream()
                nm = {}
                for doc in notas:
                    dd = doc.to_dict()
                    if dd['materia'] not in nm: nm[dd['materia']] = {}
                    nm[dd['materia']][dd['mes']] = dd['promedio_final']
                
                if not nm: st.warning("Sin notas registradas.")
                else:
                    filas = []
                    malla = MAPA_CURRICULAR.get(a['grado_actual'], [])
                    for mat in malla:
                        if mat in nm:
                            n = nm[mat]
                            t1 = redondear_mined((n.get("Febrero",0)+n.get("Marzo",0)+n.get("Abril",0))/3)
                            t2 = redondear_mined((n.get("Mayo",0)+n.get("Junio",0)+n.get("Julio",0))/3)
                            t3 = redondear_mined((n.get("Agosto",0)+n.get("Septiembre",0)+n.get("Octubre",0))/3)
                            fin = redondear_mined((t1+t2+t3)/3)
                            filas.append(f"<tr><td style='text-align:left'>{mat}</td><td>{n.get('Febrero','-')}</td><td>{n.get('Marzo','-')}</td><td>{n.get('Abril','-')}</td><td style='background:#eee'><b>{t1}</b></td><td>{n.get('Mayo','-')}</td><td>{n.get('Junio','-')}</td><td>{n.get('Julio','-')}</td><td style='background:#eee'><b>{t2}</b></td><td>{n.get('Agosto','-')}</td><td>{n.get('Septiembre','-')}</td><td>{n.get('Octubre','-')}</td><td style='background:#eee'><b>{t3}</b></td><td style='background:#333;color:white'><b>{fin}</b></td></tr>")
                    
                    logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="60">' if logo else ""
                    html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:20px'><h2>COLEGIO PROFA. BLANCA ELENA</h2><h4>INFORME DE NOTAS</h4></div></div><p><b>Alumno:</b> {a['nombre_completo']} | <b>Grado:</b> {a['grado_actual']} | <b>Guía:</b> {guia}</p><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#ddd;font-weight:bold;'><td>ASIGNATURA</td><td>F</td><td>M</td><td>A</td><td>T1</td><td>M</td><td>J</td><td>J</td><td>T2</td><td>A</td><td>S</td><td>O</td><td>T3</td><td>FIN</td></tr>{"".join(filas)}</table><br><br><div style='display:flex;justify-content:space-between;text-align:center;padding:0 50px;'><div style='border-top:1px solid black;width:30%'>Orientador</div><div style='border-top:1px solid black;width:30%'>Dirección</div></div></div>"""
                    components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

    # --- 4. MAESTROS ---
    elif opcion == "Maestros":
        st.title("👩‍🏫 Gestión Docente")
        t1, t2, t3 = st.tabs(["Registro", "Asignar Carga 2026", "Admin Cargas"])
        
        with t1:
            with st.form("reg"):
                cod = st.text_input("Código")
                nom = st.text_input("Nombre")
                if st.form_submit_button("Guardar"):
                    db.collection("maestros_perfil").add({"codigo": cod, "nombre": nom, "activo": True})
                    st.success("Docente guardado")

        with t2:
            docs = db.collection("maestros_perfil").stream()
            profs = {d.to_dict()['nombre']: d.id for d in docs}
            with st.form("asig"):
                p = st.selectbox("Docente", list(profs.keys()) if profs else [])
                g = st.selectbox("Grado", LISTA_GRADOS_TODO)
                
                # Carga dinámica
                materias_grado = MAPA_CURRICULAR.get(g, [])
                m = st.multiselect("Materias (Malla 2026)", materias_grado)
                
                guia = st.checkbox("¿Es Maestro Guía?")
                if st.form_submit_button("Asignar"):
                    db.collection("carga_academica").add({"id_docente": profs[p], "nombre_docente": p, "grado": g, "materias": m, "es_guia": guia})
                    st.success("Carga asignada")

        with t3:
            docs = db.collection("carga_academica").stream()
            data = [{"id": d.id, **d.to_dict()} for d in docs]
            if data:
                df = pd.DataFrame(data)
                if 'es_guia' not in df: df['es_guia'] = False
                st.dataframe(df[["nombre_docente", "grado", "materias", "es_guia"]], use_container_width=True)
                sel = st.selectbox("Borrar ID:", ["Select..."]+[d['id'] for d in data])
                if sel != "Select..." and st.button("Borrar"):
                    db.collection("carga_academica").document(sel).delete(); st.rerun()

    # --- 5. NOTAS (ADMIN) ---
    elif opcion == "Notas":
        st.title("📊 Admin Notas (Vista Global)")
        g = st.selectbox("Grado", ["Select..."] + LISTA_GRADOS_NOTAS)
        mat_pos = MAPA_CURRICULAR.get(g, []) if g != "Select..." else []
        m = st.selectbox("Materia", ["Select..."] + mat_pos)
        mes = st.selectbox("Mes", LISTA_MESES)
        
        if g != "Select..." and m != "Select...":
            docs = db.collection("alumnos").where("grado_actual", "==", g).stream()
            lista = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
            if not lista: st.warning("Sin alumnos")
            else:
                df = pd.DataFrame(lista).sort_values("Nombre")
                id_doc = f"{g}_{m}_{mes}".replace(" ","_")
                
                cols = ["Nota Conducta"] if m == "Conducta" else ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
                
                doc_ref = db.collection("notas_mensuales").document(id_doc).get()
                if doc_ref.exists:
                    dd = doc_ref.to_dict().get('detalles', {})
                    for c in cols: df[c] = df["NIE"].map(lambda x: dd.get(x, {}).get(c, 0.0))
                else:
                    for c in cols: df[c] = 0.0
                
                df["Promedio"] = 0.0
                
                cfg = {"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True, width="medium"), "Promedio": st.column_config.NumberColumn(disabled=True)}
                for c in cols: cfg[c] = st.column_config.NumberColumn(min_value=0, max_value=10, step=0.1)
                
                ed = st.data_editor(df, column_config=cfg, hide_index=True, use_container_width=True, key=id_doc)
                
                if st.button("Guardar (Admin)"):
                    batch = db.batch()
                    detalles = {}
                    for _, r in ed.iterrows():
                        if m == "Conducta": prom = r[cols[0]]
                        else: prom = (r[cols[0]]*0.25 + r[cols[1]]*0.25 + r[cols[2]]*0.1 + r[cols[3]]*0.1 + r[cols[4]]*0.3)
                        
                        detalles[r["NIE"]] = {c: r[c] for c in cols}
                        detalles[r["NIE"]]["Promedio"] = round(prom, 1)
                        ref = db.collection("notas").document(f"{r['NIE']}_{id_doc}")
                        batch.set(ref, {"nie": r["NIE"], "grado": g, "materia": m, "mes": mes, "promedio_final": round(prom, 1)})
                    
                    db.collection("notas_mensuales").document(id_doc).set({"grado": g, "materia": m, "mes": mes, "detalles": detalles})
                    batch.commit()
                    st.success("Guardado por Admin")

    # --- 6. FINANZAS ---
    elif opcion == "Finanzas":
        st.title("💰 Finanzas")
        if 'recibo' not in st.session_state: st.session_state.recibo = None
        
        if st.session_state.recibo:
            r = st.session_state.recibo
            col = "#2e7d32" if r['tipo'] == 'ingreso' else "#c62828"
            tit = "RECIBO INGRESO" if r['tipo'] == 'ingreso' else "COMPROBANTE EGRESO"
            img = get_base64("logo.png"); hi = f'<img src="{img}" height="60">' if img else ""
            
            st.markdown("""<style>@media print { body * { visibility: hidden; } .ticket, .ticket * { visibility: visible; } .ticket { position: absolute; left: 0; top: 0; width: 100%; } }</style>""", unsafe_allow_html=True)
            html = f"""<div class="ticket" style="font-family:Arial;border:1px solid #ccc;padding:20px;background:white;color:black;"><div style="background:{col};color:white;padding:15px;display:flex;justify-content:space-between;"><div style="display:flex;gap:10px;">{hi}<div><h3 style="margin:0;color:white;">COLEGIO BLANCA ELENA</h3></div></div><h4>{tit}</h4></div><div style="padding:20px;"><p><b>Fecha:</b> {r['fecha']}</p><p><b>Persona:</b> {r['persona']}</p><p><b>Concepto:</b> {r['desc']}</p><h1 style="text-align:right;color:{col};">${r['monto']:.2f}</h1></div></div>"""
            st.markdown(html, unsafe_allow_html=True)
            c1, c2 = st.columns([1,4])
            if c1.button("Cerrar"): st.session_state.recibo = None; st.rerun()
            with c2: components.html(f"""<script>function p(){{window.parent.print()}}</script><button onclick="p()" style="background:green;color:white;padding:10px;">🖨️ IMPRIMIR</button>""", height=60)
        else:
            t1, t2 = st.tabs(["Cobrar", "Pagar"])
            with t1:
                n = st.text_input("NIE:")
                if st.button("Buscar para Cobro") and n:
                    d = db.collection("alumnos").document(n).get()
                    if d.exists: st.session_state.pa = d.to_dict()
                if st.session_state.get("pa"):
                    with st.form("fc"):
                        st.info(f"Cobro a: {st.session_state.pa['nombre_completo']}")
                        con = st.text_input("Concepto")
                        mon = st.number_input("Monto", min_value=0.01)
                        if st.form_submit_button("Cobrar"):
                            data = {"tipo": "ingreso", "desc": con, "monto": mon, "persona": st.session_state.pa['nombre_completo'], "alumno_nie": n, "fecha": datetime.now().strftime("%d/%m/%Y")}
                            db.collection("finanzas").add(data)
                            st.session_state.recibo = data; st.session_state.pa = None; st.rerun()

    # --- 7. CONFIGURACIÓN ---
    elif opcion == "Configuración":
        st.header("⚙️ Configuración")
        st.warning("Zona administrativa.")

# ==========================================
# MÓDULOS DE DOCENTE
# ==========================================
elif st.session_state["user_role"] == "docente" and opcion != "Inicio":
    
    if opcion == "Mis Listados":
        st.title("🖨️ Imprimir Listas")
        g = st.selectbox("Grado:", LISTA_GRADOS_TODO)
        if st.button("Generar"):
            docs = db.collection("alumnos").where("grado_actual", "==", g).stream()
            lista = sorted([d.to_dict()['nombre_completo'] for d in docs])
            if not lista: st.warning("Sin alumnos")
            else:
                rows = "".join([f"<tr><td>{i+1}</td><td style='text-align:left'>{n}</td><td></td><td></td><td></td><td></td></tr>" for i, n in enumerate(lista)])
                img = get_base64("logo.png"); hi = f'<img src="{img}" height="50">' if img else ""
                html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:15px'><h3>COLEGIO PROFA. BLANCA ELENA</h3><h4>LISTADO DE ASISTENCIA - {g.upper()}</h4></div></div><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#eee;font-weight:bold;'><td width='5%'>No.</td><td width='40%'>NOMBRE</td><td width='10%'></td><td width='10%'></td><td width='10%'></td><td width='10%'></td><td width='10%'></td></tr>{rows}</table></div>"""
                components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

    elif opcion == "Cargar Notas":
        st.title("📝 Registro de Notas")
        g = st.selectbox("Grado", ["Select..."] + LISTA_GRADOS_NOTAS)
        
        mat_pos = MAPA_CURRICULAR.get(g, []) if g != "Select..." else []
        m = st.selectbox("Materia", ["Select..."] + mat_pos)
        mes = st.selectbox("Mes", LISTA_MESES)
        
        if g != "Select..." and m != "Select...":
            docs = db.collection("alumnos").where("grado_actual", "==", g).stream()
            lista = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
            
            if not lista: st.warning("Sin alumnos")
            else:
                df = pd.DataFrame(lista).sort_values("Nombre")
                id_doc = f"{g}_{m}_{mes}".replace(" ","_")
                
                cols = ["Nota Conducta"] if m == "Conducta" else ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
                
                doc_ref = db.collection("notas_mensuales").document(id_doc).get()
                if doc_ref.exists:
                    dd = doc_ref.to_dict().get('detalles', {})
                    for c in cols: df[c] = df["NIE"].map(lambda x: dd.get(x, {}).get(c, 0.0))
                else:
                    for c in cols: df[c] = 0.0
                
                df["Promedio"] = 0.0
                
                cfg = {"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True, width="medium"), "Promedio": st.column_config.NumberColumn(disabled=True)}
                for c in cols: cfg[c] = st.column_config.NumberColumn(min_value=0, max_value=10, step=0.1)
                
                ed = st.data_editor(df, column_config=cfg, hide_index=True, use_container_width=True, key=id_doc)
                
                if st.button("Guardar"):
                    batch = db.batch()
                    detalles = {}
                    for _, r in ed.iterrows():
                        if m == "Conducta": prom = r[cols[0]]
                        else: prom = (r[cols[0]]*0.25 + r[cols[1]]*0.25 + r[cols[2]]*0.1 + r[cols[3]]*0.1 + r[cols[4]]*0.3)
                        
                        detalles[r["NIE"]] = {c: r[c] for c in cols}
                        detalles[r["NIE"]]["Promedio"] = round(prom, 1)
                        
                        ref = db.collection("notas").document(f"{r['NIE']}_{id_doc}")
                        batch.set(ref, {"nie": r["NIE"], "grado": g, "materia": m, "mes": mes, "promedio_final": round(prom, 1)})
                    
                    db.collection("notas_mensuales").document(id_doc).set({"grado": g, "materia": m, "mes": mes, "detalles": detalles})
                    batch.commit()
                    st.success("Guardado")

    elif opcion == "Ver Mis Cargas":
        st.title("📋 Mi Carga Académica")
        st.info("Aquí podrá visualizar las asignaturas que tiene asignadas.")