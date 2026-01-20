import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime, date
import base64
import time
import os
import streamlit.components.v1 as components

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema de Gestión Escolar", layout="wide", page_icon="🎓")

# --- CONEXIÓN FIREBASE ---
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

# --- UTILIDADES ---
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

# --- LISTAS OFICIALES ---
GRADOS = ["Kinder 4", "Kinder 5", "Preparatoria", "Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
MATERIAS = ["Lenguaje", "Matemática", "Ciencia y Tecnología", "Estudios Sociales", "Inglés", "Moral, Urbanidad y Cívica", "Educación Física", "Educación Artística", "Informática", "Ortografía", "Caligrafía", "Conducta"]
MESES = ["Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre"]

# --- SIDEBAR ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.warning("Falta logo.png")
    st.markdown("---")
    opcion = st.radio("Menú:", ["Inicio", "Inscripción", "Maestros", "Consulta Alumnos", "Finanzas", "Notas", "Configuración"])
    st.markdown("---")
    if conexion_exitosa: st.success("🟢 Conectado")

# 1. INICIO
if opcion == "Inicio":
    st.title("🍎 Panel de Control")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo", "2026")
    c2.metric("Estado", "Activo")

# 2. INSCRIPCIÓN
elif opcion == "Inscripción":
    st.title("📝 Inscripción")
    with st.form("f1"):
        c1, c2 = st.columns(2)
        nie = c1.text_input("NIE*")
        nom = c1.text_input("Nombres*")
        ape = c1.text_input("Apellidos*")
        est = c1.selectbox("Estado", ["Activo", "Inactivo"])
        gra = c2.selectbox("Grado", GRADOS)
        tur = c2.selectbox("Turno", ["Matutino", "Vespertino"])
        enc = c2.text_input("Encargado")
        tel = c2.text_input("Teléfono")
        dir = st.text_area("Dirección")
        st.markdown("---")
        c3, c4 = st.columns(2)
        fot = c3.file_uploader("Foto", ["jpg","png"])
        doc = c4.file_uploader("Documentos", ["pdf","jpg"], accept_multiple_files=True)
        if st.form_submit_button("Guardar"):
            if nie and nom:
                ruta = f"expedientes/{nie}"
                urls = [subir_archivo(f, ruta) for f in (doc or [])]
                db.collection("alumnos").document(nie).set({
                    "nie": nie, "nombre_completo": f"{nom} {ape}", "nombres": nom, "apellidos": ape,
                    "grado_actual": gra, "turno": tur, "estado": est,
                    "encargado": {"nombre": enc, "telefono": tel, "direccion": dir},
                    "documentos": {"foto_url": subir_archivo(fot, ruta), "doc_urls": [u for u in urls if u]},
                    "fecha_registro": firestore.SERVER_TIMESTAMP
                })
                st.success("✅ Guardado")
            else: st.error("Faltan datos")

# 3. MAESTROS
elif opcion == "Maestros":
    st.title("👩‍🏫 Maestros")
    t1, t2, t3, t4 = st.tabs(["Registro", "Carga", "Admin Carga", "Ver Todo"])
    with t1:
        with st.form("fp"):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código")
            nom = c2.text_input("Nombre")
            tel = c1.text_input("Teléfono")
            tur = c2.selectbox("Turno", ["Matutino", "Vespertino", "Tiempo Completo"])
            if st.form_submit_button("Guardar") and nom:
                db.collection("maestros_perfil").add({"codigo": cod, "nombre": nom, "contacto": {"tel": tel}, "turno_base": tur})
                st.success("Listo")
    with t2:
        docs = db.collection("maestros_perfil").stream()
        profs = {f"{d.to_dict()['nombre']}": d.id for d in docs}
        with st.form("fc"):
            p = st.selectbox("Docente", list(profs.keys()) if profs else [])
            g = st.selectbox("Grado", GRADOS)
            m = st.multiselect("Materias", MATERIAS)
            if st.form_submit_button("Asignar") and m:
                db.collection("carga_academica").add({"id_docente": profs[p], "nombre_docente": p, "grado": g, "materias": m})
                st.success("Asignado")
    with t3:
        docs = db.collection("carga_academica").stream()
        data = [{"id": d.id, **d.to_dict()} for d in docs]
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df[["nombre_docente", "grado", "materias"]], use_container_width=True)
            sel = st.selectbox("Eliminar ID:", ["Select..."]+[d['id'] for d in data])
            if sel != "Select..." and st.button("Borrar"):
                db.collection("carga_academica").document(sel).delete(); st.rerun()
    with t4:
        docs = db.collection("maestros_perfil").stream()
        data = [d.to_dict() for d in docs]
        if data: st.dataframe(pd.DataFrame(data)[["codigo", "nombre", "turno_base"]], use_container_width=True)

# 4. CONSULTA ALUMNOS (RESTAURADA + BOLETA)
elif opcion == "Consulta Alumnos":
    st.title("🔎 Consulta")
    modo = st.radio("Buscar:", ["NIE", "Grado"], horizontal=True)
    alum = None
    if modo == "NIE":
        n = st.text_input("NIE:")
        if st.button("Buscar") and n:
            d = db.collection("alumnos").document(n).get()
            alum = d.to_dict() if d.exists else None
            if not alum: st.error("No existe")
    else:
        g = st.selectbox("Grado", ["Todos"]+GRADOS)
        q = db.collection("alumnos")
        if g != "Todos": q = q.where("grado_actual", "==", g)
        l = [d.to_dict() for d in q.stream()]
        sel = st.selectbox("Alumno", ["Select..."]+[f"{a['nie']} - {a['nombre_completo']}" for a in l])
        if sel != "Select...": alum = db.collection("alumnos").document(sel.split(" - ")[0]).get().to_dict()

    if alum:
        st.markdown("---")
        # DISEÑO LIMPIO ORIGINAL
        c1, c2 = st.columns([1, 4])
        with c1: st.image(alum.get('documentos',{}).get('foto_url', "https://via.placeholder.com/150"), width=120)
        with c2: 
            st.title(alum['nombre_completo'])
            st.markdown(f"**NIE:** {alum['nie']} | **Grado:** {alum['grado_actual']} | **Turno:** {alum.get('turno')}")
            st.caption(f"Responsable: {alum.get('encargado',{}).get('nombre')}")

        t1, t2, t3, t4 = st.tabs(["General", "Maestros", "Finanzas", "🖨️ Boleta de Notas"])
        
        with t1:
            st.write(f"**Dirección:** {alum.get('encargado',{}).get('direccion')}")
            st.write(f"**Teléfono:** {alum.get('encargado',{}).get('telefono')}")
            docs = alum.get('documentos',{}).get('doc_urls', [])
            if alum.get('documentos',{}).get('doc_url'): docs.append(alum.get('documentos',{}).get('doc_url')) # Compatibilidad
            if docs:
                st.success(f"{len(set(docs))} Documentos disponibles")
                for u in list(set(docs)): st.link_button("Ver Documento", u)
            else: st.info("Sin documentos")

        with t2:
            cargas = db.collection("carga_academica").where("grado", "==", alum['grado_actual']).stream()
            for c in cargas:
                d = c.to_dict()
                with st.container(border=True):
                    st.markdown(f"**{d['nombre_docente']}**")
                    st.caption(", ".join(d['materias']))

        with t3:
            pagos = db.collection("finanzas").where("alumno_nie", "==", alum['nie']).where("tipo", "==", "ingreso").stream()
            lp = [{"id":p.id, **p.to_dict()} for p in pagos]
            if lp:
                df = pd.DataFrame(lp).sort_values("fecha", ascending=False)
                if "observaciones" not in df: df["observaciones"] = ""
                st.dataframe(df[["fecha_legible", "descripcion", "monto", "observaciones"]], use_container_width=True)
                
                sel_p = st.selectbox("Reimprimir:", ["Select..."]+[f"{p['fecha_legible']} - ${p['monto']}" for p in lp])
                if sel_p != "Select...":
                    if st.button("Ver Recibo"):
                        p_obj = next(p for p in lp if f"{p['fecha_legible']} - ${p['monto']}" == sel_p)
                        st.session_state.recibo_temp = p_obj
                        st.switch_page("app.py") # Recarga para mostrar el recibo en modulo Finanzas si es necesario, o usa JS aqui
                        # Por simplicidad en este modulo "limpio", mostramos info basica
                        st.info("Para imprimir formato ticket oficial, vaya al módulo Finanzas.")
            else: st.info("Sin pagos")

        # --- AQUÍ ESTÁ LA BOLETA SOLICITADA ---
        with t4:
            st.subheader(f"Boleta de Calificaciones {datetime.now().year}")
            
            # 1. Recuperar notas
            notas_ref = db.collection("notas").where("nie", "==", alum['nie']).stream()
            notas_map = {}
            for doc in notas_ref:
                d = doc.to_dict()
                if d['materia'] not in notas_map: notas_map[d['materia']] = {}
                notas_map[d['materia']][d['mes']] = d['promedio_final']
            
            if not notas_map:
                st.warning("No hay notas registradas para este alumno.")
            else:
                filas = []
                for mat in MATERIAS:
                    if mat in notas_map:
                        n = notas_map[mat]
                        # Cálculo Trimestral (Si falta nota, asume 0)
                        t1 = (n.get("Febrero",0) + n.get("Marzo",0) + n.get("Abril",0)) / 3
                        t2 = (n.get("Mayo",0) + n.get("Junio",0) + n.get("Julio",0)) / 3
                        t3 = (n.get("Agosto",0) + n.get("Septiembre",0) + n.get("Octubre",0)) / 3
                        fin = (t1+t2+t3)/3
                        
                        filas.append({
                            "Materia": mat,
                            "Feb": n.get("Febrero", "-"), "Mar": n.get("Marzo", "-"), "Abr": n.get("Abril", "-"), "TI": round(t1,1),
                            "May": n.get("Mayo", "-"), "Jun": n.get("Junio", "-"), "Jul": n.get("Julio", "-"), "TII": round(t2,1),
                            "Ago": n.get("Agosto", "-"), "Sep": n.get("Septiembre", "-"), "Oct": n.get("Octubre", "-"), "TIII": round(t3,1),
                            "FINAL": round(fin,1)
                        })
                
                df_b = pd.DataFrame(filas)
                st.dataframe(df_b, use_container_width=True, hide_index=True)
                
                # HTML para impresión
                html_rows = ""
                for _, r in df_b.iterrows():
                    html_rows += f"<tr><td style='text-align:left'>{r['Materia']}</td><td>{r['Feb']}</td><td>{r['Mar']}</td><td>{r['Abr']}</td><td style='background:#eee'><b>{r['TI']}</b></td><td>{r['May']}</td><td>{r['Jun']}</td><td>{r['Jul']}</td><td style='background:#eee'><b>{r['TII']}</b></td><td>{r['Ago']}</td><td>{r['Sep']}</td><td>{r['Oct']}</td><td style='background:#eee'><b>{r['TIII']}</b></td><td style='background:#333;color:white'><b>{r['FINAL']}</b></td></tr>"
                
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

# 5. FINANZAS
elif opcion == "Finanzas":
    st.title("💰 Finanzas")
    if 'recibo_temp' not in st.session_state: st.session_state.recibo_temp = None
    
    if st.session_state.recibo_temp:
        r = st.session_state.recibo_temp
        col = "#2e7d32" if r['tipo'] == 'ingreso' else "#c62828"
        tit = "RECIBO INGRESO" if r['tipo'] == 'ingreso' else "COMPROBANTE EGRESO"
        img = get_image_base64("logo.png"); h_img = f'<img src="{img}" height="60">' if img else ""
        
        st.markdown("""<style>@media print { body * { visibility: hidden; } .ticket, .ticket * { visibility: visible; } .ticket { position: absolute; left: 0; top: 0; width: 100%; margin: 0; } }</style>""", unsafe_allow_html=True)
        
        html = f"""
        <div class="ticket" style="font-family:Arial; border:1px solid #ccc; padding:20px; color:black; background:white;">
            <div style="display:flex; justify-content:space-between; background:{col}; color:white; padding:15px;">
                <div style="display:flex; gap:10px;">{h_img}<div><h3 style="margin:0;color:white;">COLEGIO BLANCA ELENA</h3></div></div>
                <h4>{tit}</h4>
            </div>
            <div style="padding:20px;">
                <p><b>Fecha:</b> {r['fecha_legible']}</p>
                <p><b>Persona:</b> {r.get('nombre_persona')}</p>
                <p><b>Concepto:</b> {r['descripcion']}</p>
                <p><b>Detalle:</b> {r.get('observaciones','')}</p>
                <h1 style="text-align:right; color:{col};">${r['monto']:.2f}</h1>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        c1, c2 = st.columns([1,4])
        if c1.button("❌ Cerrar"): st.session_state.recibo_temp = None; st.rerun()
        with c2: components.html(f"""<script>function p(){{window.parent.print()}}</script><button onclick="p()" style="background:green;color:white;padding:10px;border:none;">🖨️ IMPRIMIR</button>""", height=50)
    
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
                    mes = st.selectbox("Mes", MESES)
                    mon = st.number_input("Monto", min_value=0.01)
                    obs = st.text_area("Detalle")
                    if st.form_submit_button("Cobrar"):
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

# 6. NOTAS (ARREGLADO - NO SE QUEDA EN BLANCO)
elif opcion == "Notas":
    st.title("📊 Notas")
    # Los de Kinder NO llevan notas, por eso usamos solo GRADOS 1-9
    GRADOS_NOTAS = ["Primer Grado", "Segundo Grado", "Tercer Grado", "Cuarto Grado", "Quinto Grado", "Sexto Grado", "Séptimo Grado", "Octavo Grado", "Noveno Grado"]
    
    c1, c2, c3 = st.columns(3)
    grado = c1.selectbox("Grado", ["Seleccionar..."] + GRADOS_NOTAS)
    materia = c2.selectbox("Materia", ["Seleccionar..."] + MATERIAS)
    mes = c3.selectbox("Mes", MESES)

    if grado != "Seleccionar..." and materia != "Seleccionar...":
        # 1. Obtener alumnos (Esto fallaba antes si no había coincidencias exactas)
        docs = db.collection("alumnos").where("grado_actual", "==", grado).stream()
        lista_alumnos = [{"NIE": d.to_dict()['nie'], "Nombre": d.to_dict()['nombre_completo']} for d in docs]
        
        if not lista_alumnos:
            st.warning(f"No se encontraron alumnos inscritos en {grado}.")
        else:
            df = pd.DataFrame(lista_alumnos).sort_values("Nombre")
            
            # 2. Cargar notas existentes si las hay
            id_doc = f"{grado}_{materia}_{mes}".replace(" ","_")
            doc_ref = db.collection("notas_mensuales").document(id_doc).get()
            
            # Columnas del Excel que enviaste (25, 25, 10, 10, 30)
            cols = ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
            
            if doc_ref.exists:
                datos_db = doc_ref.to_dict().get('detalles', {})
                for c in cols: df[c] = df["NIE"].map(lambda x: datos_db.get(x, {}).get(c, 0.0))
            else:
                for c in cols: df[c] = 0.0 # Inicializar en 0
            
            # 3. Editor de Datos (Excel Web)
            cfg = {"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True, width="medium")}
            for c in cols: cfg[c] = st.column_config.NumberColumn(min_value=0, max_value=10, step=0.1, format="%.1f")
            
            st.info("Ingrese las notas. El promedio se calcula al guardar.")
            edited = st.data_editor(df, column_config=cfg, hide_index=True, use_container_width=True, key=id_doc)
            
            if st.button("💾 Guardar Notas", type="primary"):
                batch = db.batch()
                detalles_grupo = {}
                
                for _, row in edited.iterrows():
                    # Cálculo según tu Excel
                    prom = (row[cols[0]]*0.25 + row[cols[1]]*0.25 + row[cols[2]]*0.10 + row[cols[3]]*0.10 + row[cols[4]]*0.30)
                    
                    detalles_grupo[row["NIE"]] = {c: row[c] for c in cols}
                    detalles_grupo[row["NIE"]]["Promedio"] = round(prom, 1)
                    
                    # Guardar individual (para la Boleta)
                    ref = db.collection("notas").document(f"{row['NIE']}_{id_doc}")
                    batch.set(ref, {
                        "nie": row["NIE"], "grado": grado, "materia": materia, "mes": mes,
                        "promedio_final": round(prom, 1)
                    })
                
                # Guardar grupal (para recargar este editor luego)
                db.collection("notas_mensuales").document(id_doc).set({
                    "grado": grado, "materia": materia, "mes": mes, "detalles": detalles_grupo
                })
                
                batch.commit()
                st.success("✅ Notas guardadas correctamente.")

# 7. CONFIG
elif opcion == "Configuración":
    st.header("⚙️ Configuración")
    with st.expander("Borrar Todo"):
        if st.button("Resetear") and st.text_input("Confirmar:") == "BORRAR":
            st.warning("Desactivado por seguridad")