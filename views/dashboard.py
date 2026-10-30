from datetime import date, datetime

import streamlit as st

from config import CICLO_LECTIVO, COLEGIO_NOMBRE, TZ_SV

DEFAULT_DASHBOARD = {
    "titulo_admin": "Panel Administrativo",
    "subtitulo_admin": "Gestión institucional",
    "titulo_docente": "Panel Docente",
    "subtitulo_docente": "Gestión académica",
    "aviso_titulo": "Aviso institucional",
    "aviso_mensaje": "Sin avisos institucionales pendientes.",
    "aviso_activo": False,
    "estado_sistema": "Operativo",
}


def _normalizar_ciclo(valor, predeterminado=CICLO_LECTIVO):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return predeterminado


def _parsear_fecha(fecha):
    """
    Convierte una fecha (string ISO o datetime) a objeto date.
    Maneja tanto fechas de Supabase (string) como de Firebase (datetime).
    """
    if fecha is None:
        return None
    if isinstance(fecha, datetime):
        return fecha.astimezone(TZ_SV).date()
    if isinstance(fecha, date):
        return fecha
    if isinstance(fecha, str):
        try:
            return datetime.fromisoformat(fecha).astimezone(TZ_SV).date()
        except Exception:
            pass
        try:
            return datetime.strptime(fecha, "%Y-%m-%d").date()
        except Exception:
            pass
    return None


def _cargar_configuracion(db):
    """
    Carga la configuración del dashboard desde Supabase.
    db: cliente de Supabase
    """
    config = dict(DEFAULT_DASHBOARD)
    try:
        response = db.table("configuracion").select("*").eq("id", "dashboard").execute()
        if response.data and len(response.data) > 0:
            data = response.data[0]
            if "aviso_activo" in data:
                data["aviso_activo"] = bool(data["aviso_activo"])
            config.update(data)
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar la configuración: {e}")
    return config


def _cargar_agenda(db, audiencia):
    """
    Devuelve actividades activas ordenadas por fecha.
    audiencia: 'Administración' o 'Docentes'
    """
    actividades = []
    try:
        response = db.table("agenda").select("*").eq("activo", True).execute()
        if response.data:
            for data in response.data:
                audiencia_item = data.get("audiencia", "Todos")
                if audiencia_item not in ["Todos", audiencia]:
                    continue
                fecha = str(data.get("fecha", "")).strip()
                actividades.append(
                    {
                        "id": data.get("id", ""),
                        "fecha": fecha,
                        "titulo": data.get("titulo", "Actividad"),
                        "descripcion": data.get("descripcion", ""),
                        "estado": data.get("estado", "Programado"),
                    }
                )
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar la agenda: {e}")

    actividades.sort(key=lambda x: x.get("fecha", "9999-99-99"))
    return actividades[:8]


def _mostrar_aviso(config):
    if not config.get("aviso_activo", False):
        return
    st.markdown("### 📢 Aviso institucional")
    titulo = config.get("aviso_titulo", "Aviso institucional")
    mensaje = config.get("aviso_mensaje", "")
    st.info(f"**{titulo}**\n\n{mensaje}")


def _mostrar_agenda(actividades):
    st.markdown("### 📅 Próximas actividades")
    if not actividades:
        st.info("No hay actividades programadas.")
        return
    for actividad in actividades:
        with st.container(border=True):
            c1, c2 = st.columns([1, 4])
            with c1:
                st.write(f"**{actividad.get('fecha', '-')}**")
            with c2:
                st.write(f"**{actividad.get('titulo', 'Actividad')}**")
                descripcion = actividad.get("descripcion", "")
                if descripcion:
                    st.caption(descripcion)
                st.caption(f"Estado: {actividad.get('estado', 'Programado')}")


def mostrar_dashboard_admin(db, nombre_usuario):
    """
    Dashboard para administradores.
    db: cliente de Supabase
    """
    config = _cargar_configuracion(db)

    st.markdown(
        f"""
        <div class="dashboard-header">
            <div class="dashboard-eyebrow">
                {config.get("titulo_admin", "Panel Administrativo").upper()}
            </div>
            <div class="dashboard-title">
                Bienvenido, {nombre_usuario}
            </div>
            <div class="dashboard-subtitle">
                {COLEGIO_NOMBRE} · Ciclo Lectivo {CICLO_LECTIVO}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_alumnos = 0
    total_docentes = 0
    ingresos_mes = 0.0
    egresos_mes = 0.0

    # --- Contar alumnos activos del ciclo actual ---
    try:
        response = (
            db.table("alumnos")
            .select("nie")
            .eq("estado", "Activo")
            .eq("ciclo_lectivo", CICLO_LECTIVO)
            .execute()
        )
        total_alumnos = len(response.data) if response.data else 0
    except Exception as e:
        st.warning(f"⚠️ No se pudo contar alumnos: {e}")
        total_alumnos = 0

    # --- Contar docentes activos ---
    try:
        response = db.table("maestros_perfil").select("id").execute()
        total_docentes = 0
        if response.data:
            for d in response.data:
                if d.get("activo", True):
                    total_docentes += 1
    except Exception as e:
        st.warning(f"⚠️ No se pudo contar docentes: {e}")
        total_docentes = 0

    # --- Finanzas del mes actual ---
    hoy = datetime.now(TZ_SV)
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_str = inicio_mes.strftime("%Y-%m-%d")

    try:
        response = (
            db.table("finanzas").select("*").gte("fecha", inicio_mes_str).execute()
        )
        if response.data:
            for data in response.data:
                monto = float(data.get("monto", 0) or 0)
                if data.get("tipo") == "ingreso":
                    ingresos_mes += monto
                elif data.get("tipo") == "egreso":
                    egresos_mes += monto
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar finanzas: {e}")

    # --- Métricas ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👨‍🎓 Alumnos activos", total_alumnos)
    k2.metric("‍🏫 Docentes activos", total_docentes)
    k3.metric("📅 Ciclo lectivo", CICLO_LECTIVO)
    k4.metric("🟢 Estado", config.get("estado_sistema", "Operativo"))

    st.divider()

    _mostrar_aviso(config)

    c1, c2 = st.columns(2)
    with c1:
        actividades = _cargar_agenda(db, "Administración")
        _mostrar_agenda(actividades)

    with c2:
        st.markdown("### 💰 Resumen financiero del mes")
        st.metric("Ingresos", f"${ingresos_mes:.2f}")
        st.metric("Egresos", f"${egresos_mes:.2f}")
        st.metric("Balance", f"${ingresos_mes - egresos_mes:.2f}")


def mostrar_dashboard_docente(db, nombre_usuario, limpiar_nombre):
    """
    Dashboard para docentes.
    db: cliente de Supabase
    """
    config = _cargar_configuracion(db)
    nombre_limpio = limpiar_nombre(nombre_usuario)

    # --- Buscar perfil del docente ---
    perfil = None
    try:
        response = (
            db.table("maestros_perfil")
            .select("*")
            .eq("nombre", nombre_usuario)
            .execute()
        )
        if response.data and len(response.data) > 0:
            perfil = response.data[0]

        if not perfil and nombre_limpio != nombre_usuario:
            response = (
                db.table("maestros_perfil")
                .select("*")
                .eq("nombre", nombre_limpio)
                .execute()
            )
            if response.data and len(response.data) > 0:
                perfil = response.data[0]
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar el perfil: {e}")

    # --- Header con foto ---
    c_foto, c_info = st.columns([1, 4])
    with c_foto:
        if perfil and perfil.get("foto_url"):
            st.image(perfil["foto_url"], width=150)
        else:
            st.markdown(
                """
                <div style="
                    width:140px;
                    height:140px;
                    border-radius:50%;
                    background:#eef1f6;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:58px;
                    margin:auto;
                ">
                    👤
                </div>
                """,
                unsafe_allow_html=True,
            )

    with c_info:
        st.markdown(f"## Bienvenido, {nombre_limpio}")
        st.caption(
            f"{config.get('titulo_docente', 'Panel Docente')} · "
            f"{COLEGIO_NOMBRE} · Ciclo {CICLO_LECTIVO}"
        )
        if perfil:
            telefono = perfil.get("telefono", "")
            email = perfil.get("email", "")
            if telefono or email:
                st.write(f"📞 {telefono or '-'} ·  {email or '-'}")

    # --- Cargas académicas del docente ---
    cargas_actuales = []
    try:
        response = (
            db.table("carga_academica")
            .select("*")
            .eq("nombre_docente", nombre_usuario)
            .eq("ciclo_lectivo", CICLO_LECTIVO)
            .execute()
        )
        if response.data:
            cargas_actuales = response.data

        if not cargas_actuales and nombre_limpio != nombre_usuario:
            response = (
                db.table("carga_academica")
                .select("*")
                .eq("nombre_docente", nombre_limpio)
                .eq("ciclo_lectivo", CICLO_LECTIVO)
                .execute()
            )
            if response.data:
                cargas_actuales = response.data
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar las cargas académicas: {e}")

    # --- Procesar cargas ---
    grados = {c.get("grado") for c in cargas_actuales if c.get("grado")}
    materias = set()
    for carga in cargas_actuales:
        materias_carga = carga.get("materias", [])
        if isinstance(materias_carga, list):
            for materia in materias_carga:
                materias.add(materia)
        elif isinstance(materias_carga, str):
            try:
                import json

                materias_lista = json.loads(materias_carga)
                for materia in materias_lista:
                    materias.add(materia)
            except Exception:
                materias.add(materias_carga)

    es_guia = any(carga.get("es_guia") for carga in cargas_actuales)

    # --- Métricas ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(" Grados asignados", len(grados))
    k2.metric("📖 Materias", len(materias))
    k3.metric(" Ciclo", CICLO_LECTIVO)
    k4.metric("🌟 Maestro guía", "Sí" if es_guia else "No")

    st.divider()

    _mostrar_aviso(config)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📚 Mis cargas")
        if not cargas_actuales:
            st.info("No tiene cargas asignadas para el ciclo actual.")
        else:
            for carga in cargas_actuales:
                with st.container(border=True):
                    st.write(f"**{carga.get('grado', 'Sin grado')}**")
                    materias_carga = carga.get("materias", [])
                    if isinstance(materias_carga, list):
                        if materias_carga:
                            st.caption(", ".join(materias_carga))
                    elif isinstance(materias_carga, str):
                        st.caption(materias_carga)
                    if carga.get("es_guia"):
                        st.success(" Maestro guía")

    with c2:
        actividades = _cargar_agenda(db, "Docentes")
        _mostrar_agenda(actividades)
