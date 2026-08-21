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

        </style>
        """,
        unsafe_allow_html=True
    )