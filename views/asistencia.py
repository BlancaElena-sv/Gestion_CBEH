import pandas as pd
import streamlit as st
from datetime import datetime

from config import CICLO_LECTIVO, TZ_SV


def mostrar_asistencia_global(
    db,
    lista_grados,
    obtener_fecha_hoy,
):
    st.title("📅 Reporte de Asistencia Global")

    st.caption(
        f"📅 Ciclo lectivo actual: {CICLO_LECTIVO}"
    )

    c1, c2, c3 = st.columns(3)

    grado = c1.selectbox(
        "Grado",
        lista_grados
    )

    fecha_inicio = c2.date_input(
        "Desde:",
        obtener_fecha_hoy()
    )

    fecha_fin = c3.date_input(
        "Hasta:",
        obtener_fecha_hoy()
    )

    if not st.button(
        "Generar Reporte",
        type="primary"
    ):
        return

    if fecha_inicio > fecha_fin:
        st.error(
            "La fecha inicial no puede ser mayor que la fecha final."
        )
        return

    # ==========================================
    # ALUMNOS ACTIVOS
    # ==========================================

    alumnos_docs = (
        db.collection("alumnos")
        .where("grado_actual", "==", grado)
        .where("estado", "==", "Activo")
        .stream()
    )

    stats = {}

    for alumno in alumnos_docs:
        datos = alumno.to_dict()

        nie = datos["nie"]

        stats[nie] = {
            "Nombre": (
                f"{datos.get('apellidos', '')} "
                f"{datos.get('nombres', '')}"
            ).strip(),
            "P": 0,
            "A": 0,
            "T": 0,
            "Permiso": 0,
            "Obs": [],
        }

    if not stats:
        st.warning(
            "No hay alumnos activos en este grado."
        )
        return

    # ==========================================
    # REGISTROS DE ASISTENCIA
    # ==========================================

    docs = (
        db.collection("asistencia")
        .where("grado", "==", grado)
        .stream()
    )

    total_dias = 0

    for documento in docs:
        data_doc = documento.to_dict()

        # Ignorar otros ciclos
        ciclo_doc = data_doc.get(
            "ciclo_lectivo",
            2026
        )

        if ciclo_doc != CICLO_LECTIVO:
            continue

        fecha_doc = data_doc.get("fecha")

        if not fecha_doc:
            continue

        if isinstance(fecha_doc, datetime):
            fecha_obj = (
                fecha_doc
                .astimezone(TZ_SV)
                .date()
            )
        else:
            fecha_obj = datetime.fromtimestamp(
                fecha_doc.timestamp(),
                TZ_SV
            ).date()

        if not (
            fecha_inicio
            <= fecha_obj
            <= fecha_fin
        ):
            continue

        total_dias += 1

        registros = data_doc.get(
            "registros",
            {}
        )

        observaciones = data_doc.get(
            "observaciones",
            {}
        )

        for nie, estado in registros.items():

            if nie not in stats:
                continue

            if estado == "Presente":
                stats[nie]["P"] += 1

            elif estado == "Ausente":
                stats[nie]["A"] += 1

            elif estado == "Tardanza":
                stats[nie]["T"] += 1

            elif estado == "Permiso":
                stats[nie]["Permiso"] += 1

            if observaciones.get(nie):
                stats[nie]["Obs"].append(
                    f"{fecha_obj.strftime('%d/%m')}: "
                    f"{observaciones[nie]}"
                )

    # ==========================================
    # RESULTADOS
    # ==========================================

    if total_dias == 0:
        st.info(
            "No hay tomas de asistencia registradas "
            "para este periodo."
        )
        return

    filas = []

    for datos in stats.values():

        porcentaje = (
            datos["P"] / total_dias
        ) * 100

        filas.append(
            {
                "Alumno": datos["Nombre"],
                "Asistencias": datos["P"],
                "Faltas": datos["A"],
                "Tardanzas": datos["T"],
                "Permisos": datos["Permiso"],
                "% Asist.": (
                    f"{porcentaje:.0f}%"
                ),
                "Observaciones": ", ".join(
                    datos["Obs"]
                ),
            }
        )

    df = pd.DataFrame(filas)

    st.dataframe(
        df,
        width="stretch"
    )

    st.caption(
        f"Días con asistencia registrada: {total_dias}"
    )