from datetime import datetime
from html import escape
from authorization import protected, authorize
from profile_service import read_profile, save_profile, photo_url_allowed
from integrity_service import IntegrityError

import streamlit as st

from config import TZ_SV


@protected('Mi Perfil')
def mostrar_perfil(db, subir_archivo, obtener_fecha_hoy):
    """
    Módulo de Perfil de Usuario editable.
    Permite al usuario cambiar su foto, datos personales, contraseña y preferencias.
    """
    st.title("👤 Mi Perfil")

    usuario_actual = st.session_state.get("user_id", "")

    # ==========================================
    # CARGAR DATOS ACTUALES
    # ==========================================
    try:
        datos_usuario = read_profile(db)
    except Exception as e:
        st.error(f"Error al cargar perfil: {e}")
        return

    # ==========================================
    # HEADER CON FOTO
    # ==========================================
    c_foto, c_info = st.columns([1, 3])

    with c_foto:
        foto_url = datos_usuario.get("foto_url")
        if foto_url and photo_url_allowed(foto_url, usuario_actual):
            st.image(foto_url, width=150)
        else:
            # Avatar con inicial del nombre
            inicial = (datos_usuario.get("nombre") or "?")[0].upper()
            st.markdown(
                f"""
                <div style="
                    width:150px; height:150px;
                    border-radius:50%;
                    background:linear-gradient(135deg, #1e3a8a, #3b82f6);
                    display:flex; align-items:center; justify-content:center;
                    font-size:60px; color:white; font-weight:bold;
                    margin:auto;
                    box-shadow:0 4px 12px rgba(0,0,0,0.15);
                ">
                    {escape(inicial)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
        nueva_foto = st.file_uploader(
            "📷 Cambiar foto",
            type=["jpg", "jpeg", "png"],
            key="foto_perfil",
        )

    with c_info:
        st.markdown(f"## {datos_usuario.get('nombre', 'Usuario')}")
        st.caption(f"@{usuario_actual} · {datos_usuario.get('rol', 'usuario').upper()}")
        st.write("")
        email = datos_usuario.get("email", "")
        tel = datos_usuario.get("telefono", "")
        if email:
            st.write(f"📧 {email}")
        if tel:
            st.write(f"📱 {tel}")
        bio = datos_usuario.get("bio", "")
        if bio:
            st.write(f"\n{bio}")

    st.divider()

    # ==========================================
    # PESTAÑAS
    # ==========================================
    tab_datos, tab_seguridad, tab_preferencias = st.tabs(
        [
            "📝 Datos personales",
            "🔒 Seguridad",
            "⚙️ Preferencias",
        ]
    )

    # ==========================================
    # TAB 1: DATOS PERSONALES
    # ==========================================
    with tab_datos:
        with st.form("form_datos_personales"):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input(
                    "Nombre completo",
                    value=datos_usuario.get("nombre", ""),
                )
                email = st.text_input(
                    "Correo electrónico",
                    value=datos_usuario.get("email", "") or "",
                )
            with c2:
                telefono = st.text_input(
                    "Teléfono",
                    value=datos_usuario.get("telefono", "") or "",
                )
                rol = st.selectbox(
                    "Rol",
                    ["admin", "docente"],
                    index=0 if datos_usuario.get("rol") == "admin" else 1,
                    disabled=True,
                )
            bio = st.text_area(
                "Biografía / Descripción",
                value=datos_usuario.get("bio", "") or "",
                placeholder="Cuéntanos sobre ti...",
                height=100,
            )

            if st.form_submit_button(
                "💾 Guardar cambios", type="primary", use_container_width=True
            ):
                if not nombre.strip():
                    st.error("El nombre es obligatorio.")
                    return

                update_data = {
                    "nombre": nombre.strip(),
                    "email": email.strip() if email else None,
                    "telefono": telefono.strip() if telefono else None,
                    "bio": bio.strip(),
                    "ultimo_acceso": datetime.now(TZ_SV).isoformat(),
                }

                try:
                    if nueva_foto:
                        # La subida es independiente del commit; nunca se guarda una URL fallida.
                        from PIL import Image
                        if nueva_foto.size > 5 * 1024 * 1024:
                            raise IntegrityError("La fotografía no puede superar 5 MB.")
                        try:
                            Image.open(nueva_foto).verify()
                        finally:
                            nueva_foto.seek(0)
                        authorize(db, 'Mi Perfil')
                        url = subir_archivo(nueva_foto, f"perfiles/{usuario_actual}")
                        if not url:
                            raise IntegrityError("No se pudo subir la fotografía; el perfil no se guardó.")
                        update_data['foto_url'] = url
                    update_data.pop('ultimo_acceso', None)
                    save_profile(db, 'personal', update_data)

                    # Actualizar session_state
                    st.session_state["user_name"] = nombre.strip()

                    st.success("✅ Perfil actualizado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    # ==========================================
    # TAB 2: SEGURIDAD
    # ==========================================
    with tab_seguridad:
        st.markdown("### 🔑 Cambiar contraseña")
        st.caption("Tu contraseña está protegida con hash bcrypt.")

        with st.form("form_password"):
            pass_actual = st.text_input("Contraseña actual", type="password")
            pass_nueva = st.text_input("Nueva contraseña", type="password")
            pass_confirm = st.text_input("Confirmar nueva contraseña", type="password")

            if st.form_submit_button(
                " Cambiar contraseña", type="primary", use_container_width=True
            ):
                if not pass_actual or not pass_nueva or not pass_confirm:
                    st.error("Completa todos los campos.")
                    return
                if pass_nueva != pass_confirm:
                    st.error("Las contraseñas nuevas no coinciden.")
                    return
                if len(pass_nueva) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                    return

                try:
                    save_profile(db, 'password', current_password=pass_actual, new_password=pass_nueva)
                    st.success("✅ Contraseña cambiada correctamente.")
                except Exception as e:
                    st.error(f"Error al cambiar contraseña: {e}")

        st.divider()
        st.markdown("### 📊 Información de la cuenta")
        st.write(f"**Usuario:** @{usuario_actual}")
        st.write(f"**Rol:** {datos_usuario.get('rol', 'usuario').upper()}")
        st.write(f"**Cuenta creada:** {datos_usuario.get('created_at', 'Desconocido')}")
        st.write(
            f"**Estado:** {'✅ Activa' if datos_usuario.get('activo') else ' Inactiva'}"
        )

    # ==========================================
    # TAB 3: PREFERENCIAS
    # ==========================================
    with tab_preferencias:
        st.markdown("### 🎨 Apariencia")
        tema = st.selectbox(
            "Tema",
            ["claro", "oscuro", "automático"],
            index=["claro", "oscuro", "automático"].index(
                datos_usuario.get("tema", "claro")
            )
            if datos_usuario.get("tema", "claro") in ["claro", "oscuro", "automático"]
            else 0,
        )

        st.markdown("### 🔔 Notificaciones")
        notificaciones_email = st.toggle(
            "Recibir notificaciones por correo",
            value=bool(datos_usuario.get("notificaciones_email", True)),
        )

        if st.button("💾 Guardar preferencias", type="primary"):
            try:
                save_profile(db, 'preferences', {
                    'tema': tema, 'notificaciones_email': notificaciones_email,
                })
                st.success("✅ Preferencias guardadas.")
            except Exception as e:
                st.error(f"Error al guardar: {e}")
