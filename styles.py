import streamlit as st


def aplicar_estilos():
    """
    Aplica la identidad visual general de EduManager.
    """

    st.markdown(
        """
        <style>

        /* ========================================
           CONFIGURACIÓN GENERAL
        ======================================== */

        .stApp {
            background-color: #f5f7fb;
        }

        html, body, [class*="css"] {
            font-family: "Segoe UI", Arial, sans-serif;
        }


        /* ========================================
           CONTENIDO PRINCIPAL
        ======================================== */

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }


        /* ========================================
           TÍTULOS
        ======================================== */

        h1 {
            color: #16366f;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        h2, h3 {
            color: #243b64;
        }


        /* ========================================
           SIDEBAR
        ======================================== */

        section[data-testid="stSidebar"] {
            background-color: #102a56;
        }

        section[data-testid="stSidebar"] * {
            color: #ffffff;
        }

        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.15);
        }


        /* ========================================
           BOTONES
        ======================================== */

        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 8px;
            font-weight: 600;
            border: none;
            transition: 0.2s ease;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            transform: translateY(-1px);
        }


        /* ========================================
           INPUTS
        ======================================== */

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea {
            border-radius: 8px !important;
        }


        /* ========================================
           CONTENEDORES
        ======================================== */

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px;
        }


        /* ========================================
           MÉTRICAS
        ======================================== */

        div[data-testid="stMetric"] {
            background-color: white;
            padding: 18px;
            border-radius: 12px;
            border: 1px solid #e5e9f2;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        div[data-testid="stMetricLabel"] {
            font-weight: 600;
            color: #596b88;
        }

        div[data-testid="stMetricValue"] {
            color: #16366f;
            font-weight: 700;
        }


        /* ========================================
           TABLAS
        ======================================== */

        div[data-testid="stDataFrame"] {
            background-color: white;
            border-radius: 10px;
        }


        /* ========================================
           ALERTAS
        ======================================== */

        div[data-testid="stAlert"] {
            border-radius: 10px;
        }


        /* ========================================
           OCULTAR ELEMENTOS VISUALES DE STREAMLIT
        ======================================== */

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        /* ========================================
            CABECERA DEL DASHBOARD
        ======================================== */

    .dashboard-header {
        background: white;
        padding: 24px 28px;
        border-radius: 14px;
        border: 1px solid #e5e9f2;
        margin-bottom: 22px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }

    .dashboard-eyebrow {
        font-size: 13px;
        color: #718096;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .dashboard-title {
        font-size: 28px;
        color: #16366f;
        font-weight: 700;
        margin-top: 4px;
    }

    .dashboard-subtitle {
        color: #718096;
        margin-top: 5px;
        font-size: 15px;
    }

    /* ========================================
   SIDEBAR PROFESIONAL
======================================== */

.menu-section-title {
    font-size: 11px;
    font-weight: 700;
    color: rgba(255,255,255,0.55);
    letter-spacing: 1px;
    margin-top: 18px;
    margin-bottom: 6px;
}

/* ========================================
   SIDEBAR - MENÚ COMPACTO Y ALINEADO
======================================== */

/* Títulos de categoría */
.menu-section-title {
    font-size: 10px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.55);
    letter-spacing: 1.2px;

    margin-top: 22px;
    margin-bottom: 9px;

    padding-left: 2px;
}

/* Contenedor de botones */
section[data-testid="stSidebar"] .stButton {
    margin-bottom: 2px;
}

/* Botones inactivos */
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: transparent !important;
    color: rgba(255, 255, 255, 0.92) !important;

    border: none !important;
    border-radius: 7px !important;

    min-height: 34px !important;
    padding: 6px 10px !important;

    justify-content: flex-start !important;
    text-align: left !important;

    font-size: 14px !important;
    font-weight: 500 !important;

    width: 100% !important;
}

/* Texto interno del botón */
section[data-testid="stSidebar"] .stButton > button p {
    width: 100% !important;
    text-align: left !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Hover */
section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.08) !important;
}

/* Botón activo */
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(255, 255, 255, 0.12) !important;
    color: #ffffff !important;

    border: none !important;
    border-left: 3px solid #ff5252 !important;
    border-radius: 7px !important;

    min-height: 34px !important;
    padding: 6px 10px !important;

    justify-content: flex-start !important;
    text-align: left !important;

    font-size: 14px !important;
    font-weight: 600 !important;

    width: 100% !important;
}

/* Hover del activo */
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: rgba(255, 255, 255, 0.18) !important;
}

/* Separación entre grupos */
section[data-testid="stSidebar"] .menu-section-title + div {
    margin-top: 2px;
}

/* ========================================
   FORZAR ALINEACIÓN IZQUIERDA REAL
======================================== */

/* Contenido interno de todos los botones del sidebar */
section[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start !important;
    text-align: left !important;
}

/* Contenedor que Streamlit crea dentro del botón */
section[data-testid="stSidebar"] .stButton > button > div {
    width: 100% !important;
    justify-content: flex-start !important;
    text-align: left !important;
}

/* Contenedor Markdown interno */
section[data-testid="stSidebar"]
.stButton > button
div[data-testid="stMarkdownContainer"] {
    width: 100% !important;
    text-align: left !important;
}

/* Párrafo del texto */
section[data-testid="stSidebar"]
.stButton > button
div[data-testid="stMarkdownContainer"] p {
    width: 100% !important;
    text-align: left !important;
    margin: 0 !important;
}

        </style>
        """,
        unsafe_allow_html=True
    )