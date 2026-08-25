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

        st.info(
            f"📅 Ciclo lectivo activo: {CICLO_LECTIVO}"
        )
        st.caption(
            "Las calificaciones académicas aplican únicamente "
            "de Primero a Noveno Grado."
        )

        c1, c2, c3 = st.columns(3)

        grado = c1.selectbox(
            "Grado",
            ["Select..."] + lista_grados_notas,
            key="doc_notas_grado",
        )

        materias = (
            mapa_curricular.get(grado, [])
            if grado != "Select..."
            else []
        )

        materia = c2.selectbox(
            "Materia",
            ["Select..."] + materias,
            key="doc_notas_materia",
        )

        mes = c3.selectbox(
            "Mes",
            lista_meses,
            key="doc_notas_mes",
        )

        if grado == "Select..." or materia == "Select...":
            return

        # ======================================================
        # ALUMNOS ACTIVOS DEL GRADO Y CICLO ACTUAL
        # ======================================================
        alumnos_docs = (
            db.collection("alumnos")
            .where("grado_actual", "==", grado)
            .where("estado", "==", "Activo")
            .stream()
        )

        alumnos = []

        for documento in alumnos_docs:
            datos = documento.to_dict()

            ciclo_alumno = datos.get("ciclo_lectivo", CICLO_LECTIVO)
            try:
                ciclo_alumno = int(ciclo_alumno)
            except (TypeError, ValueError):
                pass

            if ciclo_alumno != CICLO_LECTIVO:
                continue

            nie = str(datos.get("nie", documento.id)).strip()
            nombre = (
                f"{datos.get('apellidos', '')} "
                f"{datos.get('nombres', '')}"
            ).strip()

            alumnos.append({"NIE": nie, "Nombre": nombre})

        if not alumnos:
            st.warning(
                "No hay alumnos activos para este grado "
                "en el ciclo actual."
            )
            return

        df = pd.DataFrame(alumnos).sort_values("Nombre")

        # ======================================================
        # IDENTIFICADORES NUEVO Y LEGACY
        # ======================================================
        id_base = f"{grado}_{materia}_{mes}".replace(" ", "_")
        id_nuevo = f"{CICLO_LECTIVO}_{id_base}"
        id_legacy = id_base

        doc_nuevo = (
            db.collection("notas_mensuales")
            .document(id_nuevo)
            .get()
        )

        doc_legacy = None
        if CICLO_LECTIVO == 2026:
            doc_legacy = (
                db.collection("notas_mensuales")
                .document(id_legacy)
                .get()
            )

        detalles_nuevos = {}
        if doc_nuevo.exists:
            detalles_nuevos = doc_nuevo.to_dict().get("detalles", {}) or {}

        detalles_legacy = {}
        if doc_legacy is not None and doc_legacy.exists:
            detalles_legacy = doc_legacy.to_dict().get("detalles", {}) or {}

        # Firestore puede conservar NIE como string o número.
        # Normalizamos todas las claves a texto para que coincidan
        # con la columna NIE del DataFrame.
        def normalizar_detalles(detalles):
            resultado = {}
            for clave, valor in detalles.items():
                resultado[str(clave).strip()] = (
                    valor if isinstance(valor, dict) else {}
                )
            return resultado

        detalles_nuevos = normalizar_detalles(detalles_nuevos)
        detalles_legacy = normalizar_detalles(detalles_legacy)

        def tiene_contenido(detalles):
            return bool(detalles)

        def tiene_notas_reales(detalles):
            for datos_alumno in detalles.values():
                if not isinstance(datos_alumno, dict):
                    continue
                for clave, valor in datos_alumno.items():
                    if clave == "Promedio":
                        continue
                    try:
                        if float(valor) != 0:
                            return True
                    except (TypeError, ValueError):
                        continue
            return False

        # Prioridad:
        # 1) nuevo con notas reales
        # 2) legacy con notas reales
        # 3) nuevo con cualquier contenido
        # 4) legacy con cualquier contenido
        # 5) documento nuevo vacío
        if tiene_notas_reales(detalles_nuevos):
            id_origen = id_nuevo
            detalles = detalles_nuevos
        elif tiene_notas_reales(detalles_legacy):
            id_origen = id_legacy
            detalles = detalles_legacy
            st.caption("ℹ️ Se cargaron calificaciones históricas de 2026.")
        elif tiene_contenido(detalles_nuevos):
            id_origen = id_nuevo
            detalles = detalles_nuevos
        elif tiene_contenido(detalles_legacy):
            id_origen = id_legacy
            detalles = detalles_legacy
            st.caption("ℹ️ Se cargó el registro histórico de 2026.")
        else:
            id_origen = id_nuevo
            detalles = {}

        # ======================================================
        # COLUMNAS DE CALIFICACIÓN
        # ======================================================
        if materia == "Conducta":
            columnas_notas = ["Nota Conducta"]
        else:
            columnas_notas = [
                "Act1 (25%)",
                "Act2 (25%)",
                "Alt1 (10%)",
                "Alt2 (10%)",
                "Examen (30%)",
            ]

        # ======================================================
        # CARGAR VALORES EXISTENTES
        # ======================================================
        for columna in columnas_notas:
            df[columna] = df["NIE"].map(
                lambda nie, c=columna: detalles.get(
                    str(nie).strip(), {}
                ).get(c, 0.0)
            )

        # Si el documento mensual no contiene detalles, intentamos
        # al menos recuperar los promedios individuales guardados
        # en la colección "notas". Esto no reconstruye actividades,
        # pero evita mostrar como inexistente una nota ya registrada.
        if not detalles:
            notas_individuales = (
                db.collection("notas")
                .where("grado", "==", grado)
                .stream()
            )

            promedios_guardados = {}
            for documento in notas_individuales:
                nota = documento.to_dict()

                ciclo_nota = nota.get("ciclo_lectivo", 2026)
                try:
                    ciclo_nota = int(ciclo_nota)
                except (TypeError, ValueError):
                    pass

                if ciclo_nota != CICLO_LECTIVO:
                    continue
                if nota.get("materia") != materia:
                    continue
                if nota.get("mes") != mes:
                    continue

                nie_nota = str(nota.get("nie", "")).strip()
                if nie_nota:
                    promedios_guardados[nie_nota] = nota.get(
                        "promedio_final", 0.0
                    )

            if promedios_guardados:
                df["Promedio"] = df["NIE"].map(
                    lambda nie: promedios_guardados.get(
                        str(nie).strip(), 0.0
                    )
                )
                st.warning(
                    "Se encontraron promedios guardados, pero no el detalle "
                    "de actividades de este mes. Las actividades aparecen en 0."
                )

        # ======================================================
        # PROMEDIO
        # ======================================================
        if "Promedio" not in df.columns:
            if materia == "Conducta":
                df["Promedio"] = df["Nota Conducta"]
            else:
                df["Promedio"] = (
                    df["Act1 (25%)"] * 0.25
                    + df["Act2 (25%)"] * 0.25
                    + df["Alt1 (10%)"] * 0.10
                    + df["Alt2 (10%)"] * 0.10
                    + df["Examen (30%)"] * 0.30
                ).apply(redondear_mined)

        # ======================================================
        # EDITOR
        # ======================================================
        config_columnas = {
            "NIE": st.column_config.TextColumn(disabled=True),
            "Nombre": st.column_config.TextColumn(
                disabled=True,
                width="medium",
            ),
            "Promedio": st.column_config.NumberColumn(disabled=True),
        }

        for columna in columnas_notas:
            config_columnas[columna] = st.column_config.NumberColumn(
                min_value=0.0,
                max_value=10.0,
                step=0.01,
            )

        editor = st.data_editor(
            df,
            column_config=config_columnas,
            hide_index=True,
            width="stretch",
            key=f"doc_editor_{CICLO_LECTIVO}_{grado}_{materia}_{mes}",
        )

        st.caption(f"Registro leído desde: {id_origen}")

        # ======================================================
        # GUARDAR SIEMPRE EN FORMATO CANÓNICO CON CICLO
        # ======================================================
        if st.button(
            "💾 Guardar Notas",
            type="primary",
            key="doc_guardar_notas",
        ):
            batch = db.batch()
            detalles_guardar = {}

            for _, fila in editor.iterrows():
                if materia == "Conducta":
                    promedio = fila["Nota Conducta"]
                else:
                    promedio = (
                        fila["Act1 (25%)"] * 0.25
                        + fila["Act2 (25%)"] * 0.25
                        + fila["Alt1 (10%)"] * 0.10
                        + fila["Alt2 (10%)"] * 0.10
                        + fila["Examen (30%)"] * 0.30
                    )

                promedio_final = redondear_mined(promedio)
                nie = str(fila["NIE"]).strip()

                detalles_guardar[nie] = {
                    columna: float(fila[columna])
                    for columna in columnas_notas
                }
                detalles_guardar[nie]["Promedio"] = promedio_final

                ref_nota = (
                    db.collection("notas")
                    .document(f"{nie}_{id_nuevo}")
                )

                batch.set(
                    ref_nota,
                    {
                        "nie": nie,
                        "ciclo_lectivo": CICLO_LECTIVO,
                        "grado": grado,
                        "materia": materia,
                        "mes": mes,
                        "promedio_final": promedio_final,
                    },
                )

            db.collection("notas_mensuales").document(id_nuevo).set(
                {
                    "ciclo_lectivo": CICLO_LECTIVO,
                    "grado": grado,
                    "materia": materia,
                    "mes": mes,
                    "detalles": detalles_guardar,
                }
            )

            batch.commit()

            st.success("✅ Notas guardadas correctamente.")
            time.sleep(1)
            st.rerun()

    elif opcion_seleccionada == "Ver Mis Cargas":
        st.title("📋 Mi Carga Académica")
        cargas = (
            db.collection("carga_academica")
            .where(
                "nombre_docente",
                "==",
                st.session_state["user_name"]
            )
            .stream()
        )

        found = False
        for c in cargas:
            d = c.to_dict()
            ciclo_carga = d.get("ciclo_lectivo", 2026)

            try:
                ciclo_carga = int(ciclo_carga)
            except (TypeError, ValueError):
                pass

            if ciclo_carga != CICLO_LECTIVO:
                continue

            found = True
            with st.container(border=True):
                st.subheader(d["grado"])
                st.write("**Materias:** " + ", ".join(d.get("materias", [])))
                st.caption(f"📅 Ciclo lectivo: {CICLO_LECTIVO}")
                if d.get("es_guia"):
                    st.success("🌟 MAESTRO GUÍA")

        if not found:
            st.info(
                f"No se encontraron cargas asignadas para el ciclo {CICLO_LECTIVO}."
            )

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

        st.caption(
            f"📅 Ciclo lectivo actual: {CICLO_LECTIVO} · "
            "Boletas disponibles únicamente para alumnos de Primero a Noveno Grado."
        )

        c1, c2 = st.columns(2)

        grado_sel = c1.selectbox(
            "Seleccionar Grado",
            lista_grados_notas
        )

        alumnos_docs = (
            db.collection("alumnos")
            .where(
                "grado_actual",
                "==",
                grado_sel
            )
            .where(
                "estado",
                "==",
                "Activo"
            )
            .stream()
        )

        dict_alumnos = {}

        for documento in alumnos_docs:

            datos = documento.to_dict()

            ciclo_alumno = datos.get(
                "ciclo_lectivo",
                CICLO_LECTIVO
            )

            try:
                ciclo_alumno = int(
                    ciclo_alumno
                )
            except (TypeError, ValueError):
                pass

            if ciclo_alumno != CICLO_LECTIVO:
                continue

            nombre = (
                f"{datos.get('apellidos', '')} "
                f"{datos.get('nombres', '')}"
            ).strip()

            dict_alumnos[nombre] = datos

        if not dict_alumnos:

            c2.warning(
                "No hay alumnos activos "
                "en este grado para el ciclo actual."
            )

            return

        nombre_alum = c2.selectbox(
            "Seleccionar Alumno",
            ["Seleccionar..."]
            + sorted(
                dict_alumnos.keys()
            )
        )

        if nombre_alum == "Seleccionar...":
            return

        alum_data = dict_alumnos[
            nombre_alum
        ]

        malla_completa = (
            mapa_curricular.get(
                grado_sel,
                []
            )
        )

        st.markdown("---")

        st.subheader(
            "Configuración de Boleta"
        )

        st.info(
            "Puede eliminar de la lista las materias "
            "que aún no desea que aparezcan "
            "en el reporte impreso."
        )

        materias_seleccionadas = (
            st.multiselect(
                "Seleccione las materias "
                "a incluir en la boleta:",
                malla_completa,
                default=malla_completa
            )
        )

        if not (
            st.button("Generar Boleta")
            and materias_seleccionadas
        ):
            return

        # ==========================================
        # MAESTRO GUÍA DEL CICLO ACTUAL
        # ==========================================

        q_guia = (
            db.collection(
                "carga_academica"
            )
            .where(
                "grado",
                "==",
                grado_sel
            )
            .where(
                "es_guia",
                "==",
                True
            )
            .stream()
        )

        maestro_guia = "No Asignado"

        for documento in q_guia:

            datos_guia = (
                documento.to_dict()
            )

            ciclo_guia = datos_guia.get(
                "ciclo_lectivo",
                2026
            )

            try:
                ciclo_guia = int(
                    ciclo_guia
                )
            except (TypeError, ValueError):
                pass

            if ciclo_guia != CICLO_LECTIVO:
                continue

            maestro_guia = (
                datos_guia.get(
                    "nombre_docente",
                    "No Asignado"
                )
            )

            break

        # ==========================================
        # NOTAS DEL ALUMNO - CICLO ACTUAL
        # ==========================================

        notas_docs = (
            db.collection("notas")
            .where(
                "nie",
                "==",
                alum_data["nie"]
            )
            .stream()
        )

        nm = {}

        for documento in notas_docs:

            dd = documento.to_dict()

            ciclo_nota = dd.get(
                "ciclo_lectivo",
                2026
            )

            try:
                ciclo_nota = int(
                    ciclo_nota
                )
            except (TypeError, ValueError):
                pass

            # Solamente ciclo actual
            if ciclo_nota != CICLO_LECTIVO:
                continue

            # Solamente grado actual
            if (
                dd.get("grado")
                != grado_sel
            ):
                continue

            materia = dd.get(
                "materia"
            )

            mes = dd.get(
                "mes"
            )

            if not materia or not mes:
                continue

            nm.setdefault(
                materia,
                {}
            )

            nm[materia][mes] = (
                dd.get(
                    "promedio_final",
                    0
                )
            )

        # ==========================================
        # GENERAR FILAS
        # ==========================================

        filas = []

        for mat in materias_seleccionadas:

            if mat in nm:

                n = nm[mat]

                t1 = redondear_mined(
                    (
                        n.get("Febrero", 0)
                        + n.get("Marzo", 0)
                        + n.get("Abril", 0)
                    ) / 3
                )

                t2 = redondear_mined(
                    (
                        n.get("Mayo", 0)
                        + n.get("Junio", 0)
                        + n.get("Julio", 0)
                    ) / 3
                )

                t3 = redondear_mined(
                    (
                        n.get("Agosto", 0)
                        + n.get("Septiembre", 0)
                        + n.get("Octubre", 0)
                    ) / 3
                )

                fin = redondear_mined(
                    (t1 + t2 + t3) / 3
                )

                filas.append(
                    f"""
                    <tr>

                        <td style='text-align:left'>
                            {mat}
                        </td>

                        <td>{n.get('Febrero', '-')}</td>
                        <td>{n.get('Marzo', '-')}</td>
                        <td>{n.get('Abril', '-')}</td>

                        <td style='background:#eee'>
                            <b>{t1}</b>
                        </td>

                        <td>{n.get('Mayo', '-')}</td>
                        <td>{n.get('Junio', '-')}</td>
                        <td>{n.get('Julio', '-')}</td>

                        <td style='background:#eee'>
                            <b>{t2}</b>
                        </td>

                        <td>{n.get('Agosto', '-')}</td>
                        <td>{n.get('Septiembre', '-')}</td>
                        <td>{n.get('Octubre', '-')}</td>

                        <td style='background:#eee'>
                            <b>{t3}</b>
                        </td>

                        <td style='
                            background:#333;
                            color:white;
                        '>
                            <b>{fin}</b>
                        </td>

                    </tr>
                    """
                )

            else:

                filas.append(
                    f"""
                    <tr>

                        <td style='text-align:left'>
                            {mat}
                        </td>

                        <td>-</td>
                        <td>-</td>
                        <td>-</td>

                        <td style='background:#eee'>
                            <b>0.0</b>
                        </td>

                        <td>-</td>
                        <td>-</td>
                        <td>-</td>

                        <td style='background:#eee'>
                            <b>0.0</b>
                        </td>

                        <td>-</td>
                        <td>-</td>
                        <td>-</td>

                        <td style='background:#eee'>
                            <b>0.0</b>
                        </td>

                        <td style='
                            background:#333;
                            color:white;
                        '>
                            <b>0.0</b>
                        </td>

                    </tr>
                    """
                )

        # ==========================================
        # BOLETA
        # ==========================================

        logo = get_base64(
            "logo.png"
        )

        hi = (
            f'<img src="{logo}" height="60">'
            if logo
            else ""
        )

        sello = get_base64(
            "sello.png"
        )

        hs = (
            f'<img src="{sello}" height="80">'
            if sello
            else ""
        )

        html = f"""
        <div style="
            font-family:Arial;
            font-size:12px;
            padding:20px;
        ">

            <div style="
                display:flex;
                align-items:center;
                border-bottom:2px solid black;
                margin-bottom:10px;
            ">

                {hi}

                <div style="margin-left:20px">

                    <h2>
                        COLEGIO PROFA. BLANCA ELENA
                    </h2>

                    <h4>
                        INFORME DE NOTAS
                        - CICLO {CICLO_LECTIVO}
                    </h4>

                </div>

            </div>

            <p>
                <b>Alumno:</b>
                {nombre_alum}

                |

                <b>Grado:</b>
                {grado_sel}

                |

                <b>Guía:</b>
                {maestro_guia}
            </p>

            <table
                border='1'
                style='
                    width:100%;
                    border-collapse:collapse;
                    text-align:center;
                '
            >

                <tr style='
                    background:#ddd;
                    font-weight:bold;
                '>

                    <td>ASIGNATURA</td>

                    <td>F</td>
                    <td>M</td>
                    <td>A</td>
                    <td>T1</td>

                    <td>M</td>
                    <td>J</td>
                    <td>J</td>
                    <td>T2</td>

                    <td>A</td>
                    <td>S</td>
                    <td>O</td>
                    <td>T3</td>

                    <td>FIN</td>

                </tr>

                {"".join(filas)}

            </table>

            <br><br><br>

            <div style='
                display:flex;
                justify-content:space-between;
                align-items:end;
                padding:0 50px;
            '>

                <div style='
                    text-align:center;
                    width:30%;
                '>

                    <div style='
                        border-top:1px solid black;
                        width:100%;
                    '>
                        Orientador
                    </div>

                </div>

                <div style='text-align:center;'>
                    {hs}
                </div>

                <div style='
                    text-align:center;
                    width:30%;
                '>

                    <div style='
                        border-top:1px solid black;
                        width:100%;
                    '>
                        Dirección
                    </div>

                </div>

            </div>

        </div>
        """

        components.html(
            f"""
            <html>
                <body>

                    {html}

                    <br>

                    <button
                        onclick="window.print()"
                    >
                        🖨️ IMPRIMIR BOLETA
                    </button>

                    <style>
                        @media print {{
                            button {{
                                display:none;
                            }}
                        }}
                    </style>

                </body>
            </html>
            """,
            height=600,
            scrolling=True
        )