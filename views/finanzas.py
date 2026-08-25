import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from firebase_admin import firestore

from config import TZ_SV, CICLO_LECTIVO


def mostrar_finanzas(
    db,
    lista_grados,
    obtener_fecha_hoy,
    obtener_hora_actual,
    existe_duplicado,
    verificar_pago_duplicado_hoy,
    get_base64,
):
    """Vista principal del módulo financiero de EduManager."""

    st.title("💰 Administración Financiera")

    st.caption(f"📅 Ciclo lectivo activo: {CICLO_LECTIVO}")

    t1, t2, t3, t4 = st.tabs(
        [
            "📊 Corte de Caja",
            "➕ Cobros (Alumnos)",
            "➖ Gastos Operativos",
            "📜 Reportes & Reimpresión",
        ]
    )

    mostrar_corte_caja(
        db=db,
        tab=t1,
        obtener_fecha_hoy=obtener_fecha_hoy,
        get_base64=get_base64,
    )

    mostrar_cobros_alumnos(
        db=db,
        tab=t2,
        lista_grados=lista_grados,
        obtener_hora_actual=obtener_hora_actual,
        existe_duplicado=existe_duplicado,
        get_base64=get_base64,
    )

    mostrar_gastos(
        db=db,
        tab=t3,
        obtener_hora_actual=obtener_hora_actual,
        verificar_pago_duplicado_hoy=verificar_pago_duplicado_hoy,
        get_base64=get_base64,
    )

    mostrar_reportes(
        db=db,
        tab=t4,
        lista_grados=lista_grados,
        obtener_fecha_hoy=obtener_fecha_hoy,
        get_base64=get_base64,
    )


def mostrar_corte_caja(
    db,
    tab,
    obtener_fecha_hoy,
    get_base64,
):
    """Muestra ingresos, egresos y saldo para una fecha específica."""

    with tab:
        c_date, _ = st.columns([1, 2])

        fecha_corte = c_date.date_input(
            "Fecha de Corte",
            obtener_fecha_hoy(),
            key="fin_fecha_corte",
        )

        fecha_str = fecha_corte.strftime("%d/%m/%Y")

        movimientos = db.collection("finanzas").stream()

        data_dia = []
        ingreso_dia = 0.0
        egreso_dia = 0.0

        for documento in movimientos:
            data = documento.to_dict()
            fecha_legible = str(data.get("fecha_legible", ""))

            # Compatible tanto con "dd/mm/YYYY" como con
            # "dd/mm/YYYY HH:MM".
            if fecha_legible.startswith(fecha_str):
                data_dia.append(data)

                tipo = data.get("tipo")
                monto = float(data.get("monto", 0) or 0)

                if tipo == "ingreso":
                    ingreso_dia += monto
                elif tipo == "egreso":
                    egreso_dia += monto

        saldo_dia = ingreso_dia - egreso_dia

        kpi1, kpi2, kpi3 = st.columns(3)

        kpi1.metric(
            "Ingresos del Día",
            f"${ingreso_dia:.2f}",
            delta_color="normal",
        )

        kpi2.metric(
            "Gastos del Día",
            f"${egreso_dia:.2f}",
            delta_color="inverse",
        )

        kpi3.metric(
            "Saldo Neto",
            f"${saldo_dia:.2f}",
        )

        st.divider()

        if not data_dia:
            st.info("No hay movimientos para la fecha seleccionada.")
            return

        df_dia = pd.DataFrame(data_dia)

        columnas = [
            columna
            for columna in [
                "descripcion",
                "tipo",
                "monto",
                "nombre_persona",
            ]
            if columna in df_dia.columns
        ]

        st.dataframe(
            df_dia[columnas],
            width="stretch",
        )

        if st.button(
            "🖨️ Imprimir Corte del Día",
            key="fin_imprimir_corte",
        ):
            logo = get_base64("logo.png")
            hi = f'<img src="{logo}" height="40">' if logo else ""

            html_corte = f"""
            <div style="
                font-family:monospace;
                width:300px;
                margin:auto;
                border:1px solid black;
                padding:10px;
            ">
                <div style="text-align:center;">
                    {hi}<br>
                    <b>COLEGIO BLANCA ELENA</b><br>
                    CORTE DE CAJA
                </div>

                <br>
                <b>FECHA:</b> {fecha_str}<br>
                <hr>

                <table width="100%">
                    <tr>
                        <td>(+) INGRESOS:</td>
                        <td align="right">${ingreso_dia:.2f}</td>
                    </tr>
                    <tr>
                        <td>(-) GASTOS:</td>
                        <td align="right">${egreso_dia:.2f}</td>
                    </tr>
                    <tr>
                        <td><b>(=) SALDO:</b></td>
                        <td align="right"><b>${saldo_dia:.2f}</b></td>
                    </tr>
                </table>

                <br>
                <div style="text-align:center;margin-top:20px;">
                    ___________________<br>
                    Firma Responsable
                </div>
            </div>
            """

            components.html(
                f"""
                <html>
                    <body>
                        {html_corte}
                        <br>
                        <center>
                            <button onclick="window.print()">IMPRIMIR</button>
                        </center>
                    </body>
                </html>
                """,
                height=400,
            )



def _normalizar_ciclo(valor, predeterminado=None):
    """Convierte un ciclo almacenado a entero cuando sea posible."""
    if valor is None:
        return predeterminado

    try:
        return int(valor)
    except (TypeError, ValueError):
        return valor


def _ciclo_movimiento(data, fecha_actual=None):
    """
    Obtiene el ciclo académico de un movimiento.

    Para registros antiguos sin ciclo_lectivo se usa el año de la
    fecha real del movimiento como compatibilidad histórica.
    """
    ciclo = _normalizar_ciclo(data.get("ciclo_lectivo"))

    if ciclo is not None:
        return ciclo

    if fecha_actual is not None:
        return fecha_actual.year

    fecha_legible = str(data.get("fecha_legible", "")).strip()

    # Formatos esperados: dd/mm/YYYY o dd/mm/YYYY HH:MM
    if len(fecha_legible) >= 10:
        try:
            return int(fecha_legible[6:10])
        except (TypeError, ValueError):
            pass

    return None


def mostrar_cobros_alumnos(
    db,
    tab,
    lista_grados,
    obtener_hora_actual,
    existe_duplicado,
    get_base64,
):
    """Búsqueda de alumnos activos y registro de cobros por ciclo."""

    with tab:
        st.subheader("Búsqueda de Alumno para Cobro")

        st.caption(
            f"📅 Ciclo lectivo operativo actual: {CICLO_LECTIVO}. "
            "El cobro puede asociarse a un ciclo anterior o al próximo ciclo."
        )

        modo_busqueda = st.radio(
            "Buscar por:",
            ["NIE", "Nombre", "Grado"],
            horizontal=True,
            key="fin_modo_busqueda_alumno",
        )

        if modo_busqueda == "NIE":
            n_input = st.text_input(
                "Ingrese NIE:",
                key="fin_nie_busqueda",
            )

            if st.button(
                "Buscar por NIE",
                key="fin_btn_buscar_nie",
            ) and n_input:
                documento = (
                    db.collection("alumnos")
                    .document(n_input.strip())
                    .get()
                )

                if not documento.exists:
                    st.error("No encontrado")
                    st.session_state.pop("pago_alum", None)
                else:
                    alumno_data = documento.to_dict()

                    if alumno_data.get("estado", "Activo") != "Activo":
                        st.warning(
                            "⚠️ Este alumno está dado de baja y no puede "
                            "recibir nuevos cobros."
                        )
                        st.session_state.pop("pago_alum", None)
                    else:
                        st.session_state["pago_alum"] = alumno_data

        elif modo_busqueda == "Nombre":
            alumnos_ref = (
                db.collection("alumnos")
                .where("estado", "==", "Activo")
                .stream()
            )

            mapa_nombres = {}

            for alumno_doc in alumnos_ref:
                datos = alumno_doc.to_dict()
                nombre = (
                    f"{datos.get('apellidos', '')} "
                    f"{datos.get('nombres', '')}"
                ).strip()

                if nombre:
                    mapa_nombres[nombre] = alumno_doc.id

            sel_nom = st.selectbox(
                "Seleccione Alumno:",
                [""] + sorted(mapa_nombres.keys()),
                key="fin_sel_alumno_nombre",
            )

            if sel_nom and st.button(
                "Cargar Alumno",
                key="fin_btn_cargar_nombre",
            ):
                nie_encontrado = mapa_nombres[sel_nom]
                alumno_doc = (
                    db.collection("alumnos")
                    .document(nie_encontrado)
                    .get()
                )

                alumno = (
                    alumno_doc.to_dict()
                    if alumno_doc.exists
                    else None
                )

                if alumno and alumno.get("estado", "Activo") == "Activo":
                    st.session_state["pago_alum"] = alumno
                else:
                    st.warning(
                        "⚠️ El alumno seleccionado no está activo."
                    )
                    st.session_state.pop("pago_alum", None)

        else:  # Grado
            sel_grado = st.selectbox(
                "Seleccione Grado:",
                lista_grados,
                key="fin_sel_grado_cobro",
            )

            alumnos_grado = (
                db.collection("alumnos")
                .where("grado_actual", "==", sel_grado)
                .where("estado", "==", "Activo")
                .stream()
            )

            mapa_grado = {}

            for alumno_doc in alumnos_grado:
                datos = alumno_doc.to_dict()
                nombre = (
                    f"{datos.get('apellidos', '')} "
                    f"{datos.get('nombres', '')}"
                ).strip()

                if nombre:
                    mapa_grado[nombre] = alumno_doc.id

            sel_nom_g = st.selectbox(
                "Alumno del Grado:",
                [""] + sorted(mapa_grado.keys()),
                key="fin_sel_alumno_grado",
            )

            if sel_nom_g and st.button(
                "Cargar Alumno Grado",
                key="fin_btn_cargar_grado",
            ):
                nie_encontrado = mapa_grado[sel_nom_g]
                alumno_doc = (
                    db.collection("alumnos")
                    .document(nie_encontrado)
                    .get()
                )

                alumno = (
                    alumno_doc.to_dict()
                    if alumno_doc.exists
                    else None
                )

                if alumno and alumno.get("estado", "Activo") == "Activo":
                    st.session_state["pago_alum"] = alumno
                else:
                    st.warning(
                        "⚠️ El alumno seleccionado no está activo."
                    )
                    st.session_state.pop("pago_alum", None)

        st.divider()

        if "pago_alum" in st.session_state:
            pa = st.session_state["pago_alum"]

            if pa.get("estado", "Activo") != "Activo":
                st.warning(
                    "⚠️ El alumno seleccionado está dado de baja. "
                    "No se permiten nuevos cobros."
                )
                st.session_state.pop("pago_alum", None)
                return

            grado_actual = pa.get(
                "grado_actual",
                "Sin Grado",
            )

            ciclo_alumno_actual = _normalizar_ciclo(
                pa.get("ciclo_lectivo"),
                CICLO_LECTIVO,
            )

            st.success(
                f"Cobrando a: **{pa.get('apellidos', '')} "
                f"{pa.get('nombres', '')}** (NIE: {pa['nie']})"
            )

            st.caption(
                f"Grado actual: {grado_actual} · "
                f"Ciclo del expediente: {ciclo_alumno_actual}"
            )

            with st.form("form_cobro"):
                tipo_c = st.selectbox(
                    "Tipo de Cobro",
                    [
                        "Colegiatura",
                        "Matrícula",
                        "Uniformes",
                        "Otros",
                    ],
                )

                ciclos_disponibles = [
                    CICLO_LECTIVO + 1,
                    CICLO_LECTIVO,
                    CICLO_LECTIVO - 1,
                    CICLO_LECTIVO - 2,
                    CICLO_LECTIVO - 3,
                ]

                ciclo_pago = st.selectbox(
                    "Período académico al que corresponde el cobro",
                    ciclos_disponibles,
                    index=1,
                    help=(
                        "Ejemplo: una deuda de 2026 pagada en 2027 "
                        "debe conservar período académico 2026."
                    ),
                )

                det_c = st.text_input(
                    "Detalle (Ej: Mes de Marzo)"
                )

                monto = st.number_input(
                    "Monto ($)",
                    min_value=0.01,
                )

                obs = st.text_input("Observaciones")

                registrar = st.form_submit_button(
                    "✅ Registrar Ingreso"
                )

                if registrar:
                    detalle_limpio = det_c.strip()

                    if not detalle_limpio:
                        st.error(
                            "Debe ingresar un detalle del cobro."
                        )
                    else:
                        desc_full = (
                            f"{tipo_c} - {detalle_limpio}"
                        )

                        if existe_duplicado(
                            "finanzas",
                            "alumno_nie",
                            pa["nie"],
                            desc_full,
                        ):
                            st.error(
                                "⛔ Transacción duplicada "
                                "(mismo alumno, mismo concepto hoy)."
                            )
                        else:
                            recibo_data = {
                                "tipo": "ingreso",
                                "descripcion": desc_full,
                                "monto": float(monto),
                                "alumno_nie": pa["nie"],
                                "nombre_persona": (
                                    f"{pa.get('apellidos', '')} "
                                    f"{pa.get('nombres', '')}"
                                ).strip(),
                                # Fotografía histórica del momento del cobro
                                "grado_alumno": grado_actual,
                                # Período académico al que corresponde
                                "ciclo_lectivo": int(ciclo_pago),
                                "observaciones": obs.strip(),
                                "fecha": firestore.SERVER_TIMESTAMP,
                                "fecha_legible": obtener_hora_actual(),
                                "id_short": str(int(time.time()))[-6:],
                            }

                            db.collection(
                                "finanzas"
                            ).add(
                                recibo_data
                            )

                            st.session_state[
                                "recibo_temp"
                            ] = recibo_data

                            st.session_state.pop(
                                "pago_alum",
                                None,
                            )

                            st.success(
                                "Cobro registrado"
                            )
                            st.rerun()

        if "recibo_temp" in st.session_state:
            r = st.session_state["recibo_temp"]

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
                        <td width="20%">{hi}</td>
                        <td width="60%" align="center">
                            <h3 style="margin:0;">
                                COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ
                            </h3>
                            <p style="margin:5px;font-size:12px;">
                                San Felipe, San Bartolo, Ilopango
                            </p>
                            <p style="margin:0;font-size:12px;">
                                <b>COMPROBANTE DE INGRESO</b>
                            </p>
                        </td>
                        <td width="20%" align="right">
                            <h4 style="margin:0;color:#d32f2f;">
                                NO. {r.get('id_short', '000')}
                            </h4>
                            <p style="font-size:12px;">
                                {r.get('fecha_legible', '')}
                            </p>
                        </td>
                    </tr>
                </table>

                <hr>

                <div style="padding:10px;">
                    <p>
                        <b>RECIBIMOS DE:</b>
                        {r.get('nombre_persona', '')}
                    </p>

                    <p>
                        <b>LA CANTIDAD DE:</b>
                        <span style="font-size:18px;font-weight:bold;">
                            ${float(r.get('monto', 0)):.2f}
                        </span>
                    </p>

                    <p>
                        <b>POR CONCEPTO DE:</b>
                        {r.get('descripcion', '')}
                    </p>

                    <p>
                        <b>PERÍODO ACADÉMICO:</b>
                        {r.get('ciclo_lectivo', '-')}
                        &nbsp; | &nbsp;
                        <b>GRADO REGISTRADO:</b>
                        {r.get('grado_alumno', '-')}
                    </p>
                </div>

                <br><br>

                <table width="100%">
                    <tr>
                        <td align="center"
                            style="border-top:1px solid #000;width:40%;">
                            Entregado Por
                        </td>
                        <td width="20%"></td>
                        <td align="center"
                            style="border-top:1px solid #000;width:40%;">
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
                            <button onclick="window.print()">
                                🖨️ IMPRIMIR COMPROBANTE
                            </button>
                        </center>
                    </body>
                </html>
                """,
                height=550,
            )

            if st.button(
                "Cerrar Comprobante",
                key="fin_cerrar_recibo",
            ):
                st.session_state.pop(
                    "recibo_temp",
                    None,
                )
                st.rerun()


def mostrar_gastos(
    db,
    tab,
    obtener_hora_actual,
    verificar_pago_duplicado_hoy,
    get_base64,
):
    """Registra gastos operativos y pagos de salario."""

    with tab:
        st.caption(
            f"📅 Los gastos nuevos se registran en el "
            f"ciclo administrativo {CICLO_LECTIVO}."
        )

        with st.form("fin_form_gasto"):
            tipo_gasto = st.selectbox(
                "Gasto",
                [
                    "Salario",
                    "Servicios",
                    "Mantenimiento",
                    "Otros",
                ],
            )

            maestro_seleccionado = None
            pagado_a = ""

            if tipo_gasto == "Salario":
                maestros = (
                    db.collection("maestros_perfil")
                    .where("activo", "==", True)
                    .stream()
                )

                mapa_maestros = {
                    m.to_dict().get(
                        "nombre",
                        "Sin Nombre",
                    ): m.id
                    for m in maestros
                }

                opciones_maestros = sorted(
                    mapa_maestros.keys()
                )

                if opciones_maestros:
                    nombre_sel = st.selectbox(
                        "Seleccionar Maestro:",
                        opciones_maestros,
                    )
                    maestro_seleccionado = (
                        mapa_maestros.get(
                            nombre_sel
                        )
                    )
                    pagado_a = nombre_sel
                else:
                    st.warning(
                        "No hay docentes activos disponibles."
                    )

            else:
                pagado_a = st.text_input(
                    "Pagado a (Nombre/Empresa)"
                )

            monto = st.number_input(
                "Monto",
                min_value=0.01,
            )

            detalle = st.text_input(
                "Detalle"
            )

            registrar = (
                st.form_submit_button(
                    "Registrar"
                )
            )

            if registrar:
                detalle_limpio = detalle.strip()
                pagado_a_limpio = str(
                    pagado_a
                ).strip()

                if not detalle_limpio:
                    st.error(
                        "Debe ingresar el detalle del gasto."
                    )
                elif not pagado_a_limpio:
                    st.error(
                        "Debe indicar a quién se realizó el pago."
                    )
                else:
                    desc_full = (
                        f"{tipo_gasto} - "
                        f"{detalle_limpio}"
                    )

                    duplicado = False

                    if (
                        tipo_gasto == "Salario"
                        and maestro_seleccionado
                    ):
                        duplicado = (
                            verificar_pago_duplicado_hoy(
                                maestro_seleccionado,
                                "Salario",
                            )
                        )

                    if duplicado:
                        st.error(
                            "⛔ Pago duplicado detectado "
                            "(salario ya registrado hoy "
                            "para este docente)."
                        )
                    else:
                        gasto_data = {
                            "tipo": "egreso",
                            "descripcion": desc_full,
                            "monto": float(monto),
                            "nombre_persona": (
                                pagado_a_limpio
                            ),
                            "ciclo_lectivo": (
                                CICLO_LECTIVO
                            ),
                            "fecha": (
                                firestore.SERVER_TIMESTAMP
                            ),
                            "fecha_legible": (
                                obtener_hora_actual()
                            ),
                            "id_short": (
                                str(int(time.time()))[-6:]
                            ),
                        }

                        if maestro_seleccionado:
                            gasto_data[
                                "docente_id"
                            ] = maestro_seleccionado

                        db.collection(
                            "finanzas"
                        ).add(
                            gasto_data
                        )

                        st.session_state[
                            "gasto_temp"
                        ] = gasto_data

                        st.success("Registrado")
                        time.sleep(1)
                        st.rerun()

        if "gasto_temp" in st.session_state:
            r = st.session_state["gasto_temp"]

            logo = get_base64("logo.png")
            hi = (
                f'<img src="{logo}" height="60">'
                if logo
                else ""
            )

            html_gasto = f"""
            <div style="
                border:2px solid #d32f2f;
                padding:20px;
                font-family:Helvetica, sans-serif;
                max-width:700px;
                margin:auto;
            ">
                <table width="100%">
                    <tr>
                        <td width="20%">{hi}</td>
                        <td width="60%" align="center">
                            <h3 style="margin:0;">
                                COLEGIO PROFA. BLANCA ELENA DE HERNÁNDEZ
                            </h3>
                            <p style="margin:0;font-size:12px;">
                                <b>COMPROBANTE DE EGRESO (GASTO)</b>
                            </p>
                        </td>
                        <td width="20%" align="right">
                            <h4 style="margin:0;color:#d32f2f;">
                                NO. {r.get('id_short', '000')}
                            </h4>
                            <p style="font-size:12px;">
                                {r.get('fecha_legible', '')}
                            </p>
                        </td>
                    </tr>
                </table>

                <hr>

                <div style="padding:10px;">
                    <p>
                        <b>PAGADO A:</b>
                        {r.get('nombre_persona', '')}
                    </p>
                    <p>
                        <b>LA CANTIDAD DE:</b>
                        <span style="font-size:18px;font-weight:bold;">
                            ${float(r.get('monto', 0)):.2f}
                        </span>
                    </p>
                    <p>
                        <b>POR CONCEPTO DE:</b>
                        {r.get('descripcion', '')}
                    </p>
                    <p>
                        <b>CICLO ADMINISTRATIVO:</b>
                        {r.get('ciclo_lectivo', '-')}
                    </p>
                </div>

                <br><br>

                <table width="100%">
                    <tr>
                        <td align="center"
                            style="border-top:1px solid #000;width:40%;">
                            Autorizado Por
                        </td>
                        <td width="20%"></td>
                        <td align="center"
                            style="border-top:1px solid #000;width:40%;">
                            Recibido Conforme
                        </td>
                    </tr>
                </table>
            </div>
            """

            components.html(
                f"""
                <html>
                    <body>
                        {html_gasto}
                        <br>
                        <center>
                            <button onclick="window.print()">
                                🖨️ IMPRIMIR COMPROBANTE
                            </button>
                        </center>
                    </body>
                </html>
                """,
                height=540,
            )

            if st.button(
                "Cerrar Comprobante Gasto",
                key="fin_cerrar_gasto",
            ):
                st.session_state.pop(
                    "gasto_temp",
                    None,
                )
                st.rerun()


def mostrar_reportes(
    db,
    tab,
    lista_grados,
    obtener_fecha_hoy,
    get_base64,
):
    """
    Genera reportes financieros por rango, tipo, ciclo y grado.

    Los movimientos nuevos usan el grado almacenado en la transacción.
    Los registros históricos antiguos mantienen compatibilidad usando
    el grado actual únicamente cuando el movimiento no posee snapshot.
    """

    with tab:
        st.subheader(
            "📜 Reportes Financieros"
        )

        # Compatibilidad para movimientos antiguos que no guardaron grado.
        mapa_grados_actuales = {}

        try:
            alumnos_ref = (
                db.collection("alumnos")
                .stream()
            )

            for alumno in alumnos_ref:
                data = alumno.to_dict()

                nie = str(
                    data.get(
                        "nie",
                        alumno.id,
                    )
                )

                mapa_grados_actuales[nie] = (
                    data.get(
                        "grado_actual",
                        "Sin Grado",
                    )
                )

        except Exception as error:
            st.warning(
                f"No fue posible cargar el mapa "
                f"de grados: {error}"
            )

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------

        f1, f2 = st.columns(2)
        f3, f4 = st.columns(2)

        filtro_rango = f1.selectbox(
            "Rango de Tiempo",
            [
                "Este Mes",
                "Mes Pasado",
                "Últimos 3 Meses",
                "Últimos 6 Meses",
                "Este Año",
                "Personalizado",
            ],
            key="fin_filtro_rango",
        )

        f_tipo = f2.multiselect(
            "Tipo Transacción:",
            ["ingreso", "egreso"],
            default=["ingreso", "egreso"],
            key="fin_filtro_tipo",
        )

        ciclos_reporte = [
            "Todos",
            CICLO_LECTIVO + 1,
            CICLO_LECTIVO,
            CICLO_LECTIVO - 1,
            CICLO_LECTIVO - 2,
            CICLO_LECTIVO - 3,
            CICLO_LECTIVO - 4,
            CICLO_LECTIVO - 5,
        ]

        filtro_ciclo = f3.selectbox(
            "Ciclo académico:",
            ciclos_reporte,
            index=0,
            key="fin_filtro_ciclo",
        )

        filtro_grado = f4.selectbox(
            "Filtrar Grado (Alumnos):",
            ["Todos"] + lista_grados,
            key="fin_filtro_grado",
        )

        hoy = obtener_fecha_hoy()

        if filtro_rango == "Personalizado":
            c_d1, c_d2 = st.columns(2)

            f_inicio = c_d1.date_input(
                "Desde",
                hoy.replace(day=1),
                key="fin_desde",
            )

            f_fin = c_d2.date_input(
                "Hasta",
                hoy,
                key="fin_hasta",
            )

        elif filtro_rango == "Este Mes":
            f_inicio = hoy.replace(day=1)
            f_fin = hoy

        elif filtro_rango == "Mes Pasado":
            ultimo_dia_mes_anterior = (
                hoy.replace(day=1)
                - timedelta(days=1)
            )
            f_inicio = (
                ultimo_dia_mes_anterior.replace(
                    day=1
                )
            )
            f_fin = ultimo_dia_mes_anterior

        elif filtro_rango == "Últimos 3 Meses":
            f_inicio = hoy - timedelta(days=90)
            f_fin = hoy

        elif filtro_rango == "Últimos 6 Meses":
            f_inicio = hoy - timedelta(days=180)
            f_fin = hoy

        else:
            f_inicio = hoy.replace(
                month=1,
                day=1,
            )
            f_fin = hoy

        if f_inicio > f_fin:
            st.error(
                "La fecha inicial no puede ser "
                "posterior a la final."
            )
            return

        dt_ini = datetime.combine(
            f_inicio,
            datetime.min.time(),
        )

        dt_fin = datetime.combine(
            f_fin,
            datetime.max.time(),
        )

        documentos = (
            db.collection("finanzas")
            .stream()
        )

        data_raw = []
        total_ingresos = 0.0
        total_egresos = 0.0

        for documento in documentos:
            data = documento.to_dict()
            fecha_db = data.get("fecha")

            if not fecha_db:
                continue

            if isinstance(fecha_db, datetime):
                actual = (
                    fecha_db
                    .astimezone(TZ_SV)
                    .replace(tzinfo=None)
                )
            else:
                actual = datetime.fromtimestamp(
                    fecha_db.timestamp(),
                    TZ_SV,
                ).replace(
                    tzinfo=None
                )

            if not (
                dt_ini
                <= actual
                <= dt_fin
            ):
                continue

            tipo = data.get("tipo")

            if tipo not in f_tipo:
                continue

            ciclo_movimiento = _ciclo_movimiento(
                data,
                actual,
            )

            if (
                filtro_ciclo != "Todos"
                and ciclo_movimiento
                != filtro_ciclo
            ):
                continue

            nie_transaccion = data.get(
                "alumno_nie"
            )

            # Para nuevos movimientos: snapshot histórico exacto.
            grado_alumno = data.get(
                "grado_alumno"
            )

            # Compatibilidad histórica con movimientos antiguos.
            if (
                not grado_alumno
                and nie_transaccion
            ):
                grado_alumno = (
                    mapa_grados_actuales.get(
                        str(nie_transaccion),
                        "Sin Grado",
                    )
                )

            if not grado_alumno:
                grado_alumno = "-"

            if (
                filtro_grado != "Todos"
                and grado_alumno
                != filtro_grado
            ):
                continue

            fila = dict(data)
            fila["ciclo_reporte"] = (
                ciclo_movimiento
                if ciclo_movimiento is not None
                else "-"
            )
            fila["grado_reporte"] = grado_alumno
            data_raw.append(fila)

            monto = float(
                data.get(
                    "monto",
                    0,
                )
                or 0
            )

            if tipo == "ingreso":
                total_ingresos += monto
            elif tipo == "egreso":
                total_egresos += monto

        st.divider()

        k1, k2, k3 = st.columns(3)

        k1.metric(
            "Total Ingresos",
            f"${total_ingresos:.2f}",
            border=True,
        )

        k2.metric(
            "Total Egresos",
            f"${total_egresos:.2f}",
            delta_color="inverse",
            border=True,
        )

        k3.metric(
            "Balance Periodo",
            f"${total_ingresos - total_egresos:.2f}",
            border=True,
        )

        st.divider()

        data_raw.sort(
            key=lambda x: x.get(
                "fecha_legible",
                "",
            ),
            reverse=True,
        )

        if not data_raw:
            st.info(
                "No hay registros con los filtros seleccionados."
            )
            return

        df_rep = pd.DataFrame(
            data_raw
        )

        columnas = [
            columna
            for columna in [
                "fecha_legible",
                "ciclo_reporte",
                "tipo",
                "grado_reporte",
                "nombre_persona",
                "descripcion",
                "monto",
            ]
            if columna in df_rep.columns
        ]

        st.dataframe(
            df_rep[columnas],
            width="stretch",
        )

        st.caption(
            "ℹ️ Los movimientos nuevos conservan el grado histórico "
            "registrado al momento del cobro. Los movimientos antiguos "
            "sin ese dato usan el grado actual únicamente como "
            "compatibilidad."
        )

        if st.button(
            "🖨️ Imprimir Reporte Generado",
            key="fin_imprimir_reporte",
        ):
            logo = get_base64(
                "logo.png"
            )

            hi = (
                f'<img src="{logo}" height="50">'
                if logo
                else ""
            )

            filas_html = ""

            for item in data_raw:
                tipo = item.get(
                    "tipo",
                    "",
                )

                color_fila = (
                    "#e8f5e9"
                    if tipo == "ingreso"
                    else "#ffebee"
                )

                filas_html += f"""
                <tr style="background:{color_fila};">
                    <td>{item.get('fecha_legible', '')}</td>
                    <td>{item.get('ciclo_reporte', '-')}</td>
                    <td>{item.get('grado_reporte', '-')}</td>
                    <td>{item.get('nombre_persona', '')}</td>
                    <td>{item.get('descripcion', '')}</td>
                    <td align="right">
                        ${float(item.get('monto', 0)):.2f}
                    </td>
                </tr>
                """

            titulo_reporte = (
                f"REPORTE FINANCIERO "
                f"({filtro_rango})"
            )

            if filtro_ciclo != "Todos":
                titulo_reporte += (
                    f" - CICLO {filtro_ciclo}"
                )

            if filtro_grado != "Todos":
                titulo_reporte += (
                    f" - {filtro_grado.upper()}"
                )

            html_reporte = f"""
            <div style="
                font-family:Arial;
                padding:20px;
            ">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    border-bottom:2px solid #333;
                    padding-bottom:10px;
                ">

                    <div style="
                        display:flex;
                        align-items:center;
                        gap:15px;
                    ">
                        {hi}

                        <div>
                            <h2 style="margin:0;">
                                COLEGIO BLANCA ELENA
                            </h2>

                            <p style="margin:0;">
                                {titulo_reporte}
                            </p>
                        </div>
                    </div>

                    <div style="text-align:right;">
                        <p>
                            <b>Desde:</b>
                            {f_inicio.strftime('%d/%m/%Y')}
                            <br>

                            <b>Hasta:</b>
                            {f_fin.strftime('%d/%m/%Y')}
                        </p>
                    </div>
                </div>

                <br>

                <div style="
                    display:flex;
                    gap:20px;
                    margin-bottom:20px;
                ">

                    <div style="
                        background:#e8f5e9;
                        padding:10px;
                        border:1px solid #4caf50;
                        border-radius:5px;
                        flex:1;
                        text-align:center;
                    ">
                        <h4 style="
                            margin:0;
                            color:#2e7d32;
                        ">
                            INGRESOS
                        </h4>

                        <h2 style="margin:0;">
                            ${total_ingresos:.2f}
                        </h2>
                    </div>

                    <div style="
                        background:#ffebee;
                        padding:10px;
                        border:1px solid #e57373;
                        border-radius:5px;
                        flex:1;
                        text-align:center;
                    ">
                        <h4 style="
                            margin:0;
                            color:#c62828;
                        ">
                            EGRESOS
                        </h4>

                        <h2 style="margin:0;">
                            ${total_egresos:.2f}
                        </h2>
                    </div>

                    <div style="
                        background:#f5f5f5;
                        padding:10px;
                        border:1px solid #999;
                        border-radius:5px;
                        flex:1;
                        text-align:center;
                    ">
                        <h4 style="margin:0;">
                            BALANCE
                        </h4>

                        <h2 style="margin:0;">
                            ${total_ingresos - total_egresos:.2f}
                        </h2>
                    </div>
                </div>

                <table
                    style="
                        width:100%;
                        border-collapse:collapse;
                        font-size:12px;
                    "
                    border="1"
                    bordercolor="#ddd"
                >
                    <tr style="
                        background:#333;
                        color:white;
                    ">
                        <th>Fecha</th>
                        <th>Ciclo</th>
                        <th>Grado</th>
                        <th>Persona/Entidad</th>
                        <th>Descripción</th>
                        <th>Monto</th>
                    </tr>

                    {filas_html}
                </table>

                <br><br>

                <div style="text-align:center;">
                    __________________________
                    <br>
                    Firma Dirección
                </div>
            </div>
            """

            components.html(
                f"""
                <html>
                    <body>
                        {html_reporte}
                        <br>

                        <center>
                            <button
                                onclick="window.print()"
                                style="
                                    background:#333;
                                    color:white;
                                    padding:10px 20px;
                                    cursor:pointer;
                                "
                            >
                                🖨️ IMPRIMIR REPORTE PDF
                            </button>
                        </center>
                    </body>
                </html>
                """,
                height=650,
                scrolling=True,
            )