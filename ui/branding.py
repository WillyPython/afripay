from pathlib import Path

import streamlit as st

from config.settings import APP_NAME, APP_TAGLINE


BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


def render_sidebar_branding():
    """
    Affiche le branding AfriPay dans la sidebar.
    """
    st.sidebar.markdown(
        """
        <div style="padding-top: 0.25rem;"></div>
        """,
        unsafe_allow_html=True,
    )

    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width=190)

    st.sidebar.markdown("---")

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