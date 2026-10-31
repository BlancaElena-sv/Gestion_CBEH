import streamlit as st


def aplicar_estilos():
    """
    Aplica estilos globales a toda la aplicación EduManager.
    IMPORTANTE: Excluye el sidebar para preservar su diseño.
    """

    st.markdown(
        """
    <style>
    /* ==========================================
       VARIABLES CSS (PALETA INSTITUCIONAL)
    ========================================== */
    :root {
        --azul-primario: #1e40af;
        --azul-oscuro: #1e3a8a;
        --azul-claro: #3b82f6;
        --azul-muy-claro: #dbeafe;
        --gris-fondo: #f8fafc;
        --gris-borde: #e2e8f0;
        --gris-texto: #334155;
        --gris-secundario: #64748b;
        --blanco: #ffffff;
        --rojo: #ef4444;
        --verde: #10b981;
        --amarillo: #f59e0b;
        --sombra-suave: 0 2px 8px rgba(0, 0, 0, 0.06);
        --sombra-media: 0 4px 16px rgba(0, 0, 0, 0.1);
        --sombra-fuerte: 0 8px 24px rgba(0, 0, 0, 0.15);
        --radio-borde: 12px;
        --transicion: all 0.25s ease;
    }

    /* ==========================================
       FONDO GENERAL DE LA APP (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] {
        background-color: var(--gris-fondo) !important;
    }

    /* ==========================================
       TIPOGRAFÍA GLOBAL (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4 {
        color: var(--azul-oscuro) !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }

    [data-testid="stMain"] h1 {
        font-size: 2.2rem !important;
        margin-bottom: 1rem !important;
    }

    [data-testid="stMain"] h2 {
        font-size: 1.8rem !important;
        margin-bottom: 0.8rem !important;
    }

    [data-testid="stMain"] h3 {
        font-size: 1.4rem !important;
        margin-bottom: 0.6rem !important;
    }

    [data-testid="stMain"] p,
    [data-testid="stMain"] label,
    [data-testid="stMain"] span {
        color: var(--gris-texto) !important;
    }

    /* ==========================================
       TARJETAS Y CONTENEDORES (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stContainer"] {
        background: var(--blanco) !important;
        border-radius: var(--radio-borde) !important;
        padding: 20px !important;
        box-shadow: var(--sombra-suave) !important;
        border: 1px solid var(--gris-borde) !important;
        transition: var(--transicion) !important;
    }

    [data-testid="stMain"] [data-testid="stContainer"]:hover {
        box-shadow: var(--sombra-media) !important;
    }

    /* Contenedores con borde (border=True) */
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--blanco) !important;
        border-radius: var(--radio-borde) !important;
        padding: 16px !important;
        box-shadow: var(--sombra-suave) !important;
        border: 1px solid var(--gris-borde) !important;
    }

    /* ==========================================
       MÉTRICAS DEL DASHBOARD (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stMetric"] {
        background: var(--blanco) !important;
        border-radius: var(--radio-borde) !important;
        padding: 20px !important;
        box-shadow: var(--sombra-suave) !important;
        border: 1px solid var(--gris-borde) !important;
        transition: var(--transicion) !important;
    }

    [data-testid="stMain"] [data-testid="stMetric"]:hover {
        box-shadow: var(--sombra-media) !important;
        transform: translateY(-2px) !important;
    }

    [data-testid="stMain"] [data-testid="stMetricLabel"] {
        color: var(--gris-secundario) !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }

    [data-testid="stMain"] [data-testid="stMetricValue"] {
        color: var(--azul-oscuro) !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
    }

    [data-testid="stMain"] [data-testid="stMetric"] {
        border-top: 4px solid var(--azul-primario) !important;
    }

    /* ==========================================
       TABLAS (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stDataFrame"] {
        border-radius: var(--radio-borde) !important;
        overflow: hidden !important;
        box-shadow: var(--sombra-suave) !important;
    }

    [data-testid="stMain"] [data-testid="stDataFrame"] table {
        border-collapse: separate !important;
        border-spacing: 0 !important;
    }

    [data-testid="stMain"] [data-testid="stDataFrame"] thead tr {
        background: var(--azul-primario) !important;
    }

    [data-testid="stMain"] [data-testid="stDataFrame"] thead th {
        color: var(--blanco) !important;
        font-weight: 700 !important;
        padding: 12px 16px !important;
        border: none !important;
    }

    [data-testid="stMain"] [data-testid="stDataFrame"] tbody tr {
        transition: var(--transicion) !important;
    }

    [data-testid="stMain"] [data-testid="stDataFrame"] tbody tr:hover {
        background: var(--azul-muy-claro) !important;
    }

    [data-testid="stMain"] [data-testid="stDataFrame"] tbody td {
        padding: 10px 16px !important;
        border-bottom: 1px solid var(--gris-borde) !important;
    }

    /* ==========================================
       FORMULARIOS E INPUTS (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stForm"] {
        background: var(--blanco) !important;
        border-radius: var(--radio-borde) !important;
        padding: 24px !important;
        box-shadow: var(--sombra-suave) !important;
        border: 1px solid var(--gris-borde) !important;
    }

    [data-testid="stMain"] input[type="text"],
    [data-testid="stMain"] input[type="password"],
    [data-testid="stMain"] input[type="number"],
    [data-testid="stMain"] input[type="email"],
    [data-testid="stMain"] textarea {
        border-radius: 8px !important;
        padding: 10px 14px !important;
        border: 1px solid var(--gris-borde) !important;
        transition: var(--transicion) !important;
        font-size: 14px !important;
    }

    [data-testid="stMain"] input:focus,
    [data-testid="stMain"] textarea:focus {
        border-color: var(--azul-claro) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        outline: none !important;
    }

    [data-testid="stMain"] label {
        font-weight: 600 !important;
        color: var(--gris-texto) !important;
        margin-bottom: 6px !important;
    }

    /* ==========================================
       BOTONES (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] button[kind="primary"] {
        background: linear-gradient(135deg, var(--azul-primario), var(--azul-claro)) !important;
        color: var(--blanco) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        transition: var(--transicion) !important;
        box-shadow: var(--sombra-suave) !important;
    }

    [data-testid="stMain"] button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--sombra-media) !important;
    }

    [data-testid="stMain"] button[kind="secondary"] {
        background: var(--blanco) !important;
        color: var(--gris-texto) !important;
        border: 1px solid var(--gris-borde) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        transition: var(--transicion) !important;
    }

    [data-testid="stMain"] button[kind="secondary"]:hover {
        background: var(--gris-fondo) !important;
        border-color: var(--gris-secundario) !important;
    }

    /* ==========================================
       ALERTAS Y MENSAJES (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stAlert"] {
        border-radius: var(--radio-borde) !important;
        padding: 16px 20px !important;
        border: none !important;
        box-shadow: var(--sombra-suave) !important;
    }

    [data-testid="stMain"] [data-testid="stAlert"] [data-testid="stAlertContent"] {
        font-size: 14px !important;
    }

    /* ==========================================
       SELECTBOX Y MULTISELECT (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stSelectbox"],
    [data-testid="stMain"] [data-testid="stMultiSelect"] {
        background: var(--blanco) !important;
        border-radius: 8px !important;
    }

    [data-testid="stMain"] [data-testid="stSelectbox"] div,
    [data-testid="stMain"] [data-testid="stMultiSelect"] div {
        border-radius: 8px !important;
        border: 1px solid var(--gris-borde) !important;
    }

    /* ==========================================
       EXPANDERS (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stExpander"] {
        border-radius: var(--radio-borde) !important;
        border: 1px solid var(--gris-borde) !important;
        background: var(--blanco) !important;
        box-shadow: var(--sombra-suave) !important;
    }

    [data-testid="stMain"] [data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: var(--azul-oscuro) !important;
    }

    /* ==========================================
       DIVIDERS (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] hr {
        border-color: var(--gris-borde) !important;
        margin: 24px 0 !important;
        opacity: 0.6;
    }

    /* ==========================================
       TABS (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stTabs"] button {
        border-radius: 8px 8px 0 0 !important;
        font-weight: 600 !important;
        transition: var(--transicion) !important;
    }

    [data-testid="stMain"] [data-testid="stTabs"] button[aria-selected="true"] {
        background: var(--azul-primario) !important;
        color: var(--blanco) !important;
    }

    /* ==========================================
       FILE UPLOADER (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] [data-testid="stFileUploader"] {
        border-radius: var(--radio-borde) !important;
        border: 2px dashed var(--gris-borde) !important;
        background: var(--gris-fondo) !important;
        padding: 20px !important;
        transition: var(--transicion) !important;
    }

    [data-testid="stMain"] [data-testid="stFileUploader"]:hover {
        border-color: var(--azul-claro) !important;
        background: var(--azul-muy-claro) !important;
    }

    /* ==========================================
       IMÁGENES (SOLO CONTENIDO PRINCIPAL)
    ========================================== */
    [data-testid="stMain"] img {
        border-radius: 8px !important;
    }

    /* ==========================================
       TEXTO BLANCO SOBRE FONDOS AZULES
       (botones primarios y etiquetas del multiselect).
       Las reglas de arriba pintan todos los p/span de gris;
       estas son más específicas y recuperan el blanco.
    ========================================== */
    [data-testid="stMain"] button[kind^="primary"],
    [data-testid="stMain"] button[kind^="primary"] *,
    [data-testid="stMain"] [data-testid^="stBaseButton-primary"],
    [data-testid="stMain"] [data-testid^="stBaseButton-primary"] * {
        color: var(--blanco) !important;
        -webkit-text-fill-color: var(--blanco) !important;
    }

    [data-testid="stMain"] [data-baseweb="tag"],
    [data-testid="stMain"] [data-baseweb="tag"] * {
        color: var(--blanco) !important;
        -webkit-text-fill-color: var(--blanco) !important;
    }

    /* ==========================================
       SCROLLBAR PERSONALIZADO
    ========================================== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--gris-fondo);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--gris-secundario);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--azul-claro);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
