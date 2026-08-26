import time

import pandas as pd
import streamlit as st


MAPA_PROMOCION = {
    "Kinder 4": "Kinder 5",
    "Kinder 5": "Preparatoria",
    "Preparatoria": "Primer Grado",
    "Primer Grado": "Segundo Grado",
    "Segundo Grado": "Tercer Grado",
    "Tercer Grado": "Cuarto Grado",
    "Cuarto Grado": "Quinto Grado",
    "Quinto Grado": "Sexto Grado",
    "Sexto Grado": "Séptimo Grado",
    "Séptimo Grado": "Octavo Grado",
    "Octavo Grado": "Noveno Grado",
    "Noveno Grado": "Graduado",
}


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

    promovidos = 0
    no_promovidos = 0
    graduados = 0
    errores = []

    fecha = (
        obtener_fecha_hoy()
        .strftime("%d/%m/%Y")
    )

    usuario = (
        st.session_state.get(
            "user_name",
            "Administrador",
        )
    )

    # Mapa rápido por NIE
    mapa_alumnos = {
        alumno["NIE"]: alumno
        for alumno in alumnos
    }

    with st.spinner(
        "Procesando cierre de ciclo..."
    ):

        for _, fila in editor.iterrows():

            resultado = fila[
                "Resultado"
            ]

            if resultado == "No procesar":
                continue

            nie = str(
                fila["NIE"]
            )

            alumno = mapa_alumnos.get(
                nie
            )

            if not alumno:

                errores.append(
                    f"{nie}: alumno no encontrado."
                )

                continue

            data = alumno["data"]
            documento_id = alumno["id"]

            try:

                historial = list(
                    data.get(
                        "historial_academico",
                        []
                    )
                )

                turno_actual = data.get(
                    "turno",
                    "Matutino"
                )

                # ======================================
                # NO PROMOVIDO
                # ======================================

                if resultado == "No promovido":

                    historial.append(
                        {
                            "ciclo": ciclo_origen,
                            "grado": grado_origen,
                            "resultado": (
                                "No promovido"
                            ),
                            "grado_destino": (
                                grado_origen
                            ),
                            "ciclo_destino": (
                                ciclo_destino
                            ),
                            "turno_origen": (
                                turno_actual
                            ),
                            "turno_destino": (
                                turno_actual
                            ),
                            "fecha": fecha,
                            "usuario": usuario,
                        }
                    )

                    update_data = {
                        "grado_anterior": (
                            grado_origen
                        ),

                        "grado_actual": (
                            grado_origen
                        ),

                        "ciclo_lectivo": (
                            ciclo_destino
                        ),

                        "turno": turno_actual,

                        "estado": "Activo",

                        "activo": True,

                        "fecha_promocion": (
                            fecha
                        ),

                        "promovido_por": (
                            usuario
                        ),

                        "resultado_cierre": (
                            "No promovido"
                        ),

                        "historial_academico": (
                            historial
                        ),
                    }

                    no_promovidos += 1

                # ======================================
                # NOVENO → GRADUADO
                # ======================================

                elif (
                    grado_destino
                    == "Graduado"
                ):

                    historial.append(
                        {
                            "ciclo": (
                                ciclo_origen
                            ),
                            "grado": (
                                grado_origen
                            ),
                            "resultado": (
                                "Graduado"
                            ),
                            "fecha": fecha,
                            "usuario": usuario,
                        }
                    )

                    update_data = {
                        "estado": (
                            "Graduado"
                        ),

                        "activo": False,

                        "fecha_baja": (
                            fecha
                        ),

                        "fecha_graduacion": (
                            fecha
                        ),

                        "motivo_baja": (
                            "Graduación"
                        ),

                        "baja_realizada_por": (
                            usuario
                        ),

                        "ciclo_lectivo": (
                            ciclo_origen
                        ),

                        "resultado_cierre": (
                            "Graduado"
                        ),

                        "historial_academico": (
                            historial
                        ),
                    }

                    graduados += 1

                # ======================================
                # PROMOVIDO NORMAL
                # ======================================

                else:

                    nuevo_turno = (
                        turno_actual
                    )

                    # Cuarto → Quinto
                    # cambia automáticamente
                    # a turno vespertino.
                    if (
                        grado_origen
                        == "Cuarto Grado"
                    ):

                        nuevo_turno = (
                            "Vespertino"
                        )

                    historial.append(
                        {
                            "ciclo": (
                                ciclo_origen
                            ),

                            "grado": (
                                grado_origen
                            ),

                            "resultado": (
                                "Promovido"
                            ),

                            "grado_destino": (
                                grado_destino
                            ),

                            "ciclo_destino": (
                                ciclo_destino
                            ),

                            "turno_origen": (
                                turno_actual
                            ),

                            "turno_destino": (
                                nuevo_turno
                            ),

                            "fecha": fecha,

                            "usuario": usuario,
                        }
                    )

                    update_data = {
                        "grado_anterior": (
                            grado_origen
                        ),

                        "grado_actual": (
                            grado_destino
                        ),

                        "ciclo_lectivo": (
                            ciclo_destino
                        ),

                        "turno": nuevo_turno,

                        "estado": "Activo",

                        "activo": True,

                        "fecha_promocion": (
                            fecha
                        ),

                        "promovido_por": (
                            usuario
                        ),

                        "resultado_cierre": (
                            "Promovido"
                        ),

                        "historial_academico": (
                            historial
                        ),
                    }

                    promovidos += 1

                # ======================================
                # ACTUALIZAR FIRESTORE
                # ======================================

                (
                    db.collection(
                        "alumnos"
                    )
                    .document(
                        documento_id
                    )
                    .update(
                        update_data
                    )
                )

            except Exception as error:

                errores.append(
                    f"{nie}: {error}"
                )

    # ==================================================
    # RESULTADO
    # ==================================================

    st.success(
        "✅ Proceso de cierre finalizado."
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "✅ Promovidos",
        promovidos,
    )

    c2.metric(
        "🔁 No promovidos",
        no_promovidos,
    )

    c3.metric(
        "🎓 Graduados",
        graduados,
    )

    if errores:

        st.error(
            f"Se encontraron "
            f"{len(errores)} errores."
        )

        for error in errores:
            st.write(error)

    else:

        st.success(
            "No se reportaron errores."
        )

    time.sleep(2)
    st.rerun()