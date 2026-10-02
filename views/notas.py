import time
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from views.notas_historicas import mostrar_notas_historicas
from config import CICLO_LECTIVO


def mostrar_notas(
    db,
    lista_grados_notas,
    lista_meses,
    mapa_curricular,
    redondear_mined,
    get_base64,
):
    """
    Gestión administrativa de notas.
    Incluye:
    - Registro mensual
    - Reporte anual por grado
    - Impresión masiva de boletas
    Todos los procesos respetan el ciclo lectivo actual.
    """
    st.title("📊 Gestión y Reportes de Notas")
    st.caption(f"📅 Ciclo lectivo actual: {CICLO_LECTIVO}")

    tab_registro, tab_reporte_grado, tab_historico = st.tabs(
        [
            "📝 Registro Mensual",
            "📜 Reporte por Grado (Cuadros)",
            "🕰️ Consulta Histórica",
        ]
    )

    # ========================================================
    # 1. REGISTRO MENSUAL
    # ========================================================
    with tab_registro:
        c1, c2, c3 = st.columns(3)
        grado = c1.selectbox(
            "Grado",
            ["Select..."] + lista_grados_notas,
            key="g_reg",
        )
        materias = (
            mapa_curricular.get(grado, [])
            if grado != "Select..."
            else []
        )
        materia = c2.selectbox(
            "Materia",
            ["Select..."] + materias,
            key="m_reg",
        )
        mes = c3.selectbox(
            "Mes",
            lista_meses,
            key="mes_reg",
        )

        if grado != "Select..." and materia != "Select...":
            # ------------------------------------------------
            # SOLO ALUMNOS ACTIVOS DEL GRADO
            # ------------------------------------------------
            docs = (
                db.collection("alumnos")
                .where("grado_actual", "==", grado)
                .where("estado", "==", "Activo")
                .stream()
            )

            lista = []
            for doc in docs:
                datos = doc.to_dict()
                ciclo_alumno = datos.get("ciclo_lectivo", CICLO_LECTIVO)
                try:
                    ciclo_alumno = int(ciclo_alumno)
                except (TypeError, ValueError):
                    pass
                if ciclo_alumno != CICLO_LECTIVO:
                    continue
                lista.append(
                    {
                        "NIE": str(datos.get("nie", doc.id)).strip(),
                        "Nombre": (
                            f"{datos.get('apellidos', '')} "
                            f"{datos.get('nombres', '')}"
                        ).strip(),
                    }
                )

            if not lista:
                st.warning("No hay alumnos activos para este grado y ciclo.")
            else:
                df = pd.DataFrame(lista).sort_values("Nombre")

                # ============================================
                # IDENTIFICADOR POR CICLO (nuevo + legacy)
                # ============================================
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

                detalles_nuevos = (
                    doc_nuevo.to_dict().get("detalles", {}) or {}
                    if doc_nuevo.exists
                    else {}
                )
                detalles_legacy = (
                    doc_legacy.to_dict().get("detalles", {}) or {}
                    if (doc_legacy is not None and doc_legacy.exists)
                    else {}
                )

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
                    id_doc = id_nuevo
                    detalles = detalles_nuevos
                elif tiene_notas_reales(detalles_legacy):
                    id_doc = id_legacy
                    detalles = detalles_legacy
                    st.caption(
                        "ℹ️ Se cargaron calificaciones históricas de 2026."
                    )
                elif tiene_contenido(detalles_nuevos):
                    id_doc = id_nuevo
                    detalles = detalles_nuevos
                elif tiene_contenido(detalles_legacy):
                    id_doc = id_legacy
                    detalles = detalles_legacy
                    st.caption(
                        "ℹ️ Se cargó el registro histórico de 2026."
                    )
                else:
                    id_doc = id_nuevo
                    detalles = {}

                # ============================================
                # COLUMNAS
                # ============================================
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

                # ============================================
                # CARGAR VALORES EXISTENTES
                # ============================================
                if detalles:
                    for columna in columnas_notas:
                        df[columna] = df["NIE"].map(
                            lambda nie, c=columna: detalles.get(
                                str(nie).strip(), {}
                            ).get(c, 0.0)
                        )
                    st.info("✅ Datos cargados desde notas_mensuales")
                else:
                    # Fallback: buscar en colección 'notas' individual
                    notas_ref = (
                        db.collection("notas")
                        .where("grado", "==", grado)
                        .where("materia", "==", materia)
                        .where("mes", "==", mes)
                        .stream()
                    )

                    promedios_reconstruidos = {}
                    for nota_doc in notas_ref:
                        nota_data = nota_doc.to_dict()

                        ciclo_nota = nota_data.get(
                            "ciclo_lectivo", CICLO_LECTIVO
                        )
                        try:
                            ciclo_nota = int(ciclo_nota)
                        except (TypeError, ValueError):
                            pass

                        if ciclo_nota != CICLO_LECTIVO:
                            continue

                        nie_nota = str(
                            nota_data.get("nie", "")
                        ).strip()
                        if nie_nota:
                            promedios_reconstruidos[nie_nota] = (
                                nota_data.get("promedio_final", 0.0)
                            )

                    for columna in columnas_notas:
                        df[columna] = 0.0

                    if promedios_reconstruidos:
                        df["Promedio"] = df["NIE"].map(
                            lambda nie: promedios_reconstruidos.get(
                                str(nie).strip(), 0.0
                            )
                        )
                        st.warning(
                            "⚠️ Los datos detallados (Act1, Act2, Alt1, "
                            "Alt2, Examen) no están disponibles. "
                            "Solo se muestra el promedio final guardado."
                        )
                    else:
                        df["Promedio"] = 0.0
                        st.info(
                            "No hay notas registradas para este mes."
                        )

                # ============================================
                # PROMEDIO (solo si no fue recuperado en el fallback)
                # ============================================
                if "Promedio" not in df.columns:
                    if materia == "Conducta":
                        df["Promedio"] = df[columnas_notas[0]]
                    else:
                        df["Promedio"] = (
                            df["Act1 (25%)"] * 0.25
                            + df["Act2 (25%)"] * 0.25
                            + df["Alt1 (10%)"] * 0.10
                            + df["Alt2 (10%)"] * 0.10
                            + df["Examen (30%)"] * 0.30
                        ).apply(redondear_mined)

                # ============================================
                # CONFIGURACIÓN EDITOR
                # ============================================
                config_columnas = {
                    "NIE": st.column_config.TextColumn(disabled=True),
                    "Nombre": st.column_config.TextColumn(
                        disabled=True, width="medium"
                    ),
                    "Promedio": st.column_config.NumberColumn(
                        disabled=True
                    ),
                }
                for columna in columnas_notas:
                    config_columnas[columna] = (
                        st.column_config.NumberColumn(
                            min_value=0.0,
                            max_value=10.0,
                            step=0.01,
                        )
                    )

                editor = st.data_editor(
                    df,
                    column_config=config_columnas,
                    hide_index=True,
                    width="stretch",
                    key=f"editor_{id_doc}",
                )

                st.caption(f"Registro leído desde: {id_doc}")

                # ============================================
                # BOTÓN: GUARDAR NOTAS
                # ============================================
                if st.button(
                    "💾 Guardar Notas",
                    type="primary",
                    key="doc_guardar_notas_admin",
                ):
                    batch = db.batch()
                    detalles_guardar = {}

                    for _, fila in editor.iterrows():
                        if materia == "Conducta":
                            promedio = fila[columnas_notas[0]]
                        else:
                            promedio = (
                                fila["Act1 (25%)"] * 0.25
                                + fila["Act2 (25%)"] * 0.25
                                + fila["Alt1 (10%)"] * 0.10
                                + fila["Alt2 (10%)"] * 0.10
                                + fila["Examen (30%)"] * 0.30
                            )

                        promedio_redondeado = redondear_mined(promedio)
                        nie = str(fila["NIE"]).strip()

                        detalles_guardar[nie] = {
                            columna: float(fila[columna])
                            for columna in columnas_notas
                        }
                        detalles_guardar[nie]["Promedio"] = (
                            promedio_redondeado
                        )

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
                                "promedio_final": promedio_redondeado,
                            },
                        )

                    db.collection("notas_mensuales").document(
                        id_nuevo
                    ).set(
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

                # ============================================
                # BOTÓN: IMPRIMIR CUADRO DEL MES (PDF)
                # ============================================
                st.markdown("---")
                st.markdown("### 🖨️ Respaldo del Cuadro de Notas")

                if st.button(
                    "📄 Generar PDF del Cuadro de este Mes"
                ):
                    logo_b64 = get_base64("logo.png")
                    imagen_logo = (
                        f'<img src="{logo_b64}" height="50">'
                        if logo_b64
                        else ""
                    )
                    fecha_impresion = time.strftime("%d/%m/%Y %H:%M")

                    df_impresion = editor.copy()

                    if materia == "Conducta":
                        df_impresion["Promedio"] = df_impresion[
                            columnas_notas[0]
                        ]
                    else:
                        df_impresion["Promedio"] = (
                            df_impresion["Act1 (25%)"] * 0.25
                            + df_impresion["Act2 (25%)"] * 0.25
                            + df_impresion["Alt1 (10%)"] * 0.10
                            + df_impresion["Alt2 (10%)"] * 0.10
                            + df_impresion["Examen (30%)"] * 0.30
                        ).apply(redondear_mined)

                    filas_html = ""
                    for _, fila in df_impresion.iterrows():
                        celdas_notas = ""
                        for col in columnas_notas:
                            valor = fila[col]
                            celdas_notas += f"<td>{valor}</td>"
                        filas_html += f"""
                        <tr>
                            <td style="text-align:left; padding-left:5px;">
                                {fila['Nombre']}
                            </td>
                            <td>{fila['NIE']}</td>
                            {celdas_notas}
                            <td style="background:#1e3a8a; color:white; font-weight:bold;">
                                {fila['Promedio']}
                            </td>
                        </tr>
                        """

                    encabezados_notas = "".join(
                        [f"<th>{col}</th>" for col in columnas_notas]
                    )

                    html_cuadro = f"""
                    <div style="font-family: Arial, sans-serif; padding: 20px;">
                        <div style="display:flex; align-items:center; border-bottom:2px solid #333; margin-bottom:15px;">
                            {imagen_logo}
                            <div style="margin-left:20px;">
                                <h2 style="margin:0;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2>
                                <h4 style="margin:5px 0 0 0; color:#555;">CUADRO DE NOTAS MENSUAL - CICLO {CICLO_LECTIVO}</h4>
                            </div>
                        </div>

                        <table style="width:100%; font-size:12px; margin-bottom:15px;">
                            <tr>
                                <td><b>GRADO:</b> {grado}</td>
                                <td><b>ASIGNATURA:</b> {materia}</td>
                                <td><b>MES:</b> {mes}</td>
                            </tr>
                            <tr>
                                <td><b>TOTAL ALUMNOS:</b> {len(df_impresion)}</td>
                                <td><b>FECHA DE IMPRESIÓN:</b> {fecha_impresion}</td>
                                <td></td>
                            </tr>
                        </table>

                        <table border="1" style="width:100%; border-collapse:collapse; text-align:center; font-size:11px;">
                            <tr style="background:#f2f2f2; font-weight:bold;">
                                <th style="text-align:left; padding-left:5px;">NOMBRE DEL ALUMNO</th>
                                <th>NIE</th>
                                {encabezados_notas}
                                <th style="background:#1e3a8a; color:white;">PROMEDIO</th>
                            </tr>
                            {filas_html}
                        </table>

                        <br><br>
                        <div style="display:flex; justify-content:space-between; margin-top:60px;">
                            <div style="width:40%; border-top:1px solid black; text-align:center; font-size:11px;">
                                <br>Firma del Docente
                            </div>
                            <div style="width:40%; border-top:1px solid black; text-align:center; font-size:11px;">
                                <br>Firma de Coordinación
                            </div>
                        </div>
                    </div>
                    """

                    components.html(
                        f"""
                        <html>
                        <head>
                            <style>
                                @media print {{
                                    button {{ display:none; }}
                                    body {{ margin: 0.5cm; }}
                                }}
                                body {{ font-family: Arial, sans-serif; }}
                            </style>
                        </head>
                        <body>
                            {html_cuadro}
                            <br>
                            <center>
                                <button onclick="window.print()" style="
                                    padding:12px 24px;
                                    background:#2e7d32;
                                    color:white;
                                    border:none;
                                    border-radius:5px;
                                    font-size:15px;
                                    cursor:pointer;
                                ">
                                    ️ IMPRIMIR / GUARDAR COMO PDF
                                </button>
                            </center>
                        </body>
                        </html>
                        """,
                        height=700,
                        scrolling=True,
                    )

    # ========================================================
    # 2. REPORTE ANUAL POR GRADO
    # ========================================================
    with tab_reporte_grado:
        st.subheader("📜 Cuadro de Registro Anual y Promedios")
        c1, _ = st.columns([2, 2])
        grado_reporte = c1.selectbox(
            "Seleccione Grado para el Cuadro Anual:",
            ["Select..."] + lista_grados_notas,
            key="g_rep_anual",
        )

        if grado_reporte != "Select...":
            if st.button(
                "Generar Reporte de Rendimiento Anual"
            ):
                with st.spinner("Calculando promedios anuales..."):
                    alumnos_docs = (
                        db.collection("alumnos")
                        .where("grado_actual", "==", grado_reporte)
                        .where("estado", "==", "Activo")
                        .stream()
                    )

                    alumnos_list = []
                    for doc in alumnos_docs:
                        datos = doc.to_dict()

                        ciclo_alumno = datos.get(
                            "ciclo_lectivo", CICLO_LECTIVO
                        )
                        try:
                            ciclo_alumno = int(ciclo_alumno)
                        except (TypeError, ValueError):
                            pass

                        if ciclo_alumno != CICLO_LECTIVO:
                            continue

                        alumnos_list.append(
                            {
                                "nie": str(
                                    datos.get("nie", doc.id)
                                ).strip(),
                                "nombre": (
                                    f"{datos.get('apellidos', '')} "
                                    f"{datos.get('nombres', '')}"
                                ).strip(),
                            }
                        )

                    alumnos_list.sort(
                        key=lambda x: x["nombre"]
                    )
                    materias_reporte = mapa_curricular.get(
                        grado_reporte, []
                    )

                    notas_ref = (
                        db.collection("notas")
                        .where("grado", "==", grado_reporte)
                        .stream()
                    )

                    data_anual = {}
                    for nota_doc in notas_ref:
                        nota = nota_doc.to_dict()

                        ciclo_nota = nota.get(
                            "ciclo_lectivo", CICLO_LECTIVO
                        )
                        try:
                            ciclo_nota = int(ciclo_nota)
                        except (TypeError, ValueError):
                            pass

                        if ciclo_nota != CICLO_LECTIVO:
                            continue

                        nie = str(nota["nie"]).strip()
                        materia = nota["materia"]
                        mes_nota = nota["mes"]
                        valor = nota["promedio_final"]
                        data_anual.setdefault(
                            nie, {}
                        ).setdefault(materia, {})[
                            mes_nota
                        ] = valor

                    rows_html = ""
                    for indice, alumno in enumerate(
                        alumnos_list
                    ):
                        notas_alumno = data_anual.get(
                            alumno["nie"], {}
                        )
                        for indice_materia, materia in enumerate(
                            materias_reporte
                        ):
                            notas_materia = (
                                notas_alumno.get(materia, {})
                            )
                            t1 = (
                                notas_materia.get("Febrero", 0)
                                + notas_materia.get("Marzo", 0)
                                + notas_materia.get("Abril", 0)
                            ) / 3
                            t2 = (
                                notas_materia.get("Mayo", 0)
                                + notas_materia.get("Junio", 0)
                                + notas_materia.get("Julio", 0)
                            ) / 3
                            t3 = (
                                notas_materia.get("Agosto", 0)
                                + notas_materia.get(
                                    "Septiembre", 0
                                )
                                + notas_materia.get("Octubre", 0)
                            ) / 3
                            rt1 = redondear_mined(t1)
                            rt2 = redondear_mined(t2)
                            rt3 = redondear_mined(t3)
                            promedio_final = redondear_mined(
                                (rt1 + rt2 + rt3) / 3
                            )

                            if indice_materia == 0:
                                row_start = (
                                    f"<tr>"
                                    f"<td rowspan='{len(materias_reporte)}'>"
                                    f"{indice + 1}</td>"
                                    f"<td rowspan='{len(materias_reporte)}' "
                                    f"style='text-align:left;'>"
                                    f"{alumno['nombre']}</td>"
                                )
                            else:
                                row_start = "<tr>"

                            rows_html += f"""
                                {row_start}
                                <td style="text-align:left; font-size:10px;">{materia}</td>
                                <td>{notas_materia.get('Febrero', '-')}</td>
                                <td>{notas_materia.get('Marzo', '-')}</td>
                                <td>{notas_materia.get('Abril', '-')}</td>
                                <td style="background:#e3f2fd;"><b>{rt1}</b></td>
                                <td>{notas_materia.get('Mayo', '-')}</td>
                                <td>{notas_materia.get('Junio', '-')}</td>
                                <td>{notas_materia.get('Julio', '-')}</td>
                                <td style="background:#e3f2fd;"><b>{rt2}</b></td>
                                <td>{notas_materia.get('Agosto', '-')}</td>
                                <td>{notas_materia.get('Septiembre', '-')}</td>
                                <td>{notas_materia.get('Octubre', '-')}</td>
                                <td style="background:#e3f2fd;"><b>{rt3}</b></td>
                                <td style="background:#1e3a8a; color:white;"><b>{promedio_final}</b></td>
                                </tr>
                            """

                    logo = get_base64("logo.png")
                    imagen_logo = (
                        f'<img src="{logo}" height="50">'
                        if logo
                        else ""
                    )
                    html_reporte = f"""
                    <div style="font-family:Arial; padding:10px;">
                        <div style="text-align:center; border-bottom:2px solid #333;">
                            {imagen_logo}
                            <h2>COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2>
                            <h3>CUADRO DE REGISTRO DE CALIFICACIONES ANUAL - CICLO {CICLO_LECTIVO}</h3>
                            <p><b>GRADO:</b> {grado_reporte.upper()}</p>
                        </div>
                        <table border="1" style="width:100%; border-collapse:collapse; text-align:center; font-size:11px; margin-top:10px;">
                            <tr style="background:#f2f2f2;">
                                <th>No.</th><th>ESTUDIANTE</th><th>ASIGNATURA</th>
                                <th>FEB</th><th>MAR</th><th>ABR</th><th>PT1</th>
                                <th>MAY</th><th>JUN</th><th>JUL</th><th>PT2</th>
                                <th>AGO</th><th>SEP</th><th>OCT</th><th>PT3</th><th>PF</th>
                            </tr>
                            {rows_html}
                        </table>
                    </div>
                    """
                    components.html(
                        f"""
                        <html><body>{html_reporte}<br><center>
                            <button onclick="window.print()">🖨️ IMPRIMIR REPORTE ANUAL</button>
                        </center></body></html>
                        """,
                        height=800,
                        scrolling=True,
                    )

    # ========================================================
    # 3. CONSULTA HISTÓRICA
    # ========================================================
    with tab_historico:
        mostrar_notas_historicas(
            db=db,
            lista_grados_notas=lista_grados_notas,
            mapa_curricular=mapa_curricular,
            redondear_mined=redondear_mined,
            get_base64=get_base64,
        )

    # ========================================================
    # 4. IMPRESIÓN MASIVA DE BOLETAS
    # ========================================================
    st.divider()
    st.subheader("🖨️ Impresión Masiva de Boletas")
    c_lote, c_mat = st.columns([1, 2])
    grado_lote = c_lote.selectbox(
        "Grado:",
        ["Select..."] + lista_grados_notas,
        key="g_lote_v2",
    )
    materias_disponibles = (
        mapa_curricular.get(grado_lote, [])
        if grado_lote != "Select..."
        else []
    )
    materias_seleccionadas = c_mat.multiselect(
        "Materias a incluir en la boleta:",
        options=materias_disponibles,
        default=materias_disponibles,
    )

    if (
        grado_lote != "Select..."
        and st.button("Generar Lote Personalizado")
    ):
        if not materias_seleccionadas:
            st.warning("Seleccione al menos una materia.")
        else:
            with st.spinner("Preparando documentos..."):
                alumnos_docs = (
                    db.collection("alumnos")
                    .where("grado_actual", "==", grado_lote)
                    .where("estado", "==", "Activo")
                    .stream()
                )
                alumnos_list = []
                for doc in alumnos_docs:
                    datos = doc.to_dict()

                    ciclo_alumno = datos.get(
                        "ciclo_lectivo", CICLO_LECTIVO
                    )
                    try:
                        ciclo_alumno = int(ciclo_alumno)
                    except (TypeError, ValueError):
                        pass

                    if ciclo_alumno != CICLO_LECTIVO:
                        continue

                    alumnos_list.append(datos)

                alumnos_list.sort(
                    key=lambda x: x.get("apellidos", "")
                )

                guia_docs = (
                    db.collection("carga_academica")
                    .where("grado", "==", grado_lote)
                    .where("es_guia", "==", True)
                    .stream()
                )
                maestro_guia = "No Asignado"
                for doc in guia_docs:
                    datos_guia = doc.to_dict()

                    ciclo_guia = datos_guia.get(
                        "ciclo_lectivo", CICLO_LECTIVO
                    )
                    try:
                        ciclo_guia = int(ciclo_guia)
                    except (TypeError, ValueError):
                        pass

                    if ciclo_guia == CICLO_LECTIVO:
                        maestro_guia = datos_guia.get(
                            "nombre_docente", "No Asignado"
                        )
                        break

                notas_ref = (
                    db.collection("notas")
                    .where("grado", "==", grado_lote)
                    .stream()
                )
                mapa_notas_global = {}
                for documento in notas_ref:
                    nota = documento.to_dict()

                    ciclo_nota = nota.get(
                        "ciclo_lectivo", CICLO_LECTIVO
                    )
                    try:
                        ciclo_nota = int(ciclo_nota)
                    except (TypeError, ValueError):
                        pass

                    if ciclo_nota != CICLO_LECTIVO:
                        continue

                    nie = str(nota["nie"]).strip()
                    materia = nota["materia"]
                    mes = nota["mes"]
                    valor = nota["promedio_final"]
                    mapa_notas_global.setdefault(
                        nie, {}
                    ).setdefault(materia, {})[mes] = valor

                logo_b64 = get_base64("logo.png")
                imagen_logo = (
                    f'<img src="{logo_b64}" height="45">'
                    if logo_b64
                    else ""
                )
                html_masivo = ""

                for indice, alumno in enumerate(alumnos_list):
                    nie_alumno = str(alumno.get("nie", "")).strip()
                    notas_alumno = mapa_notas_global.get(
                        nie_alumno, {}
                    )
                    filas_notas = ""
                    for materia in materias_seleccionadas:
                        notas = notas_alumno.get(materia, {})
                        t1 = redondear_mined(
                            (
                                notas.get("Febrero", 0)
                                + notas.get("Marzo", 0)
                                + notas.get("Abril", 0)
                            )
                            / 3
                        )
                        t2 = redondear_mined(
                            (
                                notas.get("Mayo", 0)
                                + notas.get("Junio", 0)
                                + notas.get("Julio", 0)
                            )
                            / 3
                        )
                        t3 = redondear_mined(
                            (
                                notas.get("Agosto", 0)
                                + notas.get("Septiembre", 0)
                                + notas.get("Octubre", 0)
                            )
                            / 3
                        )
                        final = redondear_mined(
                            (t1 + t2 + t3) / 3
                        )
                        filas_notas += f"""
                        <tr>
                            <td style="text-align:left; padding-left:5px;">{materia}</td>
                            <td>{notas.get('Febrero', '-')}</td>
                            <td>{notas.get('Marzo', '-')}</td>
                            <td>{notas.get('Abril', '-')}</td>
                            <td class="trimestre">{t1}</td>
                            <td>{notas.get('Mayo', '-')}</td>
                            <td>{notas.get('Junio', '-')}</td>
                            <td>{notas.get('Julio', '-')}</td>
                            <td class="trimestre">{t2}</td>
                            <td>{notas.get('Agosto', '-')}</td>
                            <td>{notas.get('Septiembre', '-')}</td>
                            <td>{notas.get('Octubre', '-')}</td>
                            <td class="trimestre">{t3}</td>
                            <td class="final">{final}</td>
                        </tr>
                        """

                    boleta_html = f"""
                    <div class="boleta-container">
                        <div style="display:flex; align-items:center; border-bottom:1px solid black; margin-bottom:8px;">
                            {imagen_logo}
                            <div style="margin-left:15px;">
                                <h2 style="margin:0; font-size:16px;">COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2>
                                <h4 style="margin:0; color:#444;">INFORME DE RENDIMIENTO ACADÉMICO - {CICLO_LECTIVO}</h4>
                            </div>
                        </div>
                        <table style="width:100%; font-size:11px; margin-bottom:8px;">
                            <tr>
                                <td><b>ALUMNO:</b> {alumno.get('apellidos', '')} {alumno.get('nombres', '')}</td>
                                <td style="text-align:right;"><b>GRADO:</b> {grado_lote}</td>
                            </tr>
                            <tr>
                                <td><b>NIE:</b> {nie_alumno}</td>
                                <td style="text-align:right;"><b>GUÍA:</b> {maestro_guia}</td>
                            </tr>
                        </table>
                        <table border="1" style="width:100%; border-collapse:collapse; text-align:center; font-size:10px;">
                            <tr style="background:#f2f2f2; font-weight:bold;">
                                <td width="25%">ASIGNATURA</td>
                                <td>FEB</td><td>MAR</td><td>ABR</td><td>T1</td>
                                <td>MAY</td><td>JUN</td><td>JUL</td><td>T2</td>
                                <td>AGO</td><td>SEP</td><td>OCT</td><td>T3</td><td>PF</td>
                            </tr>
                            {filas_notas}
                        </table>
                        <div style="display:flex; justify-content:space-around; margin-top:40px;">
                            <div style="width:40%; border-top:1px solid black; text-align:center; font-size:10px;"><br>F. Maestro Orientador</div>
                            <div style="width:40%; border-top:1px solid black; text-align:center; font-size:10px;"><br>F. Dirección / Sello</div>
                        </div>
                    </div>
                    <div class="cut-line">✂-------------------------------------------------------------✂</div>
                    """
                    html_masivo += boleta_html
                    if (indice + 1) % 2 == 0:
                        html_masivo += '<div class="page-break"></div>'

                full_html = f"""
                <html>
                <head>
                    <style>
                        @page {{ size: letter; margin: 0.5cm; }}
                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin:0; }}
                        .boleta-container {{ height:46%; padding:20px; box-sizing:border-box; position:relative; }}
                        .trimestre {{ background-color:#f8f9fa; font-weight:bold; }}
                        .final {{ background-color:#1e3a8a; color:white; font-weight:bold; }}
                        .cut-line {{ width:100%; text-align:center; color:#999; font-size:12px; height:2%; border-bottom: 1px dashed #ccc; margin-bottom:10px; }}
                        .page-break {{ page-break-after:always; }}
                        @media print {{ button {{ display:none; }} .cut-line {{ border-bottom: 1px dashed #000; }} }}
                    </style>
                </head>
                <body>
                    {html_masivo}
                    <br>
                    <center>
                        <button onclick="window.print()" style="padding:15px 30px; background:#2e7d32; color:white; border:none; border-radius:5px; font-size:16px; cursor:pointer;">
                            🖨️ IMPRIMIR LOTE DE BOLETAS
                        </button>
                    </center>
                </body>
                </html>
                """
                components.html(
                    full_html, height=800, scrolling=True
                )