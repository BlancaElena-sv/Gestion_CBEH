from datetime import datetime

import pandas as pd
import streamlit as st

from config import CICLO_LECTIVO


def mostrar_asistencia_global(
    db,
    lista_grados,
    obtener_fecha_hoy,
):
    st.title("📅 Reporte de Asistencia Global")

    st.caption(f"📅 Ciclo lectivo actual: {CICLO_LECTIVO}")

    c1, c2, c3 = st.columns(3)

    grado = c1.selectbox("Grado", lista_grados)

    fecha_inicio = c2.date_input("Desde:", obtener_fecha_hoy())

    fecha_fin = c3.date_input("Hasta:", obtener_fecha_hoy())

    if not st.button("Generar Reporte", type="primary"):
        return

    if fecha_inicio > fecha_fin:
        st.error("La fecha inicial no puede ser mayor que la fecha final.")
        return

    # ==========================================
    # ALUMNOS ACTIVOS (ADAPTADO A SUPABASE)
    # ==========================================
    response_alumnos = (
        db.table("alumnos")
        .select("nie, nombres, apellidos")
        .eq("grado_actual", grado)
        .eq("estado", "Activo")
        .execute()
    )

    alumnos_data = response_alumnos.data if response_alumnos.data else []

    stats = {}

    for datos in alumnos_data:
        nie = datos["nie"]

        stats[nie] = {
            "Nombre": (
                f"{datos.get('apellidos', '')} {datos.get('nombres', '')}"
            ).strip(),
            "P": 0,
            "A": 0,
            "T": 0,
            "Permiso": 0,
            "Obs": [],
        }

    if not stats:
        st.warning("No hay alumnos activos en este grado.")
        return

    # ==========================================
    # REGISTROS DE ASISTENCIA (ADAPTADO A SUPABASE)
    # ==========================================
    response_asistencia = (
        db.table("asistencia").select("*").eq("grado", grado).execute()
    )

    docs_asistencia = response_asistencia.data if response_asistencia.data else []

    total_dias = 0

    for data_doc in docs_asistencia:
        # Ignorar otros ciclos
        ciclo_doc = data_doc.get("ciclo_lectivo", CICLO_LECTIVO)

        # En Supabase puede venir como string o int, lo forzamos a int para comparar
        try:
            if int(ciclo_doc) != CICLO_LECTIVO:
                continue
        except (ValueError, TypeError):
            pass

        fecha_doc_str = data_doc.get("fecha")
        if not fecha_doc_str:
            continue

        # Convertir el string de Supabase a objeto date de Python
        try:
            # Si la fecha viene como "2026-02-15" o "2026-02-15T00:00:00"
            fecha_str_limpia = str(fecha_doc_str).split("T")[0]
            fecha_obj = datetime.strptime(fecha_str_limpia, "%Y-%m-%d").date()
        except Exception:
            continue

        if not (fecha_inicio <= fecha_obj <= fecha_fin):
            continue

        total_dias += 1

        registros = data_doc.get("registros", {})
        observaciones = data_doc.get("observaciones", {})

        # En Supabase las columnas JSONB a veces vuelven como texto, hay que asegurarse
        if isinstance(registros, str):
            import json

            try:
                registros = json.loads(registros)
            except:
                registros = {}

        if isinstance(observaciones, str):
            import json

            try:
                observaciones = json.loads(observaciones)
            except:
                observaciones = {}

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
                    f"{fecha_obj.strftime('%d/%m')}: {observaciones[nie]}"
                )

    # ==========================================
    # RESULTADOS
    # ==========================================

    if total_dias == 0:
        st.info("No hay tomas de asistencia registradas para este periodo.")
        return

    filas = []

    for datos in stats.values():
        porcentaje = (datos["P"] / total_dias) * 100

        filas.append(
            {
                "Alumno": datos["Nombre"],
                "Asistencias": datos["P"],
                "Faltas": datos["A"],
                "Tardanzas": datos["T"],
                "Permisos": datos["Permiso"],
                "% Asist.": (f"{porcentaje:.0f}%"),
                "Observaciones": ", ".join(datos["Obs"]),
            }
        )

    df = pd.DataFrame(filas)

    st.dataframe(df, width="stretch")

    st.caption(f"Días con asistencia registrada: {total_dias}")
