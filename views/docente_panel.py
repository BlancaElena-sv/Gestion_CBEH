import time
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from firebase_admin import firestore

from config import CICLO_LECTIVO


def mostrar_panel_docente(
    opcion_seleccionada,
    db,
    lista_grados,
    lista_grados_notas,
    lista_meses,
    mapa_curricular,
    redondear_mined,
    get_base64,
    obtener_fecha_hoy,
    obtener_hora_actual,
):

    if opcion_seleccionada == "Mis Listados":
        st.title("🖨️ Imprimir Listas")
        g = st.selectbox("Grado:", lista_grados)
        mes_lista = st.selectbox("Mes:", lista_meses)
        if st.button("Generar Hoja de Control"):
            docs = (
                db.collection("alumnos")
                .where("grado_actual", "==", g)
                .where("estado", "==", "Activo")
                .stream()
            )
            lista = sorted([f"{d.to_dict().get('apellidos', '')} {d.to_dict().get('nombres', '')}" for d in docs])
            if not lista: st.warning("Sin alumnos")
            else:
                logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="50">' if logo else ""
                rows = ""
                for i, n in enumerate(lista):
                    rows += f"<tr><td>{i+1}</td><td style='text-align:left;padding-left:5px;'>{n}</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>"
                html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:15px'><h3>COLEGIO PROFA. BLANCA ELENA</h3><h4>CONTROL DE EVALUACIÓN - {mes_lista.upper()} - {g.upper()}</h4></div></div><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#eee;font-weight:bold;'><td width='5%'>No.</td><td width='40%'>NOMBRE</td><td width='8%'>ACT1</td><td width='8%'>ACT2</td><td width='8%'>ALT1</td><td width='8%'>ALT2</td><td width='8%'>EXAM</td><td width='10%'>PROM</td></tr>{rows}</table></div>"""
                components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR LISTADO</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)

    elif opcion_seleccionada == "Tomar Asistencia":
        st.title("📅 Control de Asistencia")
        c1, c2 = st.columns(2)
        fecha_asist = c1.date_input("Fecha:", obtener_fecha_hoy())
        grado_asist = c2.selectbox("Grado:", lista_grados)
        if grado_asist:
            id_asistencia = ( f"{CICLO_LECTIVO}_{fecha_asist}_{grado_asist}")
            doc_ref = db.collection("asistencia").document(id_asistencia)
            doc_snap = doc_ref.get()
            alumnos_ref = (
                db.collection("alumnos")
                .where("grado_actual", "==", grado_asist)
                .where("estado", "==", "Activo")
                .stream()
            )    
            lista_alumnos = [{"NIE": d.to_dict()['nie'], "Nombre": f"{d.to_dict().get('apellidos', '')} {d.to_dict().get('nombres', '')}"} for d in alumnos_ref]
            lista_alumnos.sort(key=lambda x: x["Nombre"])
            if lista_alumnos:
                datos = doc_snap.to_dict().get("registros", {}) if doc_snap.exists else {}
                observaciones = doc_snap.to_dict().get("observaciones", {}) if doc_snap.exists else {}
                data_editor = []
                for alum in lista_alumnos:
                    data_editor.append({"NIE": alum["NIE"], "Nombre": alum["Nombre"], "Estado": datos.get(alum["NIE"], "Presente"), "Observación": observaciones.get(alum["NIE"], "")})
                df_asist = pd.DataFrame(data_editor)
                ed = st.data_editor(df_asist, column_config={"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True), "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente", "Tardanza", "Permiso"], required=True), "Observación": st.column_config.TextColumn(width="medium")}, hide_index=True, use_container_width=True, key=id_asistencia)
                if st.button("💾 Guardar Asistencia"):
                    regs = {r["NIE"]: r["Estado"] for r in ed.to_dict(orient="records")}
                    obs_regs = {r["NIE"]: r["Observación"] for r in ed.to_dict(orient="records")}
                    doc_ref.set({"fecha": datetime.combine(fecha_asist, datetime.min.time()), "ciclo_lectivo": CICLO_LECTIVO, "grado": grado_asist, "registros": regs, "observaciones": obs_regs})
                    st.success("Guardado.")
            else: st.warning("Sin alumnos.")

    elif opcion_seleccionada == "Cargar Notas":
        st.title("📝 Registro de Notas")
        c1, c2, c3 = st.columns(3)
        g = c1.selectbox("Grado", ["Select..."]+lista_grados_notas)
        mp = mapa_curricular.get(g,[]) if g!="Select..." else []
        m = c2.selectbox("Materia", ["Select..."]+mp)
        mes = c3.selectbox("Mes", lista_meses)
        if g!="Select..." and m!="Select...":
            docs = (
                db.collection("alumnos")
                .where("grado_actual", "==", g)
                .where("estado", "==", "Activo")
                .stream()
            )
            lista = [{"NIE": d.to_dict()['nie'], "Nombre": f"{d.to_dict().get('apellidos', '')} {d.to_dict().get('nombres', '')}"} for d in docs]
            if not lista: st.warning("Sin alumnos")
            else:
                df = pd.DataFrame(lista).sort_values("Nombre")
                id_doc = (f"{CICLO_LECTIVO}_{g}_{m}_{mes}".replace(" ","_"))
                cols = ["Nota Conducta"] if m == "Conducta" else ["Act1 (25%)", "Act2 (25%)", "Alt1 (10%)", "Alt2 (10%)", "Examen (30%)"]
                doc_ref = db.collection("notas_mensuales").document(id_doc).get()
                if doc_ref.exists:
                    dd = doc_ref.to_dict().get('detalles', {})
                    for c in cols: df[c] = df["NIE"].map(lambda x: dd.get(x, {}).get(c, 0.0))
                else:
                    for c in cols: df[c] = 0.0
                df["Promedio"] = 0.0
                cfg = {"NIE": st.column_config.TextColumn(disabled=True), "Nombre": st.column_config.TextColumn(disabled=True, width="medium"), "Promedio": st.column_config.NumberColumn(disabled=True)}
                for c in cols: cfg[c] = st.column_config.NumberColumn(min_value=0.0, max_value=10.0, step=0.01)
                if m == "Conducta": df["Promedio"] = df[cols[0]]
                else: df["Promedio"] = (df["Act1 (25%)"]*0.25 + df["Act2 (25%)"]*0.25 + df["Alt1 (10%)"]*0.10 + df["Alt2 (10%)"]*0.10 + df["Examen (30%)"]*0.30).apply(redondear_mined)
                ed = st.data_editor(df, column_config=cfg, hide_index=True, use_container_width=True, key=id_doc)
                if st.button("Guardar"):
                    batch = db.batch()
                    detalles = {}
                    for _, r in ed.iterrows():
                        if m == "Conducta": prom = r[cols[0]]
                        else: prom = (r[cols[0]]*0.25 + r[cols[1]]*0.25 + r[cols[2]]*0.1 + r[cols[3]]*0.1 + r[cols[4]]*0.3)
                        prom_r = redondear_mined(prom)
                        detalles[r["NIE"]] = {c: r[c] for c in cols}
                        detalles[r["NIE"]]["Promedio"] = prom_r
                        ref = db.collection("notas").document(f"{r['NIE']}_{id_doc}")
                        batch.set(ref, {"nie": r["NIE"], "grado": g, "materia": m, "mes": mes, "promedio_final": prom_r,"ciclo_lectivo": CICLO_LECTIVO })
                    db.collection("notas_mensuales").document(id_doc).set({"ciclo_lectivo": CICLO_LECTIVO, "grado": g, "materia": m, "mes": mes, "detalles": detalles})
                    batch.commit()
                    st.success("Guardado"); time.sleep(1); st.rerun()

    elif opcion_seleccionada == "Ver Mis Cargas":
        st.title("📋 Mi Carga Académica")
        cargas = db.collection("carga_academica").where("nombre_docente", "==", st.session_state["user_name"]).stream()
        found = False
        for c in cargas:
            found = True
            d = c.to_dict()
            with st.container(border=True):
                st.subheader(d['grado'])
                st.write("**Materias:** " + ", ".join(d['materias']))
                if d.get('es_guia'): st.success("🌟 MAESTRO GUÍA")
        if not found: st.info("No se encontraron cargas asignadas a su nombre exacto. Contacte a Dirección.")

    elif opcion_seleccionada == "Expediente Alumnos":
        st.title("📂 Bitácora del Alumno")
        c1, c2 = st.columns(2)
        grado_sel = c1.selectbox("Seleccionar Grado", lista_grados)
        alumnos_grado = (
            db.collection("alumnos")
            .where("grado_actual", "==", grado_sel)
            .where("estado", "==", "Activo")
            .stream()
        )
        dict_alumnos = {f"{a.to_dict().get('apellidos', '')} {a.to_dict().get('nombres', '')}": a.to_dict() for a in alumnos_grado}
        if dict_alumnos:
            nombre_alum = c2.selectbox("Seleccionar Alumno", ["Seleccionar..."] + sorted(list(dict_alumnos.keys())))
            if nombre_alum != "Seleccionar...":
                alum_data = dict_alumnos[nombre_alum]
                nie_actual = alum_data['nie']
                st.markdown("---")
                cp1, cp2 = st.columns([1, 4])
                with cp1:
                    foto_url_alum = (
                        alum_data.get("documentos", {})
                        .get("foto_url")
                    )

                    if foto_url_alum:
                        try:
                            st.image(
                                foto_url_alum,
                                width=130
                            )
                        except Exception:
                            st.markdown(
                                """
                                <div style="
                                    width:130px;
                                    height:130px;
                                    border-radius:50%;
                                    background:#e9edf5;
                                    display:flex;
                                    align-items:center;
                                    justify-content:center;
                                    font-size:55px;
                                    margin:auto;
                                ">
                                    👤
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            """
                            <div style="
                                width:130px;
                                height:130px;
                                border-radius:50%;
                                background:#e9edf5;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                font-size:55px;
                                margin:auto;
                            ">
                                👤
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                with cp2:
                    st.subheader(f"{alum_data.get('apellidos', '')} {alum_data.get('nombres', '')}")
                    st.write(f"**NIE:** {alum_data['nie']} | **Responsable:** {alum_data.get('encargado',{}).get('nombre','-')}")
                    st.write(f"**Tel:** {alum_data.get('encargado',{}).get('telefono','-')}")
                st.divider()
                st.markdown("### 📝 Historial de Observaciones")
                with st.expander("➕ Agregar Nueva Nota / Observación", expanded=True):
                    with st.form("form_bitacora"):
                        nota_texto = st.text_area("Escriba la observación:")
                        if st.form_submit_button("Guardar en Bitácora"):
                            if nota_texto:
                                nueva_entrada = {"nie": nie_actual, "alumno": nombre_alum, "grado": grado_sel, "fecha": firestore.SERVER_TIMESTAMP, "fecha_legible": obtener_hora_actual(), "autor": st.session_state["user_name"], "contenido": nota_texto}
                                db.collection("bitacora").add(nueva_entrada)
                                st.success("Nota agregada."); time.sleep(1); st.rerun()
                            else: st.warning("La nota no puede estar vacía.")
                logs = db.collection("bitacora").where("nie", "==", nie_actual).stream()
                lista_logs = [l.to_dict() for l in logs]
                lista_logs.sort(key=lambda x: x.get('fecha_legible', ''), reverse=True)
                if lista_logs:
                    for log in lista_logs:
                        with st.container(border=True):
                            c_meta, c_body = st.columns([1, 3])
                            with c_meta:
                                st.caption(f"📅 {log.get('fecha_legible')}")
                                st.caption(f"✍️ **{log.get('autor')}**")
                            with c_body: st.write(log.get('contenido'))
                else: st.info("No hay registros en la bitácora de este alumno.")
        else: c2.warning("No hay alumnos inscritos en este grado.")

    # AÑADIDO: MÓDULO DE BOLETAS PARA DOCENTES
    elif opcion_seleccionada == "Boletas de Notas":
        st.title("🖨️ Impresión de Boletas de Notas")
        c1, c2 = st.columns(2)
        grado_sel = c1.selectbox("Seleccionar Grado", lista_grados)
        alumnos_grado = (
            db.collection("alumnos")
            .where("grado_actual", "==", grado_sel)
            .where("estado", "==", "Activo")
            .stream()
        )
        dict_alumnos = {f"{a.to_dict().get('apellidos', '')} {a.to_dict().get('nombres', '')}": a.to_dict() for a in alumnos_grado}
        
        if dict_alumnos:
            nombre_alum = c2.selectbox("Seleccionar Alumno", ["Seleccionar..."] + sorted(list(dict_alumnos.keys())))
            if nombre_alum != "Seleccionar...":
                alum_data = dict_alumnos[nombre_alum]
                malla_completa = mapa_curricular.get(grado_sel, [])
                
                st.markdown("---")
                st.subheader("Configuración de Boleta")
                st.info("Puede eliminar de la lista las materias que aún no desea que aparezcan en el reporte impreso.")
                materias_seleccionadas = st.multiselect("Seleccione las materias a incluir en la boleta:", malla_completa, default=malla_completa)
                
                if st.button("Generar Boleta") and materias_seleccionadas:
                    # Obtener al guía del grado
                    q_guia = db.collection("carga_academica").where("grado", "==", grado_sel).where("es_guia", "==", True).stream()
                    maestro_guia = "No Asignado"
                    for d in q_guia: maestro_guia = d.to_dict()['nombre_docente']

                    # Obtener notas del alumno
                    notas = db.collection("notas").where("nie", "==", alum_data['nie']).stream()
                    nm = {}
                    for doc in notas:
                        dd = doc.to_dict()
                        if dd['materia'] not in nm: nm[dd['materia']] = {}
                        nm[dd['materia']][dd['mes']] = dd['promedio_final']
                    
                    filas = []
                    for mat in materias_seleccionadas:
                        if mat in nm:
                            n = nm[mat]
                            t1 = redondear_mined((n.get("Febrero",0)+n.get("Marzo",0)+n.get("Abril",0))/3)
                            t2 = redondear_mined((n.get("Mayo",0)+n.get("Junio",0)+n.get("Julio",0))/3)
                            t3 = redondear_mined((n.get("Agosto",0)+n.get("Septiembre",0)+n.get("Octubre",0))/3)
                            fin = redondear_mined((t1+t2+t3)/3)
                            filas.append(f"<tr><td style='text-align:left'>{mat}</td><td>{n.get('Febrero','-')}</td><td>{n.get('Marzo','-')}</td><td>{n.get('Abril','-')}</td><td style='background:#eee'><b>{t1}</b></td><td>{n.get('Mayo','-')}</td><td>{n.get('Junio','-')}</td><td>{n.get('Julio','-')}</td><td style='background:#eee'><b>{t2}</b></td><td>{n.get('Agosto','-')}</td><td>{n.get('Septiembre','-')}</td><td>{n.get('Octubre','-')}</td><td style='background:#eee'><b>{t3}</b></td><td style='background:#333;color:white'><b>{fin}</b></td></tr>")
                        else:
                            # Si no hay notas registradas para esa materia todavía
                            filas.append(f"<tr><td style='text-align:left'>{mat}</td><td>-</td><td>-</td><td>-</td><td style='background:#eee'><b>0.0</b></td><td>-</td><td>-</td><td>-</td><td style='background:#eee'><b>0.0</b></td><td>-</td><td>-</td><td>-</td><td style='background:#eee'><b>0.0</b></td><td style='background:#333;color:white'><b>0.0</b></td></tr>")

                    logo = get_base64("logo.png"); hi = f'<img src="{logo}" height="60">' if logo else ""
                    sello = get_base64("sello.png"); hs = f'<img src="{sello}" height="80">' if sello else ""
                    html = f"""<div style='font-family:Arial;font-size:12px;padding:20px;'><div style='display:flex;align-items:center;border-bottom:2px solid black;margin-bottom:10px;'>{hi}<div style='margin-left:20px'><h2>COLEGIO PROFA. BLANCA ELENA</h2><h4>INFORME DE NOTAS</h4></div></div><p><b>Alumno:</b> {nombre_alum} | <b>Grado:</b> {grado_sel} | <b>Guía:</b> {maestro_guia}</p><table border='1' style='width:100%;border-collapse:collapse;text-align:center;'><tr style='background:#ddd;font-weight:bold;'><td>ASIGNATURA</td><td>F</td><td>M</td><td>A</td><td>T1</td><td>M</td><td>J</td><td>J</td><td>T2</td><td>A</td><td>S</td><td>O</td><td>T3</td><td>FIN</td></tr>{"".join(filas)}</table><br><br><br><div style='display:flex;justify-content:space-between;align-items:end;padding:0 50px;'><div style='text-align:center;width:30%'><div style='border-top:1px solid black;width:100%'>Orientador</div></div><div style='text-align:center;'>{hs}</div><div style='text-align:center;width:30%'><div style='border-top:1px solid black;width:100%'>Dirección</div></div></div></div>"""
                    components.html(f"""<html><body>{html}<br><button onclick="window.print()">🖨️ IMPRIMIR BOLETA</button><style>@media print{{button{{display:none;}}}}</style></body></html>""", height=600, scrolling=True)
        else:
            c2.warning("No hay alumnos inscritos en este grado.")