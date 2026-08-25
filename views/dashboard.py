from datetime import datetime

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


def _cargar_configuracion(db):
    config = dict(DEFAULT_DASHBOARD)

    try:
        doc = (
            db.collection("configuracion")
            .document("dashboard")
            .get()
        )

        if doc.exists:
            data = doc.to_dict() or {}
            config.update(data)

    except Exception:
        pass

    return config


def _cargar_agenda(db, audiencia):
    """
    Devuelve actividades activas ordenadas por fecha.
    audiencia: 'Administración' o 'Docentes'
    """
    actividades = []

    try:
        docs = db.collection("agenda").stream()

        for doc in docs:
            data = doc.to_dict() or {}

            if not data.get("activo", True):
                continue

            audiencia_item = data.get("audiencia", "Todos")

            if audiencia_item not in ["Todos", audiencia]:
                continue

            fecha = str(data.get("fecha", "")).strip()

            actividades.append(
                {
                    "id": doc.id,
                    "fecha": fecha,
                    "titulo": data.get("titulo", "Actividad"),
                    "descripcion": data.get("descripcion", ""),
                    "estado": data.get("estado", "Programado"),
                }
            )

    except Exception:
        pass

    actividades.sort(
        key=lambda x: x.get("fecha", "9999-99-99")
    )

    return actividades[:8]


def _mostrar_aviso(config):
    if not config.get("aviso_activo", False):
        return

    st.markdown("### 📢 Aviso institucional")

    titulo = config.get(
        "aviso_titulo",
        "Aviso institucional"
    )

    mensaje = config.get(
        "aviso_mensaje",
        ""
    )

    st.info(
        f"**{titulo}**\n\n{mensaje}"
    )


def _mostrar_agenda(actividades):
    st.markdown("### 📅 Próximas actividades")

    if not actividades:
        st.info(
            "No hay actividades programadas."
        )
        return

    for actividad in actividades:
        with st.container(border=True):
            c1, c2 = st.columns([1, 4])

            with c1:
                st.write(
                    f"**{actividad.get('fecha', '-')}**"
                )

            with c2:
                st.write(
                    f"**{actividad.get('titulo', 'Actividad')}**"
                )

                descripcion = actividad.get(
                    "descripcion",
                    ""
                )

                if descripcion:
                    st.caption(descripcion)

                st.caption(
                    f"Estado: {actividad.get('estado', 'Programado')}"
                )


def mostrar_dashboard_admin(
    db,
    nombre_usuario,
):
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

    try:
        alumnos = (
            db.collection("alumnos")
            .where("estado", "==", "Activo")
            .stream()
        )

        for doc in alumnos:
            data = doc.to_dict()

            ciclo = _normalizar_ciclo(
                data.get("ciclo_lectivo")
            )

            if ciclo == CICLO_LECTIVO:
                total_alumnos += 1

    except Exception:
        total_alumnos = 0

    try:
        docentes = (
            db.collection("maestros_perfil")
            .where("activo", "==", True)
            .stream()
        )

        total_docentes = sum(
            1
            for _ in docentes
        )

    except Exception:
        total_docentes = 0

    hoy = datetime.now(TZ_SV)
    inicio_mes = hoy.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    try:
        movimientos = (
            db.collection("finanzas")
            .stream()
        )

        for doc in movimientos:
            data = doc.to_dict()
            fecha = data.get("fecha")

            if not fecha:
                continue

            try:
                fecha_sv = fecha.astimezone(TZ_SV)
            except Exception:
                continue

            if fecha_sv < inicio_mes:
                continue

            monto = float(
                data.get("monto", 0)
                or 0
            )

            if data.get("tipo") == "ingreso":
                ingresos_mes += monto
            elif data.get("tipo") == "egreso":
                egresos_mes += monto

    except Exception:
        pass

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "👨‍🎓 Alumnos activos",
        total_alumnos,
    )

    k2.metric(
        "👩‍🏫 Docentes activos",
        total_docentes,
    )

    k3.metric(
        "📅 Ciclo lectivo",
        CICLO_LECTIVO,
    )

    k4.metric(
        "🟢 Estado",
        config.get(
            "estado_sistema",
            "Operativo",
        ),
    )

    st.divider()

    _mostrar_aviso(config)

    c1, c2 = st.columns(2)

    with c1:
        actividades = _cargar_agenda(
            db,
            "Administración",
        )

        _mostrar_agenda(
            actividades
        )

    with c2:
        st.markdown(
            "### 💰 Resumen financiero del mes"
        )

        st.metric(
            "Ingresos",
            f"${ingresos_mes:.2f}",
        )

        st.metric(
            "Egresos",
            f"${egresos_mes:.2f}",
        )

        st.metric(
            "Balance",
            f"${ingresos_mes - egresos_mes:.2f}",
        )


def mostrar_dashboard_docente(
    db,
    nombre_usuario,
    limpiar_nombre,
):
    config = _cargar_configuracion(db)

    nombre_limpio = limpiar_nombre(
        nombre_usuario
    )

    perfil = None

    try:
        docs = (
            db.collection("maestros_perfil")
            .where(
                "nombre",
                "==",
                nombre_usuario,
            )
            .stream()
        )

        for doc in docs:
            perfil = doc.to_dict()
            break

        if not perfil and nombre_limpio != nombre_usuario:
            docs = (
                db.collection("maestros_perfil")
                .where(
                    "nombre",
                    "==",
                    nombre_limpio,
                )
                .stream()
            )

            for doc in docs:
                perfil = doc.to_dict()
                break

    except Exception:
        perfil = None

    c_foto, c_info = st.columns(
        [1, 4]
    )

    with c_foto:
        if perfil and perfil.get("foto_url"):
            st.image(
                perfil["foto_url"],
                width=150,
            )
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
        st.markdown(
            f"## Bienvenido, {nombre_limpio}"
        )

        st.caption(
            f"{config.get('titulo_docente', 'Panel Docente')} · "
            f"{COLEGIO_NOMBRE} · Ciclo {CICLO_LECTIVO}"
        )

        if perfil:
            telefono = perfil.get(
                "telefono",
                ""
            )

            email = perfil.get(
                "email",
                ""
            )

            if telefono or email:
                st.write(
                    f"📞 {telefono or '-'} "
                    f"· 📧 {email or '-'}"
                )

    cargas_actuales = []

    try:
        cargas = (
            db.collection("carga_academica")
            .where(
                "nombre_docente",
                "==",
                nombre_usuario,
            )
            .stream()
        )

        for doc in cargas:
            data = doc.to_dict()

            ciclo = _normalizar_ciclo(
                data.get(
                    "ciclo_lectivo",
                    2026,
                )
            )

            if ciclo != CICLO_LECTIVO:
                continue

            cargas_actuales.append(data)

    except Exception:
        pass

    grados = {
        c.get("grado")
        for c in cargas_actuales
        if c.get("grado")
    }

    materias = set()

    for carga in cargas_actuales:
        for materia in carga.get(
            "materias",
            [],
        ):
            materias.add(materia)

    es_guia = any(
        carga.get("es_guia")
        for carga in cargas_actuales
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "📚 Grados asignados",
        len(grados),
    )

    k2.metric(
        "📖 Materias",
        len(materias),
    )

    k3.metric(
        "📅 Ciclo",
        CICLO_LECTIVO,
    )

    k4.metric(
        "🌟 Maestro guía",
        "Sí" if es_guia else "No",
    )

    st.divider()

    _mostrar_aviso(config)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            "### 📚 Mis cargas"
        )

        if not cargas_actuales:
            st.info(
                "No tiene cargas asignadas "
                "para el ciclo actual."
            )
        else:
            for carga in cargas_actuales:
                with st.container(border=True):
                    st.write(
                        f"**{carga.get('grado', 'Sin grado')}**"
                    )

                    materias_carga = carga.get(
                        "materias",
                        [],
                    )

                    if materias_carga:
                        st.caption(
                            ", ".join(
                                materias_carga
                            )
                        )

                    if carga.get("es_guia"):
                        st.success(
                            "🌟 Maestro guía"
                        )

    with c2:
        actividades = _cargar_agenda(
            db,
            "Docentes",
        )

        _mostrar_agenda(
            actividades
        )