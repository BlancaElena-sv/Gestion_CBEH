import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

def eliminar_documentos_consulta(query):
    """
    Elimina todos los documentos devueltos
    por una consulta de Firestore.
    """

    documentos = list(query.stream())

    for documento in documentos:
        documento.reference.delete()

    return len(documentos)

def mostrar_consulta_alumnos(
    db,
    lista_grados,
    mapa_curricular,
    redondear_mined,
    get_base64,
    obtener_fecha_hoy,
    subir_archivo,
):
    """
    Vista del expediente electrónico del alumno.

    Permite:
    - Buscar alumnos por NIE o grado.
    - Consultar datos y documentos.
    - Consultar historial financiero.
    - Generar solvencia.
    - Consultar/imprimir boleta.
    - Editar expediente.
    - Consultar bitácora.
    """

    st.title("🔎 Expediente Electrónico")

    col_search, col_res = st.columns([1, 3])

    with col_search:
        st.markdown("### 🔍 Búsqueda")

        metodo = st.radio(
            "Criterio:",
            ["NIE", "Grado"]
        )

        if metodo == "NIE":
            val = st.text_input("Ingrese NIE:")

            if st.button("Buscar Expediente") and val:
                d = db.collection("alumnos").document(val).get()

                if d.exists:
                    st.session_state.alum_view = d.to_dict()
                else:
                    st.error("No existe")

        else:
            g = st.selectbox(
                "Filtrar Grado",
                ["Todos"] + lista_grados
            )

            if g != "Todos":
                res = [
                    d.to_dict()
                    for d in db.collection("alumnos")
                    .where("grado_actual", "==", g)
                    .stream()
                ]
            else:
                res = [
                    d.to_dict()
                    for d in db.collection("alumnos")
                    .limit(20)
                    .stream()
                ]

            sel = st.selectbox(
                "Seleccionar Alumno",
                ["Seleccionar..."]
                + [
                    f"{r['nie']} - "
                    f"{r.get('apellidos', '')} "
                    f"{r.get('nombres', '')}"
                    for r in res
                ]
            )

            if sel != "Seleccionar...":
                nie_sel = sel.split(" - ")[0]

                st.session_state.alum_view = (
                    db.collection("alumnos")
                    .document(nie_sel)
                    .get()
                    .to_dict()
                )

    # ==========================================
    # EXPEDIENTE
    # ==========================================

    if "alum_view" not in st.session_state:
        st.info(
            "Busque un alumno por NIE o seleccione uno por grado "
            "para visualizar su expediente."
        )
        return

    a = st.session_state.alum_view

    q_guia = (
        db.collection("carga_academica")
        .where("grado", "==", a["grado_actual"])
        .where("es_guia", "==", True)
        .stream()
    )

    maestro_guia = "No Asignado"

    for d in q_guia:
        maestro_guia = d.to_dict()["nombre_docente"]

    st.markdown("---")

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 3, 2])

        with c1:
            foto_url_alum = (
                a.get("documentos", {})
                .get("foto_url")
            )

            if not foto_url_alum:
                foto_url_alum = "https://via.placeholder.com/150"

            st.image(foto_url_alum, width=130)

        with c2:
            st.title(
                f"{a.get('apellidos', '')} "
                f"{a.get('nombres', '')}"
            )

            st.markdown(f"#### **NIE:** {a['nie']}")

            st.markdown(
                f"**Grado:** {a['grado_actual']} | "
                f"**Turno:** {a.get('turno')}"
            )

            st.markdown(
                f"**Ciclo Lectivo:** "
                f"{a.get('ciclo_lectivo', 'No definido')}" 
            )

            st.info(
                f"👨‍🏫 **Maestro Guía:** {maestro_guia}"
            )

        with c3:
            estado = a.get("estado", "Activo")
            color = "green" if estado == "Activo" else "red"

            st.markdown(
                f"""
                <h3 style="
                    color:{color};
                    text-align:center;
                    border:2px solid {color};
                    padding:5px;
                    border-radius:10px;
                ">
                    {estado.upper()}
                </h3>
                """,
                unsafe_allow_html=True
            )

    tabs = st.tabs(
    [
        "📋 Datos y Documentos",
        "💰 Historial y Solvencia",
        "📊 Boleta de Notas",
        "⚙️ Edición Expediente",
        "📒 Bitácora",
        "🛡️ Estado y Baja",
        "📚 Historial Académico",
    ]
)

        # ==========================================
    # TAB 1 - DATOS Y DOCUMENTOS
    # ==========================================

    with tabs[0]:
        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.subheader("Datos Personales")

            st.write(
                f"**Responsable:** "
                f"{a.get('encargado', {}).get('nombre')}"
            )

            st.write(
                f"**Teléfono:** "
                f"{a.get('encargado', {}).get('telefono')}"
            )

            st.write(
                f"**Dirección:** "
                f"{a.get('encargado', {}).get('direccion')}"
            )

        with col_d2:
            st.subheader("📂 Documentos")

            documentos = a.get("documentos", {})
            docs = list(documentos.get("doc_urls", []))

            doc_url_antiguo = documentos.get("doc_url")

            if doc_url_antiguo:
                docs.append(doc_url_antiguo)

            if docs:
                for i, url in enumerate(set(docs), start=1):
                    with st.expander(
                        f"👁️ Visualizar Documento {i}"
                    ):
                        g_view = (
                            "https://docs.google.com/gview"
                            f"?embedded=true&url={url}"
                        )

                        st.markdown(
                            f"""
                            <iframe
                                src="{g_view}"
                                width="100%"
                                height="500px"
                                style="border:none;">
                            </iframe>
                            """,
                            unsafe_allow_html=True
                        )

                        st.caption(
                            f"[Enlace Directo]({url})"
                        )

            else:
                st.info("Sin documentos.")

    # ==========================================
    # TAB 2 - HISTORIAL Y SOLVENCIA
    # ==========================================

    with tabs[1]:
        col_fin1, col_fin2 = st.columns([2, 1])

        with col_fin1:
            st.subheader("Historial de Pagos")

            pagos = (
                db.collection("finanzas")
                .where("alumno_nie", "==", a["nie"])
                .where("tipo", "==", "ingreso")
                .stream()
            )

            raw_pagos = [
                {"id": p.id, **p.to_dict()}
                for p in pagos
            ]

            if raw_pagos:
                df_pagos = pd.DataFrame(raw_pagos)

                st.dataframe(
                    df_pagos[
                        [
                            "fecha_legible",
                            "descripcion",
                            "monto",
                        ]
                    ],
                    width="stretch"
                )

                st.write("---")
                st.write(
                    "**🖨️ Reimprimir Recibo Histórico**"
                )

                opciones_recibo = {
                    (
                        f"{p['fecha_legible']} - "
                        f"{p['descripcion']} "
                        f"(${p['monto']})"
                    ): p
                    for p in raw_pagos
                }

                sel_recibo = st.selectbox(
                    "Seleccione un pago:",
                    ["Seleccionar..."]
                    + list(opciones_recibo.keys())
                )

                if sel_recibo != "Seleccionar...":
                    p_obj = opciones_recibo[sel_recibo]

                    if st.button(
                        "Visualizar Recibo",
                        key="btn_visualizar_recibo_alumno"
                    ):
                        logo = get_base64("logo.png")

                        hi = (
                            f'<img src="{logo}" height="60">'
                            if logo
                            else ""
                        )

                        html_recibo = f"""
                        <div style="
                            border:2px solid #333;
                            padding:20px;
                            font-family:Helvetica, sans-serif;
                            max-width:700px;
                            margin:auto;
                        ">
                            <table width="100%">
                                <tr>
                                    <td width="20%">
                                        {hi}
                                    </td>

                                    <td width="60%" align="center">
                                        <h3 style="margin:0;">
                                            COLEGIO PROFA. BLANCA ELENA
                                            DE HERNÁNDEZ
                                        </h3>

                                        <p style="
                                            margin:5px;
                                            font-size:12px;
                                        ">
                                            San Felipe, San Bartolo,
                                            Ilopango
                                        </p>

                                        <p style="
                                            margin:0;
                                            font-size:12px;
                                        ">
                                            <b>
                                                COMPROBANTE DE INGRESO
                                                (COPIA)
                                            </b>
                                        </p>
                                    </td>

                                    <td width="20%" align="right">
                                        <h4 style="
                                            margin:0;
                                            color:#d32f2f;
                                        ">
                                            NO.
                                            {p_obj.get(
                                                'id_short',
                                                '000'
                                            )}
                                        </h4>

                                        <p style="font-size:12px;">
                                            {p_obj['fecha_legible']}
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <hr>

                            <div style="padding:10px;">
                                <p>
                                    <b>RECIBIMOS DE:</b>
                                    {p_obj.get('nombre_persona')}
                                </p>

                                <p>
                                    <b>LA CANTIDAD DE:</b>
                                    <span style="
                                        font-size:18px;
                                        font-weight:bold;
                                    ">
                                        ${p_obj['monto']:.2f}
                                    </span>
                                </p>

                                <p>
                                    <b>POR CONCEPTO DE:</b>
                                    {p_obj['descripcion']}
                                </p>
                            </div>

                            <br><br>

                            <table width="100%">
                                <tr>
                                    <td
                                        align="center"
                                        style="
                                            border-top:1px solid #000;
                                            width:40%;
                                        "
                                    >
                                        Entregado Por
                                    </td>

                                    <td width="20%"></td>

                                    <td
                                        align="center"
                                        style="
                                            border-top:1px solid #000;
                                            width:40%;
                                        "
                                    >
                                        Recibido (Caja)
                                    </td>
                                </tr>
                            </table>
                        </div>
                        """

                        components.html(
                            f"""
                            <html>
                                <body>
                                    {html_recibo}
                                    <br>
                                    <center>
                                        <button
                                            onclick="window.print()"
                                        >
                                            🖨️ IMPRIMIR COPIA
                                        </button>
                                    </center>
                                </body>
                            </html>
                            """,
                            height=400,
                            scrolling=True
                        )

            else:
                st.info("Sin pagos registrados.")

        with col_fin2:
            st.markdown("### 🎫 Solvencia")

            periodo = st.selectbox(
                "Examen:",
                [
                    "I Trimestre",
                    "II Trimestre",
                    "III Trimestre",
                    "Final",
                ]
            )

            if st.button(
                "Generar Taco",
                key="btn_generar_taco"
            ):
                fecha = (
                    obtener_fecha_hoy()
                    .strftime("%d/%m/%Y")
                )

                logo = get_base64("logo.png")

                hi = (
                    f'<img src="{logo}" height="40">'
                    if logo
                    else ""
                )

                html = f"""
                <div style="
                    font-family:monospace;
                    width:300px;
                    margin:auto;
                    padding:10px;
                    border:1px dashed black;
                    text-align:center;
                ">
                    <div style="
                        display:flex;
                        align-items:center;
                        justify-content:center;
                    ">
                        {hi}
                        <b>COLEGIO BLANCA ELENA</b>
                    </div>

                    <h4 style="
                        background:black;
                        color:white;
                        margin:5px 0;
                    ">
                        SOLVENCIA EXAMEN
                    </h4>

                    <div style="
                        text-align:left;
                        font-size:11px;
                    ">
                        <b>ALUMNO:</b>
                        {a.get('apellidos', '')}
                        {a.get('nombres', '')}
                        <br>

                        <b>NIE:</b>
                        {a['nie']}
                        <br>

                        <b>PERIODO:</b>
                        {periodo}
                        <br>

                        <b>ESTADO:</b>
                        SOLVENTE ✅
                    </div>

                    <br>

                    <table
                        border="1"
                        style="
                            width:100%;
                            font-size:10px;
                            border-collapse:collapse;
                            text-align:center;
                        "
                    >
                        <tr>
                            <td>LUN</td>
                            <td>MAR</td>
                            <td>MIE</td>
                            <td>JUE</td>
                            <td>VIE</td>
                        </tr>

                        <tr>
                            <td height="30"></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                        </tr>
                    </table>

                    <br>

                    <span style="font-size:9px;">
                        Fecha: {fecha}
                    </span>
                </div>
                """

                components.html(
                    f"""
                    <html>
                        <body>
                            {html}
                            <br>

                            <center>
                                <button onclick="window.print()">
                                    🖨️ IMPRIMIR
                                </button>
                            </center>
                        </body>
                    </html>
                    """,
                    height=350
                )

    # ==========================================
    # TAB 3 - BOLETA
    # ==========================================

    with tabs[2]:
        st.subheader("Boleta Oficial")

        notas = (
            db.collection("notas")
            .where("nie", "==", a["nie"])
            .stream()
        )

        nm = {}

        for doc in notas:
            dd = doc.to_dict()

            if dd["materia"] not in nm:
                nm[dd["materia"]] = {}

            nm[dd["materia"]][dd["mes"]] = (
                dd["promedio_final"]
            )

        filas = []

        malla = mapa_curricular.get(
            a["grado_actual"],
            []
        )

        for mat in malla:
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
                        <td style="text-align:left">
                            {mat}
                        </td>

                        <td>{n.get('Febrero', '-')}</td>
                        <td>{n.get('Marzo', '-')}</td>
                        <td>{n.get('Abril', '-')}</td>

                        <td style="background:#eee">
                            <b>{t1}</b>
                        </td>

                        <td>{n.get('Mayo', '-')}</td>
                        <td>{n.get('Junio', '-')}</td>
                        <td>{n.get('Julio', '-')}</td>

                        <td style="background:#eee">
                            <b>{t2}</b>
                        </td>

                        <td>{n.get('Agosto', '-')}</td>
                        <td>{n.get('Septiembre', '-')}</td>
                        <td>{n.get('Octubre', '-')}</td>

                        <td style="background:#eee">
                            <b>{t3}</b>
                        </td>

                        <td style="
                            background:#333;
                            color:white;
                        ">
                            <b>{fin}</b>
                        </td>
                    </tr>
                    """
                )

        logo = get_base64("logo.png")
        sello = get_base64("sello.png")

        hi = (
            f'<img src="{logo}" height="60">'
            if logo
            else ""
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
                    </h4>
                </div>
            </div>

            <p>
                <b>Alumno:</b>
                {a.get('apellidos', '')}
                {a.get('nombres', '')}

                |

                <b>Grado:</b>
                {a['grado_actual']}

                |

                <b>Guía:</b>
                {maestro_guia}
            </p>

            <table
                border="1"
                style="
                    width:100%;
                    border-collapse:collapse;
                    text-align:center;
                "
            >
                <tr style="
                    background:#ddd;
                    font-weight:bold;
                ">
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

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:end;
                padding:0 50px;
            ">
                <div style="
                    text-align:center;
                    width:30%;
                ">
                    <div style="
                        border-top:1px solid black;
                        width:100%;
                    ">
                        Orientador
                    </div>
                </div>

                <div style="text-align:center;">
                    {hs}
                </div>

                <div style="
                    text-align:center;
                    width:30%;
                ">
                    <div style="
                        border-top:1px solid black;
                        width:100%;
                    ">
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

                    <button onclick="window.print()">
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

    # ==========================================
    # TAB 4 - EDICIÓN
    # ==========================================

    with tabs[3]:
        st.subheader("Gestión del Expediente")

        with st.form("edit_full"):
            c1, c2 = st.columns(2)

            nn = c1.text_input(
                "Nombres",
                a["nombres"]
            )

            na = c2.text_input(
                "Apellidos",
                a["apellidos"]
            )

            indice_grado = (
                lista_grados.index(a["grado_actual"])
                if a["grado_actual"] in lista_grados
                else 0
            )

            ng = c1.selectbox(
                "Grado",
                lista_grados,
                index=indice_grado
            )

            turnos = [
                "Matutino",
                "Vespertino",
            ]

            turno_actual = a.get(
                "turno",
                "Matutino"
            )

            indice_turno = (
                turnos.index(turno_actual)
                if turno_actual in turnos
                else 0
            )

            nt = c2.selectbox(
                "Turno",
                turnos,
                index=indice_turno
            )

            estados = [
                "Activo",
                "Inactivo",
                "Retirado",
            ]

            estado_actual = a.get(
                "estado",
                "Activo"
            )

            indice_estado = (
                estados.index(estado_actual)
                if estado_actual in estados
                else 0
            )

            ne = c1.selectbox(
                "Estado",
                estados,
                index=indice_estado
            )

            nres = c2.text_input(
                "Responsable",
                a.get(
                    "encargado",
                    {}
                ).get(
                    "nombre",
                    ""
                )
            )

            ntel = c1.text_input(
                "Teléfono",
                a.get(
                    "encargado",
                    {}
                ).get(
                    "telefono",
                    ""
                )
            )

            ndir = c2.text_area(
                "Dirección",
                a.get(
                    "encargado",
                    {}
                ).get(
                    "direccion",
                    ""
                )
            )

            st.markdown("---")

            new_foto = st.file_uploader(
                "Actualizar Foto",
                ["jpg", "png"],
                key="up_foto"
            )

            new_doc = st.file_uploader(
                "Adjuntar Documento",
                ["pdf", "jpg", "png"],
                key="up_doc"
            )

            if st.form_submit_button(
                "💾 Guardar Cambios"
            ):
                update_data = {
                    "nombres": nn,
                    "apellidos": na,
                    "nombre_completo": (
                        f"{na} {nn}"
                    ),
                    "grado_actual": ng,
                    "turno": nt,
                    "estado": ne,
                    "encargado": {
                        "nombre": nres,
                        "telefono": ntel,
                        "direccion": ndir,
                    },
                }

                if new_foto:
                    url = subir_archivo(
                        new_foto,
                        f"expedientes/{a['nie']}"
                    )

                    if url:
                        update_data[
                            "documentos.foto_url"
                        ] = url

                if new_doc:
                    url = subir_archivo(
                        new_doc,
                        f"expedientes/{a['nie']}"
                    )

                    if url:
                        cds = list(
                            a.get(
                                "documentos",
                                {}
                            ).get(
                                "doc_urls",
                                []
                            )
                        )

                        cds.append(url)

                        update_data[
                            "documentos.doc_urls"
                        ] = cds

                db.collection(
                    "alumnos"
                ).document(
                    a["nie"]
                ).update(
                    update_data
                )

                # Actualizar también la copia de sesión
                st.session_state.alum_view = (
                    db.collection("alumnos")
                    .document(a["nie"])
                    .get()
                    .to_dict()
                )

                st.success(
                    "Expediente actualizado."
                )

                time.sleep(1)
                st.rerun()

    # ==========================================
    # TAB 5 - BITÁCORA
    # ==========================================

    with tabs[4]:
        st.markdown(
            "### 📒 Bitácora del Alumno"
        )

        logs = (
            db.collection("bitacora")
            .where("nie", "==", a["nie"])
            .stream()
        )

        lista_logs = [
            l.to_dict()
            for l in logs
        ]

        lista_logs.sort(
            key=lambda x: x.get(
                "fecha_legible",
                ""
            ),
            reverse=True
        )

        if lista_logs:
            for log in lista_logs:
                with st.container(border=True):
                    c_meta, c_body = st.columns(
                        [1, 3]
                    )

                    with c_meta:
                        st.caption(
                            f"📅 "
                            f"{log.get('fecha_legible')}"
                        )

                        st.caption(
                            f"✍️ **"
                            f"{log.get('autor')}"
                            f"**"
                        )

                    with c_body:
                        st.write(
                            log.get("contenido")
                        )

        else:
            st.info(
                "No hay registros en la bitácora."
            )
        # ==========================================
    # TAB 6 - ESTADO, BAJA Y ELIMINACIÓN
    # ==========================================

    with tabs[5]:

        st.subheader("🛡️ Gestión del Estado del Alumno")

        estado_actual = a.get(
            "estado",
            "Activo"
        )

        col_estado, col_info = st.columns(
            [1, 2]
        )

        with col_estado:

            if estado_actual == "Activo":
                st.success(
                    "✅ Alumno actualmente ACTIVO"
                )

            elif estado_actual == "Retirado":
                st.warning(
                    "⚠️ Alumno dado de BAJA"
                )

            else:
                st.info(
                    f"Estado actual: {estado_actual}"
                )

        with col_info:

            if a.get("fecha_baja"):
                st.write(
                    f"**Fecha de baja:** "
                    f"{a.get('fecha_baja')}"
                )

            if a.get("motivo_baja"):
                st.write(
                    f"**Motivo:** "
                    f"{a.get('motivo_baja')}"
                )

            if a.get("baja_realizada_por"):
                st.write(
                    f"**Registrado por:** "
                    f"{a.get('baja_realizada_por')}"
                )

        st.divider()

            # ==========================================
    # TAB 7 - HISTORIAL ACADÉMICO
    # ==========================================

    with tabs[6]:

        st.subheader("📚 Historial Académico")

        historial = a.get(
            "historial_academico",
            []
        )

        if not historial:

            st.info(
                "Este alumno todavía no tiene "
                "registros históricos de promoción."
            )

            st.caption(
                "El historial comenzará a generarse "
                "cuando se ejecute una promoción de grado."
            )

        else:

            # Ordenar de más reciente a más antiguo
            historial_ordenado = sorted(
                historial,
                key=lambda registro: registro.get(
                    "ciclo",
                    0
                ),
                reverse=True
            )

            filas = []

            for registro in historial_ordenado:

                resultado = registro.get(
                    "resultado",
                    "-"
                )

                grado = registro.get(
                    "grado",
                    "-"
                )

                grado_destino = registro.get(
                    "grado_destino",
                    "-"
                )

                ciclo = registro.get(
                    "ciclo",
                    "-"
                )

                ciclo_destino = registro.get(
                    "ciclo_destino",
                    "-"
                )

                fecha = registro.get(
                    "fecha",
                    "-"
                )

                usuario = registro.get(
                    "usuario",
                    "-"
                )

                if resultado == "Graduado":
                    destino_mostrar = "Graduado"
                else:
                    destino_mostrar = grado_destino

                filas.append(
                    {
                        "Ciclo": ciclo,
                        "Grado cursado": grado,
                        "Resultado": resultado,
                        "Destino": destino_mostrar,
                        "Ciclo destino": ciclo_destino,
                        "Fecha": fecha,
                        "Procesado por": usuario,
                    }
                )

            df_historial = pd.DataFrame(
                filas
            )

            st.dataframe(
                df_historial,
                width="stretch",
                hide_index=True
            )

            st.divider()

            st.markdown(
                "### 📖 Trayectoria del alumno"
            )

            for registro in historial_ordenado:

                ciclo = registro.get(
                    "ciclo",
                    "-"
                )

                grado = registro.get(
                    "grado",
                    "-"
                )

                resultado = registro.get(
                    "resultado",
                    "-"
                )

                grado_destino = registro.get(
                    "grado_destino",
                    ""
                )

                if resultado == "Graduado":

                    st.success(
                        f"🎓 {ciclo} · "
                        f"{grado} · "
                        f"Graduado"
                    )

                elif resultado == "Promovido":

                    st.info(
                        f"📘 {ciclo} · "
                        f"{grado} → "
                        f"{grado_destino}"
                    )

                else:

                    st.write(
                        f"{ciclo} · "
                        f"{grado} · "
                        f"{resultado}"
                    )

        # ==========================================
        # DAR DE BAJA
        # ==========================================

        st.markdown("### 🟠 Dar de baja")

        st.caption(
            "Esta opción conserva completamente el expediente "
            "académico, financiero y administrativo del alumno."
        )

        motivos_baja = [
            "Retiro voluntario",
            "Cambio de institución",
            "Finalización de estudios",
            "Inasistencia prolongada",
            "Razones económicas",
            "Otro",
        ]

        motivo = st.selectbox(
            "Motivo de baja",
            motivos_baja,
            key=f"motivo_baja_{a['nie']}"
        )

        motivo_otro = ""

        if motivo == "Otro":
            motivo_otro = st.text_input(
                "Especifique el motivo",
                key=f"motivo_otro_{a['nie']}"
            )

        if estado_actual == "Activo":

            if st.button(
                "🟠 Dar de baja al alumno",
                key=f"btn_baja_{a['nie']}"
            ):

                motivo_final = (
                    motivo_otro.strip()
                    if motivo == "Otro"
                    else motivo
                )

                if (
                    motivo == "Otro"
                    and not motivo_final
                ):

                    st.error(
                        "Debe especificar el motivo."
                    )

                else:

                    datos_baja = {
                        "estado": "Retirado",
                        "activo": False,
                        "fecha_baja": (
                            obtener_fecha_hoy()
                            .strftime("%d/%m/%Y")
                        ),
                        "motivo_baja": motivo_final,
                        "baja_realizada_por": (
                            st.session_state.get(
                                "user_name",
                                "Administrador"
                            )
                        ),
                    }

                    db.collection(
                        "alumnos"
                    ).document(
                        a["nie"]
                    ).update(
                        datos_baja
                    )

                    st.session_state.alum_view.update(
                        datos_baja
                    )

                    st.success(
                        "✅ Alumno dado de baja correctamente."
                    )

                    time.sleep(1)
                    st.rerun()

        else:

            st.info(
                "El alumno ya se encuentra dado de baja."
            )

            if st.button(
                "♻️ Reactivar alumno",
                key=f"btn_reactivar_{a['nie']}"
            ):

                datos_reactivacion = {
                    "estado": "Activo",
                    "activo": True,
                    "fecha_baja": None,
                    "motivo_baja": None,
                    "baja_realizada_por": None,
                }

                db.collection(
                    "alumnos"
                ).document(
                    a["nie"]
                ).update(
                    datos_reactivacion
                )

                st.session_state.alum_view.update(
                    datos_reactivacion
                )

                st.success(
                    "✅ Alumno reactivado."
                )

                time.sleep(1)
                st.rerun()

        # ==========================================
        # ZONA DE PELIGRO
        # ==========================================

        st.divider()

        st.markdown("### 🔴 Zona de peligro")

        st.error(
            "La eliminación definitiva no se puede deshacer. "
            "Se eliminarán también notas, pagos y bitácora "
            "relacionados con este alumno."
        )

        st.write(
            f"Para confirmar escriba el NIE: **{a['nie']}**"
        )

        confirmacion = st.text_input(
            "Confirmación",
            key=f"confirm_delete_{a['nie']}"
        )

        confirmar_eliminacion = st.checkbox(
            "Entiendo que esta acción es irreversible.",
            key=f"check_delete_{a['nie']}"
        )

        if st.button(
            "🗑️ ELIMINAR DEFINITIVAMENTE",
            key=f"delete_alumno_{a['nie']}"
        ):

            if confirmacion.strip() != str(
                a["nie"]
            ):

                st.error(
                    "El NIE escrito no coincide."
                )

            elif not confirmar_eliminacion:

                st.error(
                    "Debe confirmar que comprende "
                    "que la eliminación es irreversible."
                )

            else:

                try:

                    nie = a["nie"]

                    # ==================================
                    # 1. NOTAS INDIVIDUALES
                    # ==================================

                    notas_eliminadas = (
                        eliminar_documentos_consulta(
                            db.collection("notas")
                            .where(
                                "nie",
                                "==",
                                nie
                            )
                        )
                    )

                    # ==================================
                    # 2. FINANZAS
                    # ==================================

                    pagos_eliminados = (
                        eliminar_documentos_consulta(
                            db.collection("finanzas")
                            .where(
                                "alumno_nie",
                                "==",
                                nie
                            )
                        )
                    )

                    # ==================================
                    # 3. BITÁCORA
                    # ==================================

                    logs_eliminados = (
                        eliminar_documentos_consulta(
                            db.collection("bitacora")
                            .where(
                                "nie",
                                "==",
                                nie
                            )
                        )
                    )

                    # ==================================
                    # 4. NOTAS MENSUALES
                    # ==================================

                    notas_mensuales = (
                        db.collection(
                            "notas_mensuales"
                        ).stream()
                    )

                    for documento in notas_mensuales:

                        datos = documento.to_dict()

                        detalles = datos.get(
                            "detalles",
                            {}
                        )

                        if nie in detalles:

                            detalles.pop(
                                nie,
                                None
                            )

                            documento.reference.update(
                                {
                                    "detalles": detalles
                                }
                            )

                    # ==================================
                    # 5. ASISTENCIA
                    # ==================================

                    asistencias = (
                        db.collection(
                            "asistencia"
                        ).stream()
                    )

                    for documento in asistencias:

                        datos = documento.to_dict()

                        registros = datos.get(
                            "registros",
                            {}
                        )

                        observaciones = datos.get(
                            "observaciones",
                            {}
                        )

                        modificado = False

                        if nie in registros:
                            registros.pop(
                                nie,
                                None
                            )
                            modificado = True

                        if nie in observaciones:
                            observaciones.pop(
                                nie,
                                None
                            )
                            modificado = True

                        if modificado:

                            documento.reference.update(
                                {
                                    "registros": registros,
                                    "observaciones": (
                                        observaciones
                                    ),
                                }
                            )

                    # ==================================
                    # 6. DOCUMENTO PRINCIPAL
                    # ==================================

                    db.collection(
                        "alumnos"
                    ).document(
                        nie
                    ).delete()

                    # Limpiar sesión
                    if (
                        "alum_view"
                        in st.session_state
                    ):
                        del st.session_state[
                            "alum_view"
                        ]

                    st.success(
                        "✅ Alumno y registros relacionados "
                        "eliminados definitivamente."
                    )

                    st.write(
                        f"Notas eliminadas: "
                        f"{notas_eliminadas}"
                    )

                    st.write(
                        f"Movimientos financieros eliminados: "
                        f"{pagos_eliminados}"
                    )

                    st.write(
                        f"Registros de bitácora eliminados: "
                        f"{logs_eliminados}"
                    )

                    time.sleep(2)
                    st.rerun()

                except Exception as error:

                    st.error(
                        "No se pudo completar la eliminación: "
                        f"{error}"
                    )