import streamlit as st

def mostrar_sidebar(nombre_usuario, rol_usuario):
    """
    Sidebar principal de EduManager.

    Mantiene la página seleccionada utilizando
    st.session_state y devuelve el nombre exacto
    que espera app.py.
    """

    # Página inicial
    if "menu_actual" not in st.session_state:
        st.session_state["menu_actual"] = "Inicio"

    with st.sidebar:

        # ==========================================
        # IDENTIDAD
        # ==========================================
        try:
            st.image("logo.png", width=85)
        except Exception:
            pass

        st.markdown("### EduManager")
        st.caption("Gestión Académica Institucional")

        st.markdown(
            "<div style='height:8px'></div>",
            unsafe_allow_html=True
        )
        # ==========================================
        # USUARIO
        # ==========================================
        st.markdown(f"**👤 {nombre_usuario}**")

        if rol_usuario == "admin":
            st.caption("Administrador")
        elif rol_usuario == "docente":
            st.caption("Docente")
        else:
            st.caption(str(rol_usuario).capitalize())

        st.divider()

        # ==========================================
        # FUNCIÓN INTERNA PARA BOTONES
        # ==========================================
        def opcion_menu(texto, pagina, key):
            seleccionada = (
                st.session_state["menu_actual"] == pagina
            )

            tipo = "primary" if seleccionada else "secondary"

            if st.button(
                texto,
                key=key,
                width="stretch",
                type=tipo
            ):
                st.session_state["menu_actual"] = pagina
                st.rerun()

        # ==========================================
        # ADMINISTRADOR
        # ==========================================
        if rol_usuario == "admin":

            st.markdown(
                "<div class='menu-section-title'>PRINCIPAL</div>",
                unsafe_allow_html=True
            )

            opcion_menu(
                "🏠  Inicio",
                "Inicio",
                "menu_inicio_admin"
            )

            st.markdown(
                "<div class='menu-section-title'>GESTIÓN ACADÉMICA</div>",
                unsafe_allow_html=True
            )

            opcion_menu(
                "🎓  Inscripción",
                "Inscripción",
                "menu_inscripcion"
            )

            opcion_menu(
                "🔎  Consulta Alumnos",
                "Consulta Alumnos",
                "menu_alumnos"
            )

            opcion_menu(
                "👩‍🏫  Maestros",
                "Maestros",
                "menu_maestros"
            )

            opcion_menu(
                "📅  Asistencia Global",
                "Asistencia Global",
                "menu_asistencia"
            )

            opcion_menu(
                "📊  Notas",
                "Notas",
                "menu_notas"
            )

            st.markdown(
                "<div class='menu-section-title'>ADMINISTRACIÓN</div>",
                unsafe_allow_html=True
            )

            opcion_menu(
                "💰  Finanzas",
                "Finanzas",
                "menu_finanzas"
            )

            opcion_menu(
                "🎓  Promoción de Grado",
                "Promoción de Grado",
                "menu_promocion"
            )

            st.markdown(
                "<div class='menu-section-title'>SISTEMA</div>",
                unsafe_allow_html=True
            )

            opcion_menu(
                "⚙️  Configuración",
                "Configuración (Usuarios)",
                "menu_configuracion"
            )

        # ==========================================
        # DOCENTE
        # ==========================================
        else:

            st.markdown(
                "<div class='menu-section-title'>PRINCIPAL</div>",
                unsafe_allow_html=True
            )

            opcion_menu(
                "🏠  Inicio",
                "Inicio",
                "menu_inicio_docente"
            )

            st.markdown(
                "<div class='menu-section-title'>ACADÉMICO</div>",
                unsafe_allow_html=True
            )

            opcion_menu(
                "📋  Mis Listados",
                "Mis Listados",
                "menu_listados"
            )

            opcion_menu(
                "📅  Tomar Asistencia",
                "Tomar Asistencia",
                "menu_tomar_asistencia"
            )

            opcion_menu(
                "📝  Cargar Notas",
                "Cargar Notas",
                "menu_cargar_notas"
            )

            opcion_menu(
                "📚  Ver Mis Cargas",
                "Ver Mis Cargas",
                "menu_mis_cargas"
            )

            opcion_menu(
                "📂  Expediente Alumnos",
                "Expediente Alumnos",
                "menu_expediente_docente"
            )

            opcion_menu(
                "📄  Boletas de Notas",
                "Boletas de Notas",
                "menu_boletas_docente"
            )

        # ==========================================
        # CERRAR SESIÓN
        # ==========================================
        st.divider()

        if st.button(
            "🚪 Cerrar sesión",
            width="stretch",
            key="btn_logout_sidebar"
        ):
            return "__logout__"

        st.caption("©David Fuentes - EduManager · Ciclo 2026")

    return st.session_state["menu_actual"]