from pathlib import Path

import streamlit as st

from config.settings import APP_NAME, APP_TAGLINE


BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


def render_sidebar_branding():
    """
    Affiche le branding AfriPay dans la sidebar.
    """

    # Petit espace en haut
    st.sidebar.markdown(
        "<div style='padding-top:0.25rem;'></div>",
        unsafe_allow_html=True,
    )

    # Logo AfriPay
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width=190)

    st.sidebar.markdown("---")

    # Nom de l'application
    st.sidebar.markdown(
        f"""
        <h3 style="
            text-align:center;
            margin-bottom:6px;
            color:white;
            font-weight:700;
        ">
            {APP_NAME}
        </h3>
        """,
        unsafe_allow_html=True,
    )

    # Slogan
    st.sidebar.markdown(
        f"""
        <p style="
            text-align:center;
            font-size:13px;
            font-weight:700;
            margin-top:0;
            margin-bottom:0;
            color:#ff9900;
            text-shadow:0 0 10px rgba(255,153,0,0.9);
        ">
            ✨ {APP_TAGLINE}
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")

    # Badge sécurité AfriPay
    st.sidebar.markdown(
        """
        <div style="
            background-color:#0f172a;
            padding:10px;
            border-radius:8px;
            border:1px solid #1e293b;
            margin-top:10px;
        ">
        <p style="
            text-align:center;
            font-weight:700;
            color:#22c55e;
            margin-bottom:6px;
        ">
        🔒 Plateforme sécurisée
        </p>

        <p style="
            font-size:12px;
            color:#cbd5f5;
            margin:0;
            line-height:1.4;
        ">
        ✔ Vérification téléphone (OTP)<br>
        ✔ Paiements vérifiés<br>
        ✔ Infrastructure protégée<br>
        ✔ Connexion HTTPS sécurisée
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")