import streamlit as st
import streamlit.components.v1 as components

from config import CICLO_LECTIVO


def _normalizar_ciclo(valor):
    if valor is None:
        return 2026
    try:
        return int(valor)
    except (TypeError, ValueError):
        return valor


def _obtener_nombre_alumno(db, nie):
    try:
        doc = db.collection("alumnos").document(str(nie)).get()
        if doc.exists:
            datos = doc.to_dict()
            nombre = f"{datos.get('apellidos', '')} {datos.get('nombres', '')}".strip()
            if nombre:
                return nombre
    except Exception:
        pass
    return f"Alumno NIE {nie}"


def _ordenar_materias(materias_encontradas, materias_curriculo):
    resultado = []
    for materia in materias_curriculo:
        if materia in materias_encontradas:
            resultado.append(materia)
    for materia in sorted(materias_encontradas):
        if materia not in resultado:
            resultado.append(materia)
    return resultado


def _calcular_promedios(notas_materia, redondear_mined):
    t1 = redondear_mined(
        (
            notas_materia.get("Febrero", 0)
            + notas_materia.get("Marzo", 0)
            + notas_materia.get("Abril", 0)
        ) / 3
    )
    t2 = redondear_mined(
        (
            notas_materia.get("Mayo", 0)
            + notas_materia.get("Junio", 0)
            + notas_materia.get("Julio", 0)
        ) / 3
    )
    t3 = redondear_mined(
        (
            notas_materia.get("Agosto", 0)
            + notas_materia.get("Septiembre", 0)
            + notas_materia.get("Octubre", 0)
        ) / 3
    )
    final = redondear_mined((t1 + t2 + t3) / 3)
    return t1, t2, t3, final


def mostrar_notas_historicas(
    db,
    lista_grados_notas,
    mapa_curricular,
    redondear_mined,
    get_base64,
):
    st.subheader("🕰️ Consulta Histórica de Notas")
    st.info(
        "Esta sección permite consultar ciclos anteriores "
        "sin modificar las calificaciones almacenadas."
    )

    ciclo_minimo = max(2000, CICLO_LECTIVO - 10)
    ciclos = list(range(CICLO_LECTIVO, ciclo_minimo - 1, -1))

    c1, c2 = st.columns(2)

    ciclo_seleccionado = c1.selectbox(
        "Ciclo lectivo",
        ciclos,
        key="hist_ciclo_notas",
    )

    grado_seleccionado = c2.selectbox(
        "Grado cursado",
        ["Seleccionar..."] + lista_grados_notas,
        key="hist_grado_notas",
    )

    if grado_seleccionado == "Seleccionar...":
        st.caption(
            "Seleccione un ciclo y un grado para consultar "
            "las calificaciones históricas."
        )
        return

    try:
        notas_docs = (
            db.collection("notas")
            .where("grado", "==", grado_seleccionado)
            .stream()
        )

        notas_ciclo = []

        for documento in notas_docs:
            datos = documento.to_dict()
            ciclo_nota = _normalizar_ciclo(datos.get("ciclo_lectivo"))
            if ciclo_nota == ciclo_seleccionado:
                notas_ciclo.append(datos)

    except Exception as error:
        st.error(f"No fue posible consultar las notas históricas: {error}")
        return

    if not notas_ciclo:
        st.warning(
            f"No se encontraron notas de {grado_seleccionado} "
            f"para el ciclo {ciclo_seleccionado}."
        )
        return

    mapa_alumnos = {}

    for nota in notas_ciclo:
        nie = str(nota.get("nie", "")).strip()
        materia = nota.get("materia")
        mes = nota.get("mes")
        valor = nota.get("promedio_final", 0)

        if not nie or not materia or not mes:
            continue

        mapa_alumnos.setdefault(nie, {})
        mapa_alumnos[nie].setdefault(materia, {})
        mapa_alumnos[nie][materia][mes] = valor

    if not mapa_alumnos:
        st.warning(
            "Los registros encontrados no contienen información suficiente."
        )
        return

    opciones_alumnos = {}

    with st.spinner("Preparando alumnos del ciclo seleccionado..."):
        for nie in mapa_alumnos:
            nombre = _obtener_nombre_alumno(db, nie)
            opciones_alumnos[f"{nombre} - NIE {nie}"] = nie

    alumno_etiqueta = st.selectbox(
        "Alumno",
        ["Seleccionar..."] + sorted(opciones_alumnos.keys()),
        key="hist_alumno_notas",
    )

    if alumno_etiqueta == "Seleccionar...":
        return

    nie_seleccionado = opciones_alumnos[alumno_etiqueta]
    notas_alumno = mapa_alumnos[nie_seleccionado]
    nombre_alumno = _obtener_nombre_alumno(db, nie_seleccionado)

    maestro_guia = "No Asignado"

    try:
        guias = (
            db.collection("carga_academica")
            .where("grado", "==", grado_seleccionado)
            .where("es_guia", "==", True)
            .stream()
        )

        for documento in guias:
            datos_guia = documento.to_dict()
            ciclo_guia = _normalizar_ciclo(
                datos_guia.get("ciclo_lectivo")
            )

            if ciclo_guia == ciclo_seleccionado:
                maestro_guia = datos_guia.get(
                    "nombre_docente",
                    "No Asignado",
                )
                break
    except Exception:
        pass

    materias_encontradas = set(notas_alumno.keys())
    materias_curriculo = mapa_curricular.get(grado_seleccionado, [])
    materias = _ordenar_materias(
        materias_encontradas,
        materias_curriculo,
    )

    st.divider()
    st.markdown(f"### 📘 {nombre_alumno}")

    c_info1, c_info2, c_info3 = st.columns(3)
    c_info1.metric("Ciclo", ciclo_seleccionado)
    c_info2.metric("Grado cursado", grado_seleccionado)
    c_info3.metric("NIE", nie_seleccionado)

    st.caption(f"👨‍🏫 Maestro guía del ciclo: {maestro_guia}")

    filas_pantalla = []

    for materia in materias:
        notas = notas_alumno.get(materia, {})
        t1, t2, t3, final = _calcular_promedios(
            notas,
            redondear_mined,
        )

        filas_pantalla.append(
            {
                "Asignatura": materia,
                "Feb": notas.get("Febrero", "-"),
                "Mar": notas.get("Marzo", "-"),
                "Abr": notas.get("Abril", "-"),
                "T1": t1,
                "May": notas.get("Mayo", "-"),
                "Jun": notas.get("Junio", "-"),
                "Jul": notas.get("Julio", "-"),
                "T2": t2,
                "Ago": notas.get("Agosto", "-"),
                "Sep": notas.get("Septiembre", "-"),
                "Oct": notas.get("Octubre", "-"),
                "T3": t3,
                "PF": final,
            }
        )

    st.dataframe(
        filas_pantalla,
        width="stretch",
        hide_index=True,
    )

    st.warning(
        "🔒 Consulta en modo solo lectura. "
        "Las notas históricas no pueden editarse desde esta pantalla."
    )

    st.divider()
    st.markdown("### 🖨️ Boleta histórica")

    materias_boleta = st.multiselect(
        "Materias a incluir",
        options=materias,
        default=materias,
        key="hist_materias_boleta",
    )

    if not materias_boleta:
        st.info("Seleccione al menos una materia para generar la boleta.")
        return

    if st.button(
        "Generar Boleta Histórica",
        type="primary",
        key="btn_boleta_historica",
    ):
        filas_html = ""

        for materia in materias_boleta:
            notas = notas_alumno.get(materia, {})
            t1, t2, t3, final = _calcular_promedios(
                notas,
                redondear_mined,
            )

            filas_html += f"""
            <tr>
                <td style="text-align:left;padding-left:5px;">{materia}</td>
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

        logo = get_base64("logo.png")
        imagen_logo = f'<img src="{logo}" height="60">' if logo else ""

        html = f"""
        <html>
        <head>
            <style>
                @page {{ size: letter; margin: 1cm; }}
                body {{ font-family: Arial, sans-serif; }}
                .encabezado {{
                    display:flex;
                    align-items:center;
                    border-bottom:2px solid #222;
                    padding-bottom:10px;
                    margin-bottom:15px;
                }}
                .titulo {{ margin-left:20px; }}
                .titulo h2, .titulo h4 {{ margin:3px; }}
                table {{
                    width:100%;
                    border-collapse:collapse;
                    text-align:center;
                    font-size:10px;
                }}
                td, th {{ border:1px solid #777; padding:5px; }}
                th {{ background:#eeeeee; }}
                .trimestre {{ background:#f3f6f9; font-weight:bold; }}
                .final {{
                    background:#1e3a8a;
                    color:white;
                    font-weight:bold;
                }}
                .firmas {{
                    display:flex;
                    justify-content:space-around;
                    margin-top:60px;
                }}
                .firma {{
                    width:35%;
                    border-top:1px solid #000;
                    text-align:center;
                    padding-top:5px;
                }}
                @media print {{
                    button {{ display:none; }}
                }}
            </style>
        </head>
        <body>
            <div class="encabezado">
                {imagen_logo}
                <div class="titulo">
                    <h2>COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ</h2>
                    <h4>INFORME HISTÓRICO DE RENDIMIENTO ACADÉMICO</h4>
                    <strong>CICLO {ciclo_seleccionado}</strong>
                </div>
            </div>

            <p>
                <b>Alumno:</b> {nombre_alumno}
                &nbsp;&nbsp;&nbsp;
                <b>NIE:</b> {nie_seleccionado}
            </p>

            <p>
                <b>Grado cursado:</b> {grado_seleccionado}
                &nbsp;&nbsp;&nbsp;
                <b>Maestro guía:</b> {maestro_guia}
            </p>

            <table>
                <tr>
                    <th>ASIGNATURA</th>
                    <th>FEB</th><th>MAR</th><th>ABR</th><th>T1</th>
                    <th>MAY</th><th>JUN</th><th>JUL</th><th>T2</th>
                    <th>AGO</th><th>SEP</th><th>OCT</th><th>T3</th>
                    <th>PF</th>
                </tr>
                {filas_html}
            </table>

            <div class="firmas">
                <div class="firma">Maestro Orientador</div>
                <div class="firma">Dirección / Sello</div>
            </div>

            <br><br>

            <center>
                <button onclick="window.print()">
                    🖨️ IMPRIMIR BOLETA HISTÓRICA
                </button>
            </center>
        </body>
        </html>
        """

        components.html(
            html,
            height=750,
            scrolling=True,
        )
