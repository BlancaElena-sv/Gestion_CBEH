from authorization import AccessDenied, protected
from integrity_service import IntegrityError
from promotion_service import MAPA_PROMOCION, promote_student

import pandas as pd
import streamlit as st


@protected('Promoción de Grado')
def mostrar_promocion(
    db,
    obtener_fecha_hoy,
    ciclo_origen=2026,
    ciclo_destino=2027,
):

    st.title(
        "🎓 Promoción y Cierre de Ciclo"
    )

    st.info(
        f"Proceso de cierre académico {ciclo_origen} "
        f"y apertura del ciclo {ciclo_destino}."
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Ciclo origen",
        ciclo_origen,
    )

    c2.metric(
        "Ciclo destino",
        ciclo_destino,
    )

    # ==================================================
    # SELECCIÓN DEL GRADO
    # ==================================================

    grados_disponibles = list(
        MAPA_PROMOCION.keys()
    )

    grado_origen = st.selectbox(
        "Grado a procesar",
        grados_disponibles,
    )

    grado_destino = MAPA_PROMOCION[
        grado_origen
    ]

    if grado_destino == "Graduado":

        st.warning(
            "En Noveno Grado, los alumnos promovidos "
            "serán marcados como GRADUADOS. "
            "Los no promovidos permanecerán en "
            f"Noveno Grado para el ciclo {ciclo_destino}."
        )

    else:

        st.success(
            f"Promoción automática: "
            f"{grado_origen} → "
            f"{grado_destino} · "
            f"Ciclo {ciclo_destino}"
        )

    # ==================================================
    # CARGAR ALUMNOS
    # ==================================================

    alumnos_docs = (
        db.collection("alumnos")
        .where(
            "grado_actual",
            "==",
            grado_origen
        )
        .where(
            "estado",
            "==",
            "Activo"
        )
        .stream()
    )

    alumnos = []

    for doc in alumnos_docs:

        data = doc.to_dict()

        # ----------------------------------------------
        # Solo alumnos pertenecientes al ciclo origen
        # ----------------------------------------------

        ciclo_alumno = data.get(
            "ciclo_lectivo",
            ciclo_origen
        )

        try:
            ciclo_alumno = int(
                ciclo_alumno
            )
        except (TypeError, ValueError):
            pass

        if ciclo_alumno != ciclo_origen:
            continue

        # ----------------------------------------------
        # Evitar procesamiento duplicado
        # ----------------------------------------------

        historial = data.get(
            "historial_academico",
            []
        )

        if not isinstance(historial, list) or any(not isinstance(row, dict) for row in historial):
            st.warning(
                f"Alumno {data.get('nie', doc.id)}: historial incompatible; "
                "operación bloqueada hasta su revisión."
            )
            continue

        ya_procesado = any(

            registro.get("ciclo")
            == ciclo_origen

            and registro.get("resultado")
            in [
                "Promovido",
                "No promovido",
                "Graduado",
            ]

            for registro in historial
        )

        if ya_procesado:
            continue

        alumnos.append(
            {
                "id": doc.id,

                "NIE": str(
                    data.get(
                        "nie",
                        doc.id
                    )
                ),

                "Alumno": (
                    f"{data.get('apellidos', '')} "
                    f"{data.get('nombres', '')}"
                ).strip(),

                "Resultado": "Promover",

                "data": data,
            }
        )

    alumnos.sort(
        key=lambda x: x["Alumno"]
    )

    if not alumnos:

        st.warning(
            "No hay alumnos pendientes de procesar "
            "en este grado."
        )

        return

    st.write(
        f"**Alumnos pendientes:** "
        f"{len(alumnos)}"
    )

    st.caption(
        "Seleccione el resultado de cierre "
        "para cada alumno."
    )

    # ==================================================
    # TABLA DE RESULTADOS
    # ==================================================

    df = pd.DataFrame(
        [
            {
                "NIE": alumno["NIE"],
                "Alumno": alumno["Alumno"],
                "Resultado": alumno["Resultado"],
            }
            for alumno in alumnos
        ]
    )

    editor = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "NIE": (
                st.column_config.TextColumn(
                    "NIE",
                    disabled=True,
                )
            ),

            "Alumno": (
                st.column_config.TextColumn(
                    "Alumno",
                    disabled=True,
                    width="large",
                )
            ),

            "Resultado": (
                st.column_config.SelectboxColumn(
                    "Resultado",
                    options=[
                        "Promover",
                        "No promovido",
                        "No procesar",
                    ],
                    required=True,
                )
            ),
        },
        key=(
            f"editor_promocion_"
            f"{grado_origen}_"
            f"{ciclo_origen}"
        ),
    )

    # ==================================================
    # RESUMEN
    # ==================================================

    cantidad_promover = len(
        editor[
            editor["Resultado"]
            == "Promover"
        ]
    )

    cantidad_repetir = len(
        editor[
            editor["Resultado"]
            == "No promovido"
        ]
    )

    cantidad_ignorar = len(
        editor[
            editor["Resultado"]
            == "No procesar"
        ]
    )

    st.divider()

    r1, r2, r3 = st.columns(3)

    r1.metric(
        "✅ Promover",
        cantidad_promover,
    )

    r2.metric(
        "🔁 No promovidos",
        cantidad_repetir,
    )

    r3.metric(
        "⏸️ No procesar",
        cantidad_ignorar,
    )

    if (
        cantidad_promover
        + cantidad_repetir
        == 0
    ):

        st.warning(
            "No hay alumnos seleccionados "
            "para procesar."
        )

        return

    # ==================================================
    # ADVERTENCIAS
    # ==================================================

    if grado_destino == "Graduado":

        st.warning(
            f"Los alumnos marcados como Promover "
            f"serán graduados. Los marcados como "
            f"No promovido permanecerán en "
            f"Noveno Grado para {ciclo_destino}."
        )

    else:

        st.info(
            f"Los promovidos pasarán a "
            f"{grado_destino}. "
            f"Los no promovidos permanecerán "
            f"en {grado_origen}. "
            f"Todos iniciarán el ciclo "
            f"{ciclo_destino}."
        )

    # ==================================================
    # CONFIRMACIÓN
    # ==================================================

    confirmacion = st.text_input(
        "Para confirmar escriba: PROMOVER"
    )

    confirmar = st.checkbox(
        "Confirmo que revisé los resultados "
        "de todos los alumnos."
    )

    if not st.button(
        "🎓 EJECUTAR CIERRE DE CICLO",
        type="primary",
        width="stretch",
    ):
        return

    if (
        confirmacion
        .strip()
        .upper()
        != "PROMOVER"
    ):

        st.error(
            "Debe escribir PROMOVER "
            "para confirmar."
        )

        return

    if not confirmar:

        st.error(
            "Debe marcar la casilla "
            "de confirmación."
        )

        return

    # ==================================================
    # PROCESAMIENTO
    # ==================================================

    counts = dict(promovido=0, no_promovido=0, graduado=0, omitido=0, rechazado=0, error=0)
    detalles = []
    fecha = obtener_fecha_hoy().strftime("%d/%m/%Y")
    # Se conserva el documento real; un NIE duplicado nunca selecciona otro alumno.
    with st.spinner("Procesando cierre de ciclo..."):
        for index, fila in editor.iterrows():
            alumno = alumnos[index]
            try:
                outcome = promote_student(
                    db, alumno['id'], fila['Resultado'], grado_origen,
                    ciclo_origen, ciclo_destino, fecha,
                )
            except (IntegrityError, AccessDenied) as error:
                counts['rechazado'] += 1
                detalles.append(f"{alumno['NIE']}: rechazado: {error}")
            except Exception as error:
                counts['error'] += 1
                detalles.append(
                    f"{alumno['NIE']}: no se confirmó la escritura: {error}. "
                    "Recargue antes de reintentar; el ciclo ya procesado no se repetirá."
                )
            else:
                # El callback puede reintentarse; solo se cuenta tras el commit.
                counts[outcome.status] += 1
                if outcome.reason:
                    detalles.append(f"{alumno['NIE']}: {outcome.reason}")

    if counts['error'] or counts['rechazado']:
        st.warning("Cierre con operaciones pendientes; revise el detalle antes de reintentar.")
    else:
        st.success("✅ Proceso de cierre finalizado.")
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Promovidos", counts['promovido'])
    c2.metric("🔁 No promovidos", counts['no_promovido'])
    c3.metric("🎓 Graduados", counts['graduado'])
    st.write(
        f"Omitidos: {counts['omitido']} · Rechazados: {counts['rechazado']} · "
        f"Errores de escritura o confirmación: {counts['error']}"
    )
    for detalle in detalles:
        st.write(detalle)
    # No se fuerza rerun: el resumen debe permanecer visible. Una nueva ejecución
    # vuelve a leer alumnos y excluye los ciclos ya confirmados.
