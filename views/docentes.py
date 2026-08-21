import time

import pandas as pd
import streamlit as st
from firebase_admin import firestore
from config import CICLO_LECTIVO


def mostrar_maestros(
    db,
    lista_grados,
    mapa_curricular,
    subir_archivo,
    obtener_fecha_hoy,
    obtener_hora_actual,
    verificar_pago_duplicado_hoy,
):
    """
    Vista de gestión docente.

    Permite:
    - Registrar docentes.
    - Consultar perfil.
    - Editar información.
    - Asignar carga académica.
    - Registrar movimientos financieros.
    """

    st.title("👩‍🏫 Gestión Docente")

    # ==========================================
    # CARGAR DOCENTES
    # ==========================================

    docs_m = db.collection("maestros_perfil").stream()

    mapa_profesores = {}

    for documento in docs_m:
        data = documento.to_dict()

        nombre = data.get("nombre", "Sin Nombre")
        codigo = data.get("codigo", "S/C")

        estado_texto = (
            "ACTIVO"
            if data.get("activo", True)
            else "BAJA"
        )

        key_name = (
            f"{codigo} - {nombre} "
            f"[{estado_texto}]"
        )

        mapa_profesores[key_name] = {
            "id": documento.id,
            "data": data,
        }

    opciones_prof = [
        "➕ Registrar Nuevo Maestro"
    ] + sorted(mapa_profesores.keys())

    col_sel, _ = st.columns([2, 1])

    with col_sel:
        sel_prof = st.selectbox(
            "Seleccionar Docente:",
            opciones_prof,
            key="sel_prof_main",
        )

    st.markdown("---")

    # ==========================================
    # NUEVO DOCENTE
    # ==========================================

    if sel_prof == "➕ Registrar Nuevo Maestro":

        with st.form("new_prof"):
            c1, c2 = st.columns(2)

            codigo = c1.text_input("Código")
            nombre = c2.text_input("Nombre")

            telefono = c1.text_input("Teléfono")
            email = c2.text_input("Email")

            direccion = st.text_area("Dirección")

            foto = st.file_uploader(
                "Foto",
                ["jpg", "jpeg", "png"]
            )

            guardar = st.form_submit_button(
                "💾 Guardar",
                width="stretch"
            )

            if guardar:

                nombre = nombre.strip()
                codigo = codigo.strip()

                if not nombre:
                    st.error(
                        "El nombre del docente es obligatorio."
                    )
                    return

                try:
                    foto_url = None

                    if foto:
                        foto_url = subir_archivo(
                            foto,
                            f"profesores/{codigo or 'SN'}"
                        )

                    db.collection(
                        "maestros_perfil"
                    ).add(
                        {
                            "codigo": codigo,
                            "nombre": nombre,
                            "telefono": telefono,
                            "email": email,
                            "direccion": direccion,
                            "foto_url": foto_url,
                            "fecha_ingreso": (
                                obtener_fecha_hoy()
                                .strftime("%d/%m/%Y")
                            ),
                            "activo": True,
                        }
                    )

                    st.success(
                        "✅ Docente registrado correctamente."
                    )

                    time.sleep(1)
                    st.rerun()

                except Exception as error:
                    st.error(
                        f"Error al registrar docente: {error}"
                    )

        return

    # ==========================================
    # DOCENTE SELECCIONADO
    # ==========================================

    if sel_prof not in mapa_profesores:
        return

    prof_info = mapa_profesores[sel_prof]

    pid = prof_info["id"]
    prof_data = prof_info["data"]

    # ==========================================
    # TARJETA DE PERFIL
    # ==========================================

    with st.container(border=True):

        c1, c2, c3 = st.columns(
            [1, 3, 1]
        )

        with c1:
            url_m = prof_data.get(
                "foto_url"
            )

            if url_m:
                st.image(
                    url_m,
                    width=120
                )
            else:
                st.markdown(
                    "<h1>👤</h1>",
                    unsafe_allow_html=True
                )

        with c2:
            st.title(
                prof_data.get(
                    "nombre",
                    "Sin Nombre"
                )
            )

            st.caption(
                f"Código: "
                f"{prof_data.get('codigo', 'S/C')}"
            )

            st.write(
                f"📞 "
                f"{prof_data.get('telefono', '-')} "
                f"| 📧 "
                f"{prof_data.get('email', '-')}"
            )

        with c3:
            if st.button(
                "✏️ Editar Perfil",
                key=f"btn_edit_{pid}"
            ):
                st.session_state[
                    "edit_prof_mode"
                ] = True

    # ==========================================
    # EDICIÓN DEL PERFIL
    # ==========================================

    if st.session_state.get(
        "edit_prof_mode"
    ):

        with st.form("edit_prof_form"):

            nuevo_nombre = st.text_input(
                "Nombre",
                prof_data.get(
                    "nombre",
                    ""
                )
            )

            nuevo_telefono = st.text_input(
                "Teléfono",
                prof_data.get(
                    "telefono",
                    ""
                )
            )

            nuevo_email = st.text_input(
                "Email",
                prof_data.get(
                    "email",
                    ""
                )
            )

            nueva_direccion = st.text_area(
                "Dirección",
                prof_data.get(
                    "direccion",
                    ""
                )
            )

            nueva_foto = st.file_uploader(
                "Nueva Foto",
                [
                    "jpg",
                    "jpeg",
                    "png"
                ]
            )

            if st.form_submit_button(
                "💾 Guardar Cambios"
            ):

                actualizacion = {
                    "nombre": nuevo_nombre,
                    "telefono": nuevo_telefono,
                    "email": nuevo_email,
                    "direccion": nueva_direccion,
                }

                if nueva_foto:

                    url = subir_archivo(
                        nueva_foto,
                        (
                            "profesores/"
                            f"{prof_data.get('codigo', 'SN')}"
                        )
                    )

                    if url:
                        actualizacion[
                            "foto_url"
                        ] = url

                db.collection(
                    "maestros_perfil"
                ).document(
                    pid
                ).update(
                    actualizacion
                )

                st.session_state[
                    "edit_prof_mode"
                ] = False

                st.success(
                    "✅ Perfil actualizado."
                )

                time.sleep(1)
                st.rerun()

    # ==========================================
    # PESTAÑAS
    # ==========================================

    tabs_m = st.tabs(
        [
            "📚 Carga Académica",
            "💰 Historial Financiero",
            "🛡️ Estado y Baja",
        ]
    )

    # ==========================================
    # CARGA ACADÉMICA
    # ==========================================

    with tabs_m[0]:

        c_asig, c_tabla = st.columns(
            [1, 2]
        )

        with c_asig:

            st.markdown(
                "#### Asignar Nueva Materia"
            )

            grado_sel = st.selectbox(
                "Grado",
                lista_grados,
                key="g_prof"
            )

            materias_disponibles = (
                mapa_curricular.get(
                    grado_sel,
                    []
                )
            )

            with st.form(
                "add_carga_prof"
            ):

                materias_sel = (
                    st.multiselect(
                        "Materias",
                        materias_disponibles
                    )
                )

                es_guia = st.checkbox(
                    "¿Es Guía?"
                )

                if st.form_submit_button(
                    "Guardar Carga"
                ):

                    if not materias_sel:
                        st.warning(
                            "Seleccione al menos una materia."
                        )
                    else:

                        db.collection(
                            "carga_academica"
                        ).add(
                            {
                                "id_docente": pid,
                                "nombre_docente": (
                                    prof_data.get(
                                        "nombre",
                                        "Desconocido"
                                    )
                                ),
                                "grado": grado_sel,
                                "materias": materias_sel,
                                "es_guia": es_guia,
                                "ciclo_lectivo": CICLO_LECTIVO,
                            }
                        )

                        st.success(
                            "✅ Carga académica asignada."
                        )

                        time.sleep(0.5)
                        st.rerun()

        with c_tabla:

            st.markdown(
                "#### Carga Actual"
            )

            cargas = (
                db.collection(
                    "carga_academica"
                )
                .where(
                    "id_docente",
                    "==",
                    pid
                )
                .stream()
            )

            cargas_encontradas = False

            for carga in cargas:

                cargas_encontradas = True

                datos_carga = (
                    carga.to_dict()
                )

                texto_titulo = (
                    f"{datos_carga.get('grado', '?')}"
                )

                if datos_carga.get(
                    "es_guia"
                ):
                    texto_titulo += (
                        " · GUÍA"
                    )

                with st.expander(
                    texto_titulo
                ):

                    materias = (
                        datos_carga.get(
                            "materias",
                            []
                        )
                    )

                    st.write(
                        ", ".join(materias)
                        if materias
                        else "Sin materias"
                    )

                    if st.button(
                        "🗑️ Eliminar carga",
                        key=(
                            f"del_carga_"
                            f"{carga.id}"
                        )
                    ):

                        db.collection(
                            "carga_academica"
                        ).document(
                            carga.id
                        ).delete()

                        st.rerun()

            if not cargas_encontradas:
                st.info(
                    "El docente aún no tiene "
                    "carga académica asignada."
                )

    # ==========================================
    # FINANZAS DOCENTE
    # ==========================================

    with tabs_m[1]:

        with st.expander(
            "➕ Registrar Movimiento"
        ):

            with st.form("ffin"):

                tipo = st.selectbox(
                    "Tipo",
                    [
                        "Pago Salario (Egreso)",
                        "Préstamo (Deuda)",
                        "Abono Deuda (Ingreso)",
                    ]
                )

                monto = st.number_input(
                    "Monto",
                    min_value=0.01
                )

                descripcion = (
                    st.text_input(
                        "Detalle"
                    )
                )

                if st.form_submit_button(
                    "Registrar"
                ):

                    desc_full = (
                        f"{tipo} - "
                        f"{descripcion}"
                    )

                    duplicado = (
                        verificar_pago_duplicado_hoy(
                            pid,
                            tipo
                        )
                    )

                    if (
                        duplicado
                        and "Salario" in tipo
                    ):

                        st.error(
                            "⛔ Ya existe un pago "
                            "de salario para este "
                            "docente el día de hoy."
                        )

                    else:

                        if "Salario" in tipo:
                            tipo_db = "egreso"

                        elif "Abono" in tipo:
                            tipo_db = "ingreso"

                        else:
                            tipo_db = "interno"

                        db.collection(
                            "finanzas"
                        ).add(
                            {
                                "tipo": tipo_db,
                                "categoria_persona": (
                                    "docente"
                                ),
                                "docente_id": pid,
                                "nombre_persona": (
                                    prof_data.get(
                                        "nombre",
                                        ""
                                    )
                                ),
                                "descripcion": desc_full,
                                "monto": monto,
                                "fecha": (
                                    firestore
                                    .SERVER_TIMESTAMP
                                ),
                                "fecha_legible": (
                                    obtener_hora_actual()
                                ),
                            }
                        )

                        st.success(
                            "✅ Movimiento registrado."
                        )

                        time.sleep(1)
                        st.rerun()

        # ==========================================
        # HISTORIAL
        # ==========================================

        movimientos = (
            db.collection("finanzas")
            .where(
                "docente_id",
                "==",
                pid
            )
            .stream()
        )

        lista_movimientos = [
            movimiento.to_dict()
            for movimiento in movimientos
        ]

        lista_movimientos.sort(
            key=lambda x: x.get(
                "fecha_legible",
                ""
            ),
            reverse=True
        )

        if lista_movimientos:

            df = pd.DataFrame(
                lista_movimientos
            )

            columnas = [
                "fecha_legible",
                "descripcion",
                "monto",
            ]

            st.dataframe(
                df[columnas],
                width="stretch"
            )

        else:
            st.info(
                "Sin historial financiero."
            )

    # ==========================================
    # ESTADO, BAJA Y ELIMINACIÓN
    # ==========================================

    with tabs_m[2]:

        st.subheader("🛡️ Gestión del Estado del Docente")

        activo_actual = prof_data.get(
            "activo",
            True
        )

        estado_actual = prof_data.get(
            "estado",
            "Activo" if activo_actual else "Baja"
        )

        col_estado, col_info = st.columns(
            [1, 2]
        )

        with col_estado:

            if activo_actual:
                st.success(
                    "✅ Docente actualmente ACTIVO"
                )
            else:
                st.warning(
                    "⚠️ Docente dado de BAJA"
                )

        with col_info:

            if prof_data.get("fecha_baja"):
                st.write(
                    f"**Fecha de baja:** "
                    f"{prof_data.get('fecha_baja')}"
                )

            if prof_data.get("motivo_baja"):
                st.write(
                    f"**Motivo:** "
                    f"{prof_data.get('motivo_baja')}"
                )

            if prof_data.get(
                "baja_realizada_por"
            ):
                st.write(
                    f"**Registrado por:** "
                    f"{prof_data.get('baja_realizada_por')}"
                )

        st.divider()

        # ==========================================
        # DAR DE BAJA
        # ==========================================

        st.markdown("### 🟠 Dar de baja")

        st.caption(
            "Esta opción conserva el perfil, "
            "historial financiero y carga académica."
        )

        motivos_baja = [
            "Renuncia",
            "Finalización de contrato",
            "Despido",
            "Traslado",
            "Jubilación",
            "Otro",
        ]

        motivo = st.selectbox(
            "Motivo de baja",
            motivos_baja,
            key=f"motivo_baja_doc_{pid}"
        )

        motivo_otro = ""

        if motivo == "Otro":
            motivo_otro = st.text_input(
                "Especifique el motivo",
                key=f"motivo_otro_doc_{pid}"
            )

        if activo_actual:

            if st.button(
                "🟠 Dar de baja al docente",
                key=f"btn_baja_doc_{pid}"
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
                        "activo": False,
                        "estado": "Baja",
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
                        "maestros_perfil"
                    ).document(
                        pid
                    ).update(
                        datos_baja
                    )

                    st.success(
                        "✅ Docente dado de baja correctamente."
                    )

                    time.sleep(1)
                    st.rerun()

        else:

            st.info(
                "El docente ya se encuentra dado de baja."
            )

            if st.button(
                "♻️ Reactivar docente",
                key=f"btn_reactivar_doc_{pid}"
            ):

                datos_reactivacion = {
                    "activo": True,
                    "estado": "Activo",
                    "fecha_baja": None,
                    "motivo_baja": None,
                    "baja_realizada_por": None,
                }

                db.collection(
                    "maestros_perfil"
                ).document(
                    pid
                ).update(
                    datos_reactivacion
                )

                st.success(
                    "✅ Docente reactivado correctamente."
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
            "Se eliminará también la carga académica asociada "
            "y los movimientos financieros vinculados al docente."
        )

        codigo_docente = str(
            prof_data.get(
                "codigo",
                pid
            )
        )

        st.write(
            f"Para confirmar escriba el código: "
            f"**{codigo_docente}**"
        )

        confirmacion = st.text_input(
            "Confirmación",
            key=f"confirm_delete_doc_{pid}"
        )

        confirmar_eliminacion = st.checkbox(
            "Entiendo que esta acción es irreversible.",
            key=f"check_delete_doc_{pid}"
        )

        if st.button(
            "🗑️ ELIMINAR DEFINITIVAMENTE",
            key=f"delete_docente_{pid}"
        ):

            if (
                confirmacion.strip()
                != codigo_docente
            ):

                st.error(
                    "El código escrito no coincide."
                )

            elif not confirmar_eliminacion:

                st.error(
                    "Debe confirmar que comprende "
                    "que la eliminación es irreversible."
                )

            else:

                try:

                    # ==================================
                    # 1. CARGA ACADÉMICA
                    # ==================================

                    cargas = (
                        db.collection(
                            "carga_academica"
                        )
                        .where(
                            "id_docente",
                            "==",
                            pid
                        )
                        .stream()
                    )

                    cargas_eliminadas = 0

                    for carga in cargas:
                        carga.reference.delete()
                        cargas_eliminadas += 1

                    # ==================================
                    # 2. FINANZAS DEL DOCENTE
                    # ==================================

                    movimientos = (
                        db.collection(
                            "finanzas"
                        )
                        .where(
                            "docente_id",
                            "==",
                            pid
                        )
                        .stream()
                    )

                    movimientos_eliminados = 0

                    for movimiento in movimientos:
                        movimiento.reference.delete()
                        movimientos_eliminados += 1

                    # ==================================
                    # 3. PERFIL PRINCIPAL
                    # ==================================

                    db.collection(
                        "maestros_perfil"
                    ).document(
                        pid
                    ).delete()

                    # Limpiar estados relacionados
                    if (
                        "edit_prof_mode"
                        in st.session_state
                    ):
                        del st.session_state[
                            "edit_prof_mode"
                        ]

                    st.success(
                        "✅ Docente y registros relacionados "
                        "eliminados definitivamente."
                    )

                    st.write(
                        f"Cargas académicas eliminadas: "
                        f"{cargas_eliminadas}"
                    )

                    st.write(
                        f"Movimientos financieros eliminados: "
                        f"{movimientos_eliminados}"
                    )

                    time.sleep(2)
                    st.rerun()

                except Exception as error:

                    st.error(
                        "No se pudo completar la eliminación: "
                        f"{error}"
                    )