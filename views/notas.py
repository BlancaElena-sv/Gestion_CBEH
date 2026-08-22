import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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

    st.caption(
        f"📅 Ciclo lectivo actual: {CICLO_LECTIVO}"
    )

    tab_registro, tab_reporte_grado = st.tabs(
        [
            "📝 Registro Mensual",
            "📜 Reporte por Grado (Cuadros)",
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

        if (
            grado != "Select..."
            and materia != "Select..."
        ):

            # ------------------------------------------------
            # SOLO ALUMNOS ACTIVOS DEL GRADO
            # ------------------------------------------------

            docs = (
                db.collection("alumnos")
                .where(
                    "grado_actual",
                    "==",
                    grado,
                )
                .where(
                    "estado",
                    "==",
                    "Activo",
                )
                .stream()
            )

            lista = []

            for doc in docs:
                datos = doc.to_dict()

                # Protección adicional por ciclo
                ciclo_alumno = datos.get(
                    "ciclo_lectivo",
                    CICLO_LECTIVO,
                )

                if ciclo_alumno != CICLO_LECTIVO:
                    continue

                lista.append(
                    {
                        "NIE": datos["nie"],
                        "Nombre": (
                            f"{datos.get('apellidos', '')} "
                            f"{datos.get('nombres', '')}"
                        ).strip(),
                    }
                )

            if not lista:
                st.warning(
                    "No hay alumnos activos para "
                    "este grado y ciclo."
                )

            else:

                df = (
                    pd.DataFrame(lista)
                    .sort_values("Nombre")
                )

                # ============================================
                # IDENTIFICADOR POR CICLO
                # ============================================

                id_base = (
                    f"{grado}_{materia}_{mes}"
                    .replace(" ", "_")
                )

                id_nuevo = (
                    f"{CICLO_LECTIVO}_{id_base}"
                )

                # Compatibilidad con documentos 2026 antiguos
                id_legacy = id_base

                doc_nuevo = (
                    db.collection("notas_mensuales")
                    .document(id_nuevo)
                    .get()
                )

                if doc_nuevo.exists:
                    id_doc = id_nuevo
                    doc_ref = doc_nuevo

                elif CICLO_LECTIVO == 2026:
                    doc_antiguo = (
                        db.collection(
                            "notas_mensuales"
                        )
                        .document(id_legacy)
                        .get()
                    )

                    if doc_antiguo.exists:
                        id_doc = id_legacy
                        doc_ref = doc_antiguo

                    else:
                        id_doc = id_nuevo
                        doc_ref = doc_nuevo

                else:
                    id_doc = id_nuevo
                    doc_ref = doc_nuevo

                # ============================================
                # COLUMNAS
                # ============================================

                if materia == "Conducta":
                    columnas_notas = [
                        "Nota Conducta"
                    ]

                else:
                    columnas_notas = [
                        "Act1 (25%)",
                        "Act2 (25%)",
                        "Alt1 (10%)",
                        "Alt2 (10%)",
                        "Examen (30%)",
                    ]

                # ============================================
                # CARGAR DATOS EXISTENTES
                # ============================================

                if doc_ref.exists:

                    detalles = (
                        doc_ref
                        .to_dict()
                        .get(
                            "detalles",
                            {},
                        )
                    )

                    for columna in columnas_notas:
                        df[columna] = (
                            df["NIE"].map(
                                lambda nie: (
                                    detalles
                                    .get(nie, {})
                                    .get(
                                        columna,
                                        0.0,
                                    )
                                )
                            )
                        )

                else:

                    for columna in columnas_notas:
                        df[columna] = 0.0

                # ============================================
                # PROMEDIO
                # ============================================

                if materia == "Conducta":

                    df["Promedio"] = (
                        df[columnas_notas[0]]
                    )

                else:

                    df["Promedio"] = (
                        (
                            df["Act1 (25%)"] * 0.25
                            + df["Act2 (25%)"] * 0.25
                            + df["Alt1 (10%)"] * 0.10
                            + df["Alt2 (10%)"] * 0.10
                            + df["Examen (30%)"] * 0.30
                        )
                        .apply(redondear_mined)
                    )

                # ============================================
                # CONFIGURACIÓN EDITOR
                # ============================================

                config_columnas = {
                    "NIE": (
                        st.column_config.TextColumn(
                            disabled=True
                        )
                    ),
                    "Nombre": (
                        st.column_config.TextColumn(
                            disabled=True,
                            width="medium",
                        )
                    ),
                    "Promedio": (
                        st.column_config.NumberColumn(
                            disabled=True
                        )
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

                # ============================================
                # GUARDAR
                # ============================================

                if st.button(
                    "💾 Guardar Notas",
                    type="primary",
                ):

                    batch = db.batch()

                    detalles = {}

                    for _, fila in editor.iterrows():

                        if materia == "Conducta":

                            promedio = (
                                fila[
                                    columnas_notas[0]
                                ]
                            )

                        else:

                            promedio = (
                                fila[
                                    columnas_notas[0]
                                ] * 0.25
                                + fila[
                                    columnas_notas[1]
                                ] * 0.25
                                + fila[
                                    columnas_notas[2]
                                ] * 0.10
                                + fila[
                                    columnas_notas[3]
                                ] * 0.10
                                + fila[
                                    columnas_notas[4]
                                ] * 0.30
                            )

                        promedio_redondeado = (
                            redondear_mined(
                                promedio
                            )
                        )

                        nie = fila["NIE"]

                        detalles[nie] = {
                            columna: fila[columna]
                            for columna
                            in columnas_notas
                        }

                        detalles[nie][
                            "Promedio"
                        ] = promedio_redondeado

                        ref_nota = (
                            db.collection("notas")
                            .document(
                                f"{nie}_{id_doc}"
                            )
                        )

                        batch.set(
                            ref_nota,
                            {
                                "nie": nie,
                                "ciclo_lectivo": (
                                    CICLO_LECTIVO
                                ),
                                "grado": grado,
                                "materia": materia,
                                "mes": mes,
                                "promedio_final": (
                                    promedio_redondeado
                                ),
                            },
                        )

                    db.collection(
                        "notas_mensuales"
                    ).document(
                        id_doc
                    ).set(
                        {
                            "ciclo_lectivo": (
                                CICLO_LECTIVO
                            ),
                            "grado": grado,
                            "materia": materia,
                            "mes": mes,
                            "detalles": detalles,
                        }
                    )

                    batch.commit()

                    st.success(
                        "✅ Notas guardadas correctamente."
                    )

                    time.sleep(1)
                    st.rerun()

    # ========================================================
    # 2. REPORTE ANUAL POR GRADO
    # ========================================================

    with tab_reporte_grado:

        st.subheader(
            "📜 Cuadro de Registro Anual y Promedios"
        )

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

                with st.spinner(
                    "Calculando promedios anuales..."
                ):

                    # ----------------------------------------
                    # ALUMNOS ACTIVOS DEL CICLO
                    # ----------------------------------------

                    alumnos_docs = (
                        db.collection("alumnos")
                        .where(
                            "grado_actual",
                            "==",
                            grado_reporte,
                        )
                        .where(
                            "estado",
                            "==",
                            "Activo",
                        )
                        .stream()
                    )

                    alumnos_list = []

                    for doc in alumnos_docs:

                        datos = doc.to_dict()

                        if (
                            datos.get(
                                "ciclo_lectivo",
                                CICLO_LECTIVO,
                            )
                            != CICLO_LECTIVO
                        ):
                            continue

                        alumnos_list.append(
                            {
                                "nie": datos.get(
                                    "nie",
                                    doc.id,
                                ),
                                "nombre": (
                                    f"{datos.get('apellidos', '')} "
                                    f"{datos.get('nombres', '')}"
                                ).strip(),
                            }
                        )

                    alumnos_list.sort(
                        key=lambda x: x["nombre"]
                    )

                    materias_reporte = (
                        mapa_curricular.get(
                            grado_reporte,
                            [],
                        )
                    )

                    # ----------------------------------------
                    # NOTAS DEL GRADO Y CICLO
                    # ----------------------------------------

                    notas_ref = (
                        db.collection("notas")
                        .where(
                            "grado",
                            "==",
                            grado_reporte,
                        )
                        .stream()
                    )

                    data_anual = {}

                    for nota_doc in notas_ref:

                        nota = nota_doc.to_dict()

                        if (
                            nota.get(
                                "ciclo_lectivo",
                                2026,
                            )
                            != CICLO_LECTIVO
                        ):
                            continue

                        nie = nota["nie"]
                        materia = nota["materia"]
                        mes_nota = nota["mes"]

                        valor = nota[
                            "promedio_final"
                        ]

                        data_anual.setdefault(
                            nie,
                            {},
                        )

                        data_anual[nie].setdefault(
                            materia,
                            {},
                        )

                        data_anual[nie][
                            materia
                        ][mes_nota] = valor

                    # ----------------------------------------
                    # HTML
                    # ----------------------------------------

                    rows_html = ""

                    for indice, alumno in enumerate(
                        alumnos_list
                    ):

                        notas_alumno = (
                            data_anual.get(
                                alumno["nie"],
                                {},
                            )
                        )

                        for indice_materia, materia in enumerate(
                            materias_reporte
                        ):

                            notas_materia = (
                                notas_alumno.get(
                                    materia,
                                    {},
                                )
                            )

                            t1 = (
                                notas_materia.get(
                                    "Febrero",
                                    0,
                                )
                                + notas_materia.get(
                                    "Marzo",
                                    0,
                                )
                                + notas_materia.get(
                                    "Abril",
                                    0,
                                )
                            ) / 3

                            t2 = (
                                notas_materia.get(
                                    "Mayo",
                                    0,
                                )
                                + notas_materia.get(
                                    "Junio",
                                    0,
                                )
                                + notas_materia.get(
                                    "Julio",
                                    0,
                                )
                            ) / 3

                            t3 = (
                                notas_materia.get(
                                    "Agosto",
                                    0,
                                )
                                + notas_materia.get(
                                    "Septiembre",
                                    0,
                                )
                                + notas_materia.get(
                                    "Octubre",
                                    0,
                                )
                            ) / 3

                            rt1 = redondear_mined(t1)
                            rt2 = redondear_mined(t2)
                            rt3 = redondear_mined(t3)

                            promedio_final = (
                                redondear_mined(
                                    (
                                        rt1
                                        + rt2
                                        + rt3
                                    ) / 3
                                )
                            )

                            if indice_materia == 0:

                                row_start = (
                                    f"<tr>"
                                    f"<td rowspan='{len(materias_reporte)}'>"
                                    f"{indice + 1}"
                                    f"</td>"
                                    f"<td rowspan='{len(materias_reporte)}' "
                                    f"style='text-align:left;'>"
                                    f"{alumno['nombre']}"
                                    f"</td>"
                                )

                            else:
                                row_start = "<tr>"

                            rows_html += f"""
                                {row_start}

                                <td style="
                                    text-align:left;
                                    font-size:10px;
                                ">
                                    {materia}
                                </td>

                                <td>{notas_materia.get('Febrero', '-')}</td>
                                <td>{notas_materia.get('Marzo', '-')}</td>
                                <td>{notas_materia.get('Abril', '-')}</td>

                                <td style="background:#e3f2fd;">
                                    <b>{rt1}</b>
                                </td>

                                <td>{notas_materia.get('Mayo', '-')}</td>
                                <td>{notas_materia.get('Junio', '-')}</td>
                                <td>{notas_materia.get('Julio', '-')}</td>

                                <td style="background:#e3f2fd;">
                                    <b>{rt2}</b>
                                </td>

                                <td>{notas_materia.get('Agosto', '-')}</td>
                                <td>{notas_materia.get('Septiembre', '-')}</td>
                                <td>{notas_materia.get('Octubre', '-')}</td>

                                <td style="background:#e3f2fd;">
                                    <b>{rt3}</b>
                                </td>

                                <td style="
                                    background:#1e3a8a;
                                    color:white;
                                ">
                                    <b>{promedio_final}</b>
                                </td>

                                </tr>
                            """

                    logo = get_base64(
                        "logo.png"
                    )

                    imagen_logo = (
                        f'<img src="{logo}" height="50">'
                        if logo
                        else ""
                    )

                    html_reporte = f"""
                    <div style="
                        font-family:Arial;
                        padding:10px;
                    ">

                        <div style="
                            text-align:center;
                            border-bottom:2px solid #333;
                        ">

                            {imagen_logo}

                            <h2>
                                COLEGIO PROFA. BLANCA ELENA
                                DE HERNÁNDEZ
                            </h2>

                            <h3>
                                CUADRO DE REGISTRO DE
                                CALIFICACIONES ANUAL
                                - CICLO {CICLO_LECTIVO}
                            </h3>

                            <p>
                                <b>GRADO:</b>
                                {grado_reporte.upper()}
                            </p>

                        </div>

                        <table
                            border="1"
                            style="
                                width:100%;
                                border-collapse:collapse;
                                text-align:center;
                                font-size:11px;
                                margin-top:10px;
                            "
                        >

                            <tr style="
                                background:#f2f2f2;
                            ">
                                <th>No.</th>
                                <th>ESTUDIANTE</th>
                                <th>ASIGNATURA</th>

                                <th>FEB</th>
                                <th>MAR</th>
                                <th>ABR</th>
                                <th>PT1</th>

                                <th>MAY</th>
                                <th>JUN</th>
                                <th>JUL</th>
                                <th>PT2</th>

                                <th>AGO</th>
                                <th>SEP</th>
                                <th>OCT</th>
                                <th>PT3</th>

                                <th>PF</th>
                            </tr>

                            {rows_html}

                        </table>

                    </div>
                    """

                    components.html(
                        f"""
                        <html>
                            <body>
                                {html_reporte}

                                <br>

                                <center>
                                    <button onclick="window.print()">
                                        🖨️ IMPRIMIR REPORTE ANUAL
                                    </button>
                                </center>
                            </body>
                        </html>
                        """,
                        height=800,
                        scrolling=True,
                    )

    # ========================================================
    # 3. IMPRESIÓN MASIVA DE BOLETAS
    # ========================================================

    st.divider()

    st.subheader(
        "🖨️ Impresión Masiva de Boletas"
    )

    c_lote, c_mat = st.columns([1, 2])

    grado_lote = c_lote.selectbox(
        "Grado:",
        ["Select..."] + lista_grados_notas,
        key="g_lote_v2",
    )

    materias_disponibles = (
        mapa_curricular.get(
            grado_lote,
            [],
        )
        if grado_lote != "Select..."
        else []
    )

    materias_seleccionadas = (
        c_mat.multiselect(
            "Materias a incluir en la boleta:",
            options=materias_disponibles,
            default=materias_disponibles,
        )
    )

    if (
        grado_lote != "Select..."
        and st.button(
            "Generar Lote Personalizado"
        )
    ):

        if not materias_seleccionadas:

            st.warning(
                "Seleccione al menos una materia."
            )

        else:

            with st.spinner(
                "Preparando documentos..."
            ):

                # --------------------------------------------
                # ALUMNOS ACTIVOS
                # --------------------------------------------

                alumnos_docs = (
                    db.collection("alumnos")
                    .where(
                        "grado_actual",
                        "==",
                        grado_lote,
                    )
                    .where(
                        "estado",
                        "==",
                        "Activo",
                    )
                    .stream()
                )

                alumnos_list = []

                for doc in alumnos_docs:

                    datos = doc.to_dict()

                    if (
                        datos.get(
                            "ciclo_lectivo",
                            CICLO_LECTIVO,
                        )
                        != CICLO_LECTIVO
                    ):
                        continue

                    alumnos_list.append(
                        datos
                    )

                alumnos_list.sort(
                    key=lambda x: x.get(
                        "apellidos",
                        "",
                    )
                )

                # --------------------------------------------
                # MAESTRO GUÍA DEL CICLO
                # --------------------------------------------

                guia_docs = (
                    db.collection(
                        "carga_academica"
                    )
                    .where(
                        "grado",
                        "==",
                        grado_lote,
                    )
                    .where(
                        "es_guia",
                        "==",
                        True,
                    )
                    .stream()
                )

                maestro_guia = "No Asignado"

                for doc in guia_docs:

                    datos_guia = doc.to_dict()

                    if (
                        datos_guia.get(
                            "ciclo_lectivo",
                            2026,
                        )
                        == CICLO_LECTIVO
                    ):

                        maestro_guia = (
                            datos_guia.get(
                                "nombre_docente",
                                "No Asignado",
                            )
                        )

                        break

                # --------------------------------------------
                # MAPA DE NOTAS
                # --------------------------------------------

                notas_ref = (
                    db.collection("notas")
                    .where(
                        "grado",
                        "==",
                        grado_lote,
                    )
                    .stream()
                )

                mapa_notas_global = {}

                for documento in notas_ref:

                    nota = documento.to_dict()

                    if (
                        nota.get(
                            "ciclo_lectivo",
                            2026,
                        )
                        != CICLO_LECTIVO
                    ):
                        continue

                    nie = nota["nie"]
                    materia = nota["materia"]
                    mes = nota["mes"]
                    valor = nota[
                        "promedio_final"
                    ]

                    mapa_notas_global.setdefault(
                        nie,
                        {},
                    )

                    mapa_notas_global[
                        nie
                    ].setdefault(
                        materia,
                        {},
                    )

                    mapa_notas_global[
                        nie
                    ][materia][mes] = valor

                # --------------------------------------------
                # GENERAR BOLETAS
                # --------------------------------------------

                logo_b64 = get_base64(
                    "logo.png"
                )

                imagen_logo = (
                    f'<img src="{logo_b64}" height="45">'
                    if logo_b64
                    else ""
                )

                html_masivo = ""

                for indice, alumno in enumerate(
                    alumnos_list
                ):

                    notas_alumno = (
                        mapa_notas_global.get(
                            alumno["nie"],
                            {},
                        )
                    )

                    filas_notas = ""

                    for materia in materias_seleccionadas:

                        notas = (
                            notas_alumno.get(
                                materia,
                                {},
                            )
                        )

                        t1 = redondear_mined(
                            (
                                notas.get(
                                    "Febrero",
                                    0,
                                )
                                + notas.get(
                                    "Marzo",
                                    0,
                                )
                                + notas.get(
                                    "Abril",
                                    0,
                                )
                            ) / 3
                        )

                        t2 = redondear_mined(
                            (
                                notas.get(
                                    "Mayo",
                                    0,
                                )
                                + notas.get(
                                    "Junio",
                                    0,
                                )
                                + notas.get(
                                    "Julio",
                                    0,
                                )
                            ) / 3
                        )

                        t3 = redondear_mined(
                            (
                                notas.get(
                                    "Agosto",
                                    0,
                                )
                                + notas.get(
                                    "Septiembre",
                                    0,
                                )
                                + notas.get(
                                    "Octubre",
                                    0,
                                )
                            ) / 3
                        )

                        final = redondear_mined(
                            (t1 + t2 + t3) / 3
                        )

                        filas_notas += f"""
                        <tr>

                            <td style="
                                text-align:left;
                                padding-left:5px;
                            ">
                                {materia}
                            </td>

                            <td>{notas.get('Febrero', '-')}</td>
                            <td>{notas.get('Marzo', '-')}</td>
                            <td>{notas.get('Abril', '-')}</td>

                            <td class="trimestre">
                                {t1}
                            </td>

                            <td>{notas.get('Mayo', '-')}</td>
                            <td>{notas.get('Junio', '-')}</td>
                            <td>{notas.get('Julio', '-')}</td>

                            <td class="trimestre">
                                {t2}
                            </td>

                            <td>{notas.get('Agosto', '-')}</td>
                            <td>{notas.get('Septiembre', '-')}</td>
                            <td>{notas.get('Octubre', '-')}</td>

                            <td class="trimestre">
                                {t3}
                            </td>

                            <td class="final">
                                {final}
                            </td>

                        </tr>
                        """

                    boleta_html = f"""
                    <div class="boleta-container">

                        <div style="
                            display:flex;
                            align-items:center;
                            border-bottom:1px solid black;
                            margin-bottom:8px;
                        ">

                            {imagen_logo}

                            <div style="margin-left:15px;">

                                <h2 style="
                                    margin:0;
                                    font-size:16px;
                                ">
                                    COLEGIO PROFA. BLANCA ELENA
                                    DE HERNÁNDEZ
                                </h2>

                                <h4 style="
                                    margin:0;
                                    color:#444;
                                ">
                                    INFORME DE RENDIMIENTO
                                    ACADÉMICO - {CICLO_LECTIVO}
                                </h4>

                            </div>

                        </div>

                        <table style="
                            width:100%;
                            font-size:11px;
                            margin-bottom:8px;
                        ">

                            <tr>
                                <td>
                                    <b>ALUMNO:</b>
                                    {alumno.get('apellidos', '')}
                                    {alumno.get('nombres', '')}
                                </td>

                                <td style="text-align:right;">
                                    <b>GRADO:</b>
                                    {grado_lote}
                                </td>
                            </tr>

                            <tr>
                                <td>
                                    <b>NIE:</b>
                                    {alumno.get('nie')}
                                </td>

                                <td style="text-align:right;">
                                    <b>GUÍA:</b>
                                    {maestro_guia}
                                </td>
                            </tr>

                        </table>

                        <table
                            border="1"
                            style="
                                width:100%;
                                border-collapse:collapse;
                                text-align:center;
                                font-size:10px;
                            "
                        >

                            <tr style="
                                background:#f2f2f2;
                                font-weight:bold;
                            ">
                                <td width="25%">ASIGNATURA</td>

                                <td>FEB</td>
                                <td>MAR</td>
                                <td>ABR</td>
                                <td>T1</td>

                                <td>MAY</td>
                                <td>JUN</td>
                                <td>JUL</td>
                                <td>T2</td>

                                <td>AGO</td>
                                <td>SEP</td>
                                <td>OCT</td>
                                <td>T3</td>

                                <td>PF</td>
                            </tr>

                            {filas_notas}

                        </table>

                        <div style="
                            display:flex;
                            justify-content:space-around;
                            margin-top:40px;
                        ">

                            <div style="
                                width:40%;
                                border-top:1px solid black;
                                text-align:center;
                                font-size:10px;
                            ">
                                <br>
                                F. Maestro Orientador
                            </div>

                            <div style="
                                width:40%;
                                border-top:1px solid black;
                                text-align:center;
                                font-size:10px;
                            ">
                                <br>
                                F. Dirección / Sello
                            </div>

                        </div>

                    </div>

                    <div class="cut-line">
                        ✂-------------------------------------------------------------✂
                    </div>
                    """

                    html_masivo += boleta_html

                    if (indice + 1) % 2 == 0:
                        html_masivo += (
                            '<div class="page-break"></div>'
                        )

                full_html = f"""
                <html>

                <head>

                    <style>

                        @page {{
                            size: letter;
                            margin: 0.5cm;
                        }}

                        body {{
                            font-family:
                                'Segoe UI',
                                Tahoma,
                                Geneva,
                                Verdana,
                                sans-serif;
                            margin:0;
                        }}

                        .boleta-container {{
                            height:46%;
                            padding:20px;
                            box-sizing:border-box;
                            position:relative;
                        }}

                        .trimestre {{
                            background-color:#f8f9fa;
                            font-weight:bold;
                        }}

                        .final {{
                            background-color:#1e3a8a;
                            color:white;
                            font-weight:bold;
                        }}

                        .cut-line {{
                            width:100%;
                            text-align:center;
                            color:#999;
                            font-size:12px;
                            height:2%;
                            border-bottom:
                                1px dashed #ccc;
                            margin-bottom:10px;
                        }}

                        .page-break {{
                            page-break-after:always;
                        }}

                        @media print {{

                            button {{
                                display:none;
                            }}

                            .cut-line {{
                                border-bottom:
                                    1px dashed #000;
                            }}

                        }}

                    </style>

                </head>

                <body>

                    {html_masivo}

                    <br>

                    <center>
                        <button
                            onclick="window.print()"
                            style="
                                padding:15px 30px;
                                background:#2e7d32;
                                color:white;
                                border:none;
                                border-radius:5px;
                                font-size:16px;
                                cursor:pointer;
                            "
                        >
                            🖨️ IMPRIMIR LOTE DE BOLETAS
                        </button>
                    </center>

                </body>

                </html>
                """

                components.html(
                    full_html,
                    height=800,
                    scrolling=True,
                )