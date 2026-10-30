import uuid
from datetime import date, datetime

import streamlit as st
from postgrest.exceptions import APIError

from config import CICLO_LECTIVO, TZ_SV


def mostrar_configuracion_dashboard(db):
    st.subheader("🖥️ Configuración del Dashboard")
    st.caption("Administre avisos y actividades sin modificar el código.")

    tab_aviso, tab_agenda = st.tabs(["📢 Aviso institucional", "📅 Agenda"])

    # ========================================================
    # AVISO
    # ========================================================
    with tab_aviso:
        # SUPABASE: Obtener configuración del dashboard
        res_config = (
            db.table("configuracion").select("*").eq("id", "dashboard").execute()
        )
        data = res_config.data[0] if res_config.data else {}

        with st.form("form_config_dashboard"):
            titulo_admin = st.text_input(
                "Título panel administrativo",
                value=data.get("titulo_admin", "Panel Administrativo"),
            )
            titulo_docente = st.text_input(
                "Título panel docente",
                value=data.get("titulo_docente", "Panel Docente"),
            )
            estado_sistema = st.text_input(
                "Estado del sistema",
                value=data.get("estado_sistema", "Operativo"),
            )
            aviso_activo = st.checkbox(
                "Mostrar aviso institucional",
                value=data.get("aviso_activo", False),
            )
            aviso_titulo = st.text_input(
                "Título del aviso",
                value=data.get("aviso_titulo", "Aviso institucional"),
            )
            aviso_mensaje = st.text_area(
                "Mensaje",
                value=data.get("aviso_mensaje", ""),
                height=130,
            )

            guardar = st.form_submit_button("💾 Guardar configuración", type="primary")

            if guardar:
                # SUPABASE: Upsert de la configuración
                datos_config = {
                    "id": "dashboard",
                    "titulo_admin": (titulo_admin or "").strip(),
                    "titulo_docente": (titulo_docente or "").strip(),
                    "estado_sistema": (estado_sistema or "").strip(),
                    "aviso_activo": aviso_activo,
                    "aviso_titulo": (aviso_titulo or "").strip(),
                    "aviso_mensaje": (aviso_mensaje or "").strip(),
                    "ciclo_lectivo": CICLO_LECTIVO,
                    "actualizado_en": datetime.now(TZ_SV).isoformat(),
                }
                db.table("configuracion").upsert(datos_config).execute()

                st.success("✅ Configuración actualizada.")
                st.rerun()

    # ========================================================
    # AGENDA
    # ========================================================
    with tab_agenda:
        st.markdown("### ➕ Nueva actividad")

        with st.form("form_nueva_actividad"):
            fecha = st.date_input("Fecha", value=date.today())
            titulo = st.text_input("Actividad")
            descripcion = st.text_area("Descripción")
            audiencia = st.selectbox(
                "Visible para", ["Todos", "Docentes", "Administración"]
            )
            estado = st.selectbox(
                "Estado", ["Programado", "Pendiente", "En Curso", "Finalizado"]
            )

            guardar_actividad = st.form_submit_button(
                "➕ Agregar actividad", type="primary"
            )

            if guardar_actividad:
                if not titulo.strip():
                    st.error("Debe ingresar un título.")
                else:
                    # SUPABASE: Insertar actividad
                    nueva_actividad = {
                        "id": str(uuid.uuid4()),
                        "fecha": fecha.isoformat(),
                        "titulo": titulo.strip(),
                        "descripcion": descripcion.strip(),
                        "audiencia": audiencia,
                        "estado": estado,
                        "activo": True,
                        "ciclo_lectivo": CICLO_LECTIVO,
                        "creado_en": datetime.now(TZ_SV).isoformat(),
                    }
                    db.table("agenda").insert(nueva_actividad).execute()

                    st.success("✅ Actividad agregada.")
                    st.rerun()

        st.divider()
        st.markdown("### 📋 Actividades registradas")

        actividades = []
        try:
            # SUPABASE: Obtener todas las actividades
            res_agenda = db.table("agenda").select("*").execute()
            if res_agenda.data:
                actividades = res_agenda.data
        except APIError as error:
            st.error(f"No fue posible cargar la agenda: {error}")

        actividades.sort(key=lambda x: x.get("fecha", ""), reverse=True)

        if not actividades:
            st.info("No hay actividades registradas.")

        for actividad in actividades:
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 1])

                with c1:
                    st.write(
                        f"**{actividad.get('fecha', '-')} · {actividad.get('titulo', 'Actividad')}**"
                    )
                    st.caption(
                        f"{actividad.get('audiencia', 'Todos')} · {actividad.get('estado', 'Programado')}"
                    )
                    descripcion = actividad.get("descripcion", "")
                    if descripcion:
                        st.write(descripcion)

                with c2:
                    activo = actividad.get("activo", True)
                    texto = "Ocultar" if activo else "Publicar"

                    if st.button(texto, key=f"toggle_agenda_{actividad['id']}"):
                        # SUPABASE: Actualizar estado activo
                        db.table("agenda").update({"activo": not activo}).eq(
                            "id", actividad["id"]
                        ).execute()
                        st.rerun()

                with c3:
                    if st.button("🗑️ Eliminar", key=f"del_agenda_{actividad['id']}"):
                        # SUPABASE: Eliminar actividad
                        db.table("agenda").delete().eq("id", actividad["id"]).execute()
                        st.rerun()
