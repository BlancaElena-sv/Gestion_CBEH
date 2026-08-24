import time

import pandas as pd
import streamlit as st


def mostrar_configuracion(
    db,
    generar_hash,
    borrar_coleccion,
):
    """
    Módulo de configuración administrativa.

    Incluye:
    - Gestión de usuarios
    - Creación y actualización de credenciales
    - Roles
    - Contraseñas con hash
    - Herramientas de mantenimiento de base de datos
    """

    st.header("⚙️ Configuración")

    tab_usuarios, tab_db = st.tabs(
        [
            "👥 Usuarios",
            "⚠️ Base de Datos",
        ]
    )

    # ========================================================
    # USUARIOS
    # ========================================================

    with tab_usuarios:

        st.subheader(
            "👥 Gestión de Usuarios"
        )

        # ----------------------------------------------------
        # LISTADO
        # ----------------------------------------------------

        try:
            usuarios_ref = (
                db.collection("usuarios")
                .stream()
            )

            usuarios = []

            for documento in usuarios_ref:
                datos = documento.to_dict()

                datos_visible = {
                    "usuario": datos.get(
                        "usuario",
                        documento.id
                    ),
                    "nombre": datos.get(
                        "nombre",
                        ""
                    ),
                    "rol": datos.get(
                        "rol",
                        ""
                    ),
                    "estado": (
                        "Activo"
                        if datos.get("activo", True)
                        else "Baja"
                    ),
                }

                usuarios.append(
                    datos_visible
                )

            # Ocultar superadmin a otros administradores
            if (
                st.session_state.get("user_id")
                != "david"
            ):
                usuarios = [
                    usuario
                    for usuario in usuarios
                    if usuario.get("usuario") != "david"
                ]

            if usuarios:
                df_usuarios = pd.DataFrame(
                    usuarios
                )

                st.dataframe(
                    df_usuarios,
                    width="stretch",
                    hide_index=True,
                )

            else:
                st.info(
                    "No hay usuarios registrados."
                )

        except Exception as error:
            st.error(
                "No se pudo cargar "
                f"la lista de usuarios: {error}"
            )

        st.divider()
        st.subheader("🛡️ Estado y eliminación de usuarios")

        try:
            usuarios_ref = db.collection("usuarios").stream()

            mapa_usuarios = {}

            for documento in usuarios_ref:
                datos = documento.to_dict()

                user_id = datos.get(
                    "usuario",
                    documento.id
                )

                nombre_usuario = datos.get(
                    "nombre",
                    user_id
                )

                activo = datos.get(
                    "activo",
                    True
                )

                estado_texto = (
                    "ACTIVO"
                    if activo
                    else "BAJA"
                )

                etiqueta = (
                    f"{user_id} - "
                    f"{nombre_usuario} "
                    f"[{estado_texto}]"
                )

                mapa_usuarios[etiqueta] = {
                    "id": documento.id,
                    "data": datos,
                }

            if not mapa_usuarios:
                st.info(
                    "No hay usuarios disponibles."
                )
            else:
                usuario_sel = st.selectbox(
                    "Seleccione usuario",
                    ["Seleccionar..."]
                    + sorted(mapa_usuarios.keys()),
                    key="gestion_usuario_sel"
                )

                if usuario_sel != "Seleccionar...":

                    info = mapa_usuarios[
                        usuario_sel
                    ]

                    usuario_id = info["id"]
                    usuario_data = info["data"]

                    activo_actual = (
                        usuario_data.get(
                            "activo",
                            True
                        )
                    )

                    st.write(
                        f"**Usuario:** {usuario_id}"
                    )

                    st.write(
                        f"**Nombre:** "
                        f"{usuario_data.get('nombre', '')}"
                    )

                    st.write(
                        f"**Rol:** "
                        f"{usuario_data.get('rol', '')}"
                    )

                    if activo_actual:
                        st.success(
                            "✅ Usuario actualmente ACTIVO"
                        )
                    else:
                        st.warning(
                            "⚠️ Usuario dado de BAJA"
                        )

                    st.divider()

                    # ======================================
                    # DAR DE BAJA / REACTIVAR
                    # ======================================

                    st.markdown("### 🟠 Estado del usuario")

                    if activo_actual:

                        if st.button(
                            "🟠 Dar de baja usuario",
                            key=f"baja_user_{usuario_id}"
                        ):

                            if (
                                usuario_id
                                == st.session_state.get(
                                    "user_id"
                                )
                            ):
                                st.error(
                                    "No puede darse de baja "
                                    "a sí mismo."
                                )

                            elif usuario_id == "david":
                                st.error(
                                    "El Super Admin no puede "
                                    "ser dado de baja."
                                )

                            else:
                                db.collection(
                                    "usuarios"
                                ).document(
                                    usuario_id
                                ).update(
                                    {
                                        "activo": False,
                                        "fecha_baja": (
                                            time.strftime(
                                                "%d/%m/%Y"
                                            )
                                        ),
                                        "baja_realizada_por": (
                                            st.session_state.get(
                                                "user_name",
                                                "Administrador"
                                            )
                                        ),
                                    }
                                )

                                st.success(
                                    "✅ Usuario dado de baja."
                                )

                                time.sleep(1)
                                st.rerun()

                    else:

                        if usuario_data.get(
                            "fecha_baja"
                        ):
                            st.write(
                                f"**Fecha de baja:** "
                                f"{usuario_data.get('fecha_baja')}"
                            )

                        if usuario_data.get(
                            "baja_realizada_por"
                        ):
                            st.write(
                                f"**Registrado por:** "
                                f"{usuario_data.get('baja_realizada_por')}"
                            )

                        if st.button(
                            "♻️ Reactivar usuario",
                            key=f"reactivar_user_{usuario_id}"
                        ):

                            db.collection(
                                "usuarios"
                            ).document(
                                usuario_id
                            ).update(
                                {
                                    "activo": True,
                                    "fecha_baja": None,
                                    "baja_realizada_por": None,
                                }
                            )

                            st.success(
                                "✅ Usuario reactivado."
                            )

                            time.sleep(1)
                            st.rerun()

                    # ======================================
                    # ELIMINACIÓN DEFINITIVA
                    # ======================================

                    st.divider()
                    st.markdown("### 🔴 Eliminar usuario")

                    st.error(
                        "Esta acción elimina definitivamente "
                        "la cuenta de acceso."
                    )

                    confirmacion = st.text_input(
                        f"Escriba el usuario "
                        f"'{usuario_id}' para confirmar:",
                        key=f"confirm_delete_user_{usuario_id}"
                    )

                    confirmar_eliminacion = st.checkbox(
                        "Entiendo que esta acción "
                        "no se puede deshacer.",
                        key=f"check_delete_user_{usuario_id}"
                    )

                    if st.button(
                        "🗑️ ELIMINAR USUARIO",
                        key=f"delete_user_{usuario_id}"
                    ):

                        if usuario_id == "david":
                            st.error(
                                "⛔ El Super Admin no puede "
                                "ser eliminado."
                            )

                        elif (
                            usuario_id
                            == st.session_state.get(
                                "user_id"
                            )
                        ):
                            st.error(
                                "No puede eliminar "
                                "su propio usuario."
                            )

                        elif (
                            confirmacion.strip()
                            != usuario_id
                        ):
                            st.error(
                                "El usuario escrito "
                                "no coincide."
                            )

                        elif not confirmar_eliminacion:
                            st.error(
                                "Debe confirmar que "
                                "comprende la eliminación."
                            )

                        else:
                            db.collection(
                                "usuarios"
                            ).document(
                                usuario_id
                            ).delete()

                            st.success(
                                "✅ Usuario eliminado "
                                "definitivamente."
                            )

                            time.sleep(1)
                            st.rerun()

        except Exception as error:
            st.error(
                f"No se pudo gestionar "
                f"los usuarios: {error}"
            )

        # ----------------------------------------------------
        # CREAR / ACTUALIZAR
        # ----------------------------------------------------

        st.subheader(
            "➕ Crear / Actualizar Credencial"
        )

        with st.form(
            "form_usuario"
        ):

            c1, c2 = st.columns(2)

            usuario = c1.text_input(
                "Usuario (ID)"
            )

            password = c2.text_input(
                "Contraseña",
                type="password"
            )

            nombre = c1.text_input(
                "Nombre Real"
            )

            rol = c2.selectbox(
                "Rol",
                [
                    "docente",
                    "admin",
                ]
            )

            guardar = (
                st.form_submit_button(
                    "💾 Guardar Usuario",
                    type="primary",
                    width="stretch",
                )
            )

            if guardar:

                usuario = (
                    usuario
                    .strip()
                    .lower()
                )

                nombre = (
                    nombre.strip()
                )

                # ============================================
                # VALIDACIONES
                # ============================================

                if not usuario:

                    st.error(
                        "El usuario es obligatorio."
                    )

                    return

                if not nombre:

                    st.error(
                        "El nombre es obligatorio."
                    )

                    return

                if not password:

                    st.error(
                        "La contraseña es obligatoria."
                    )

                    return

                if len(password) < 6:

                    st.error(
                        "La contraseña debe tener "
                        "al menos 6 caracteres."
                    )

                    return

                # ============================================
                # PROTEGER SUPERADMIN
                # ============================================

                if (
                    usuario == "david"
                    and st.session_state.get(
                        "user_id"
                    )
                    != "david"
                ):

                    st.error(
                        "⛔ No tienes permiso "
                        "para modificar al Super Admin."
                    )

                    return

                try:

                    password_hash = (
                        generar_hash(
                            password
                        )
                    )

                    doc_actual = (
                        db.collection("usuarios")
                        .document(usuario)
                        .get()
                    )

                    datos_usuario = {
                        "usuario": usuario,
                        "password_hash": password_hash,
                        "rol": rol,
                        "nombre": nombre,
                    }

                    if not doc_actual.exists:
                        datos_usuario["activo"] = True

                    db.collection("usuarios").document(usuario).set(
                        datos_usuario,
                        merge=True,
                    )

                    db.collection(
                        "usuarios"
                    ).document(
                        usuario
                    ).set(
                        datos_usuario,
                        merge=True,
                    )

                    st.success(
                        "✅ Usuario creado "
                        "o actualizado correctamente."
                    )

                    time.sleep(1)
                    st.rerun()

                except Exception as error:

                    st.error(
                        f"No se pudo guardar "
                        f"el usuario: {error}"
                    )

    # ========================================================
    # BASE DE DATOS
    # ========================================================

    with tab_db:

        st.subheader(
            "⚠️ Herramientas de Base de Datos"
        )

        if (
            st.session_state.get(
                "user_id"
            )
            != "david"
        ):

            st.info(
                "Esta sección está reservada "
                "para el desarrollador."
            )

            return

        st.error(
            "⚠️ ZONA DE PELIGRO"
        )

        st.warning(
            "Estas operaciones pueden eliminar "
            "información de forma permanente."
        )

        st.markdown(
            "### 🔴 Borrar Base de Datos"
        )

        st.write(
            "Esta acción eliminará:"
        )

        st.markdown(
            """
            - Alumnos
            - Maestros
            - Cargas académicas
            - Finanzas
            - Notas
            - Usuarios
            """
        )

        st.error(
            "La acción NO puede deshacerse."
        )

        confirmacion = (
            st.text_input(
                "Escriba BORRAR para confirmar:",
                key="confirmar_borrado_db",
            )
        )

        aceptar = (
            st.checkbox(
                "Entiendo que esta acción "
                "eliminará permanentemente "
                "la información.",
                key="check_borrar_db",
            )
        )

        if st.button(
            "🔴 BORRAR TODO",
            type="primary",
            width="stretch",
        ):

            if (
                confirmacion.strip()
                != "BORRAR"
            ):

                st.error(
                    "Debe escribir BORRAR "
                    "exactamente."
                )

                return

            if not aceptar:

                st.error(
                    "Debe confirmar que comprende "
                    "que esta acción es irreversible."
                )

                return

            try:

                with st.spinner(
                    "Eliminando información..."
                ):

                    colecciones = [
                        "alumnos",
                        "maestros_perfil",
                        "carga_academica",
                        "finanzas",
                        "notas",
                        "notas_mensuales",
                        "asistencia",
                        "bitacora",
                        "usuarios",
                    ]

                    for coleccion in colecciones:

                        borrar_coleccion(
                            coleccion
                        )

                    # ========================================
                    # RECREAR SUPERADMIN CON HASH
                    # ========================================

                    password_temporal = (
                        "admin123"
                    )

                    db.collection(
                        "usuarios"
                    ).document(
                        "david"
                    ).set(
                        {
                            "usuario": "david",
                            "password_hash": (
                                generar_hash(
                                    password_temporal
                                )
                            ),
                            "rol": "admin",
                            "nombre": (
                                "David Fuentes (Dev)"
                            ),
                        }
                    )

                st.success(
                    "✅ Base de datos reiniciada."
                )

                st.warning(
                    "El Super Admin fue recreado "
                    "con la contraseña temporal "
                    "`admin123`. Cámbiela inmediatamente."
                )

            except Exception as error:

                st.error(
                    f"No se pudo completar "
                    f"el borrado: {error}"
                )