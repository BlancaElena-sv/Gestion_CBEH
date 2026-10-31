import html
import json
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

MESES_CORTOS = [
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
]

# Colores del estado de cada actividad: (texto, fondo)
COLORES_ESTADO = {
    "programado": ("#1e40af", "#dbeafe"),
    "en curso": ("#b45309", "#fef3c7"),
    "completado": ("#047857", "#d1fae5"),
    "finalizado": ("#047857", "#d1fae5"),
    "cancelado": ("#b91c1c", "#fee2e2"),
}

VERDE = "#059669"
ROJO = "#dc2626"


# ==========================================
# UTILIDADES
# ==========================================
def _esc(valor):
    """Escapa texto que viene de la base de datos antes de ponerlo en HTML.
    Si alguien guarda '<script>' en un título, aquí se vuelve texto inofensivo."""
    return html.escape(str(valor if valor is not None else ""))


def _compactar(texto_html):
    """Quita sangrías y saltos de línea. Markdown interpreta 4 espacios al inicio
    como 'bloque de código', y esto evita ese problema."""
    return "".join(linea.strip() for linea in texto_html.splitlines())


def _normalizar_ciclo(valor, predeterminado=CICLO_LECTIVO):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return predeterminado


def _parsear_fecha(fecha):
    """
    Convierte una fecha (string ISO o datetime) a objeto date.
    Una fecha sola ('2026-10-30') se lee tal cual, sin convertir zona horaria:
    así no se corre un día en servidores que están en otra zona (como Streamlit Cloud).
    """
    if fecha is None:
        return None
    if isinstance(fecha, datetime):
        if fecha.tzinfo is None:
            return fecha.date()
        return fecha.astimezone(TZ_SV).date()
    if isinstance(fecha, date):
        return fecha
    if isinstance(fecha, str):
        texto = fecha.strip()
        try:
            return datetime.strptime(texto[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(texto)
            return dt.date() if dt.tzinfo is None else dt.astimezone(TZ_SV).date()
        except ValueError:
            pass
    return None


def _inyectar_estilos():
    """CSS propio del dashboard (tarjeta de bienvenida, agenda y finanzas)."""
    st.markdown(
        """
        <style>
        .dashboard-header {
            background: #FFFFFF;
            border: 1px solid #e2e8f0;
            border-left: 6px solid #F2B544;
            border-radius: 16px;
            padding: 26px 32px;
            margin-bottom: 22px;
            box-shadow: 0 2px 8px rgba(15, 35, 71, 0.06);
        }
        .dashboard-eyebrow {
            color: #64748b;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.6px;
            margin-bottom: 6px;
        }
        .dashboard-title {
            color: #1e3a8a;
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.2;
            letter-spacing: -0.5px;
        }
        .dashboard-subtitle {
            color: #64748b;
            font-size: 15px;
            margin-top: 6px;
        }
        .dashboard-contacto {
            color: #475569;
            font-size: 13px;
            margin-top: 10px;
        }

        .agenda-item {
            display: flex;
            gap: 16px;
            align-items: flex-start;
            background: #FFFFFF;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 1px 4px rgba(15, 35, 71, 0.05);
        }
        .agenda-fecha {
            min-width: 58px;
            text-align: center;
            background: #eaf0fb;
            border-radius: 10px;
            padding: 8px 6px;
        }
        .agenda-dia {
            color: #1e3a8a;
            font-size: 1.5rem;
            font-weight: 800;
            line-height: 1;
        }
        .agenda-mes {
            color: #2457A6;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 4px;
        }
        .agenda-titulo { color: #0f172a; font-weight: 700; font-size: 15px; }
        .agenda-desc { color: #64748b; font-size: 13px; margin-top: 3px; }
        .agenda-estado {
            display: inline-block;
            margin-top: 8px;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
        }

        .fin-card {
            background: #FFFFFF;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 1px 4px rgba(15, 35, 71, 0.05);
        }
        .fin-label { color: #64748b; font-size: 13px; font-weight: 600; }
        .fin-valor { font-size: 1.9rem; font-weight: 800; margin-top: 2px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# CARGA DE DATOS
# ==========================================
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


# ==========================================
# COMPONENTES VISUALES
# ==========================================
def _mostrar_aviso(config):
    if not config.get("aviso_activo", False):
        return
    st.markdown("### :material/campaign: Aviso institucional")
    titulo = config.get("aviso_titulo", "Aviso institucional")
    mensaje = config.get("aviso_mensaje", "")
    st.info(f"**{titulo}**\n\n{mensaje}")


def _mostrar_agenda(actividades):
    st.markdown("### :material/calendar_month: Próximas actividades")
    if not actividades:
        st.info("No hay actividades programadas.")
        return

    for actividad in actividades:
        fecha = _parsear_fecha(actividad.get("fecha"))
        if fecha:
            dia, mes = f"{fecha.day:02d}", MESES_CORTOS[fecha.month - 1]
        else:
            dia, mes = "–", ""

        estado = actividad.get("estado", "Programado")
        color_txt, color_fondo = COLORES_ESTADO.get(
            str(estado).strip().lower(), ("#475569", "#e2e8f0")
        )
        descripcion = actividad.get("descripcion", "")
        bloque_desc = (
            f'<div class="agenda-desc">{_esc(descripcion)}</div>' if descripcion else ""
        )

        st.markdown(
            _compactar(
                f"""
                <div class="agenda-item">
                    <div class="agenda-fecha">
                        <div class="agenda-dia">{dia}</div>
                        <div class="agenda-mes">{mes}</div>
                    </div>
                    <div>
                        <div class="agenda-titulo">{_esc(actividad.get("titulo", "Actividad"))}</div>
                        {bloque_desc}
                        <span class="agenda-estado"
                              style="color:{color_txt};background:{color_fondo};">
                            {_esc(estado)}
                        </span>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )


def _tarjeta_finanza(etiqueta, valor, color):
    """Tarjeta de dinero con borde y número del color indicado (verde / rojo / azul)."""
    st.markdown(
        _compactar(
            f"""
            <div class="fin-card" style="border-left:5px solid {color};">
                <div class="fin-label">{_esc(etiqueta)}</div>
                <div class="fin-valor" style="color:{color};">${valor:,.2f}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


# ==========================================
# DASHBOARD ADMINISTRADOR
# ==========================================
def mostrar_dashboard_admin(db, nombre_usuario):
    """
    Dashboard para administradores.
    db: cliente de Supabase
    """
    _inyectar_estilos()
    config = _cargar_configuracion(db)

    st.markdown(
        _compactar(
            f"""
            <div class="dashboard-header">
                <div class="dashboard-eyebrow">
                    {_esc(config.get("titulo_admin", "Panel Administrativo")).upper()}
                </div>
                <div class="dashboard-title">Bienvenido, {_esc(nombre_usuario)}</div>
                <div class="dashboard-subtitle">
                    {_esc(COLEGIO_NOMBRE)} · Ciclo Lectivo {CICLO_LECTIVO}
                </div>
            </div>
            """
        ),
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
    k1.metric("Alumnos activos", total_alumnos)
    k2.metric("Docentes activos", total_docentes)
    k3.metric("Ciclo lectivo", CICLO_LECTIVO)
    k4.metric("Estado", config.get("estado_sistema", "Operativo"))

    st.divider()

    _mostrar_aviso(config)

    c1, c2 = st.columns(2)
    with c1:
        actividades = _cargar_agenda(db, "Administración")
        _mostrar_agenda(actividades)

    with c2:
        st.markdown("### :material/payments: Resumen financiero del mes")
        balance = ingresos_mes - egresos_mes
        _tarjeta_finanza("Ingresos", ingresos_mes, VERDE)
        _tarjeta_finanza("Egresos", egresos_mes, ROJO)
        _tarjeta_finanza("Balance", balance, "#1e3a8a" if balance >= 0 else ROJO)


# ==========================================
# DASHBOARD DOCENTE
# ==========================================
def mostrar_dashboard_docente(db, nombre_usuario, limpiar_nombre):
    """
    Dashboard para docentes.
    db: cliente de Supabase
    """
    _inyectar_estilos()
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
                _compactar(
                    """
                    <div style="width:140px;height:140px;border-radius:50%;
                        background:#eef1f6;display:flex;align-items:center;
                        justify-content:center;font-size:58px;margin:auto;">👤</div>
                    """
                ),
                unsafe_allow_html=True,
            )

    with c_info:
        contacto = ""
        if perfil:
            telefono = perfil.get("telefono", "")
            email = perfil.get("email", "")
            if telefono or email:
                contacto = (
                    f'<div class="dashboard-contacto">'
                    f"{_esc(telefono or '-')} · {_esc(email or '-')}</div>"
                )
        st.markdown(
            _compactar(
                f"""
                <div class="dashboard-header" style="margin-bottom:0;">
                    <div class="dashboard-eyebrow">
                        {_esc(config.get("titulo_docente", "Panel Docente")).upper()}
                    </div>
                    <div class="dashboard-title">Bienvenido, {_esc(nombre_limpio)}</div>
                    <div class="dashboard-subtitle">
                        {_esc(COLEGIO_NOMBRE)} · Ciclo Lectivo {CICLO_LECTIVO}
                    </div>
                    {contacto}
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

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
                materias_lista = json.loads(materias_carga)
                for materia in materias_lista:
                    materias.add(materia)
            except Exception:
                materias.add(materias_carga)

    es_guia = any(carga.get("es_guia") for carga in cargas_actuales)

    st.write("")  # pequeño espacio bajo la tarjeta de bienvenida

    # --- Métricas ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Grados asignados", len(grados))
    k2.metric("Materias", len(materias))
    k3.metric("Ciclo", CICLO_LECTIVO)
    k4.metric("Maestro guía", "Sí" if es_guia else "No")

    st.divider()

    _mostrar_aviso(config)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### :material/library_books: Mis cargas")
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
                        st.success("Maestro guía")

    with c2:
        actividades = _cargar_agenda(db, "Docentes")
        _mostrar_agenda(actividades)
