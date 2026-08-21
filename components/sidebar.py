import streamlit as st


def mostrar_sidebar(nombre_usuario, rol_usuario):
    """
    Construye el menú lateral principal de EduManager.

    Recibe:
        nombre_usuario: nombre que se mostrará en el menú.
        rol_usuario: rol actual (admin, docente, etc.).

    Devuelve:
        La opción seleccionada por el usuario.
    """

    with st.sidebar:

        # ==========================================
        # IDENTIDAD DEL SISTEMA
        # ==========================================

        try:
            st.image("logo.png", width=85)
        except Exception:
            pass

        st.markdown("### EduManager")
        st.caption("Gestión Académica Institucional")

        st.divider()

        # ==========================================
        # USUARIO ACTUAL
        # ==========================================

        st.markdown(f"**👤 {nombre_usuario}**")

        if rol_usuario == "admin":
            st.caption("Administrador")
        elif rol_usuario == "docente":
            st.caption("Docente")
        else:
            st.caption(rol_usuario.capitalize())

        st.divider()

        # ==========================================
        # MENÚ SEGÚN ROL
        # ==========================================

        if rol_usuario == "docente":

            opciones = [
                "🏠 Inicio",
                "📋 Mi Asistencia",
                "📝 Mis Notas",
            ]

        else:

            opciones = [
                "🏠 Inicio",
                "🎓 Inscripción",
                "🔎 Consulta Alumnos",
                "👩‍🏫 Maestros",
                "📅 Asistencia Global",
                "📊 Notas",
                "💰 Finanzas",
                "⚙️ Configuración",
            ]

        opcion = st.radio(
            "Navegación",
            opciones,
            label_visibility="collapsed"
        )

        st.divider()

        st.caption("EduManager · Ciclo 2026")

        return opcion