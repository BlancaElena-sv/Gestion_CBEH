import time

import streamlit as st


MAPA_PROMOCION = {
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
    st.title("🎓 Promoción Masiva de Alumnos")

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

    grados_disponibles = list(MAPA_PROMOCION.keys())

    grado_origen = st.selectbox(
        "Grado a promover",
        grados_disponibles,
    )

    grado_destino = MAPA_PROMOCION[grado_origen]

    if grado_destino == "Graduado":
        st.warning(
            "Los alumnos de Noveno Grado serán marcados "
            "como GRADUADOS e inactivos."
        )
    else:
        st.success(
            f"Destino automático: {grado_destino} - Ciclo {ciclo_destino}"
        )

    alumnos_docs = (
        db.collection("alumnos")
        .where("grado_actual", "==", grado_origen)
        .where("estado", "==", "Activo")
        .stream()
    )

    alumnos = []

    for doc in alumnos_docs:
        data = doc.to_dict()

        historial = data.get(
            "historial_academico",
            []
        )

        ya_promovido = any(
            registro.get("ciclo") == ciclo_origen
            and registro.get("resultado") in [
                "Promovido",
                "Graduado",
            ]
            for registro in historial
        )

        if ya_promovido:
            continue

        alumnos.append(
            {
                "id": doc.id,
                "nie": data.get("nie", doc.id),
                "nombre": (
                    f"{data.get('apellidos', '')} "
                    f"{data.get('nombres', '')}"
                ).strip(),
                "data": data,
            }
        )

    alumnos.sort(
        key=lambda x: x["nombre"]
    )

    if not alumnos:
        st.warning(
            "No hay alumnos activos en este grado."
        )
        return

    st.write(
        f"**Alumnos activos encontrados:** {len(alumnos)}"
    )

    opciones = {
        f"{a['nie']} - {a['nombre']}": a
        for a in alumnos
    }

    seleccionados = st.multiselect(
        "Seleccione los alumnos a promover",
        options=list(opciones.keys()),
        default=list(opciones.keys()),
    )

    st.caption(
        "Puede desmarcar cualquier alumno que no deba ser promovido."
    )

    st.divider()

    cantidad = len(seleccionados)

    if cantidad == 0:
        st.warning(
            "Debe seleccionar al menos un alumno."
        )
        return

    st.write(
        f"Se procesarán **{cantidad} alumnos**."
    )

    if grado_destino == "Graduado":
        st.error(
            "Los alumnos seleccionados quedarán con estado "
            "'Graduado' y dejarán de aparecer en procesos operativos."
        )
    else:
        st.warning(
            f"Los alumnos seleccionados pasarán a "
            f"**{grado_destino} - ciclo {ciclo_destino}**."
        )

    confirmacion = st.text_input(
        'Para confirmar escriba: PROMOVER'
    )

    confirmar = st.checkbox(
        "Confirmo que deseo ejecutar esta promoción masiva."
    )

    if st.button(
        "🎓 EJECUTAR PROMOCIÓN",
        type="primary",
        width="stretch",
    ):
        if confirmacion.strip().upper() != "PROMOVER":
            st.error(
                "Debe escribir PROMOVER para confirmar."
            )
            return

        if not confirmar:
            st.error(
                "Debe marcar la casilla de confirmación."
            )
            return

        promovidos = 0
        graduados = 0
        errores = []

        fecha = obtener_fecha_hoy().strftime(
            "%d/%m/%Y"
        )

        usuario = st.session_state.get(
            "user_name",
            "Administrador",
        )

        with st.spinner(
            "Procesando promoción..."
        ):
            for etiqueta in seleccionados:
                alumno = opciones[etiqueta]

                nie = alumno["nie"]
                data = alumno["data"]

                try:
                    historial = list(
                        data.get(
                            "historial_academico",
                            []
                        )
                    )

                    if grado_destino == "Graduado":
                        historial.append(
                            {
                                "ciclo": ciclo_origen,
                                "grado": grado_origen,
                                "resultado": "Graduado",
                                "fecha": fecha,
                                "usuario": usuario,
                            }
                        )

                        update_data = {
                            "estado": "Graduado",
                            "activo": False,
                            "fecha_baja": fecha,
                            "fecha_graduacion": fecha,
                            "motivo_baja": "Graduación",
                            "baja_realizada_por": usuario,
                            "ciclo_lectivo": ciclo_origen,
                            "historial_academico": historial,
                            
                        }

                        graduados += 1

                    else:
                        historial.append(
                            {
                                "ciclo": ciclo_origen,
                                "grado": grado_origen,
                                "resultado": "Promovido",
                                "grado_destino": grado_destino,
                                "ciclo_destino": ciclo_destino,
                                "turno_origen": data.get(
                                    "turno", 
                                    "_"
                                ),
                                "turno_destino": (
                                    "Vespertino"
                                    if grado_origen == "Cuarto Grado"
                                    else data.get(
                                        "turno",
                                        "_",
                                    )
                                ),
                                "fecha": fecha,
                                "usuario": usuario,
                            }
                        )

                        nuevo_turno = data.get(
                            "turno", 
                            "Matutino"
                        )

                        if grado_origen == "Cuarto Grado":
                            nuevo_turno = "Vespertino"

                        update_data = {
                            "grado_anterior": grado_origen,
                            "grado_actual": grado_destino,
                            "ciclo_lectivo": ciclo_destino,
                            "turno": nuevo_turno,
                            "estado": "Activo",
                            "activo": True,
                            "fecha_promocion": fecha,
                            "promovido_por": usuario,
                            "historial_academico": historial,
                        }

                        promovidos += 1

                    db.collection(
                        "alumnos"
                    ).document(
                        nie
                    ).update(
                        update_data
                    )

                except Exception as error:
                    errores.append(
                        f"{nie}: {error}"
                    )

        st.success(
            "Proceso de promoción finalizado."
        )

        if promovidos:
            st.write(
                f"✅ Promovidos: {promovidos}"
            )

        if graduados:
            st.write(
                f"🎓 Graduados: {graduados}"
            )

        if errores:
            st.error(
                f"Se encontraron {len(errores)} errores."
            )

            for error in errores:
                st.write(error)

        else:
            st.success(
                "No se reportaron errores."
            )

        time.sleep(2)
        st.rerun()