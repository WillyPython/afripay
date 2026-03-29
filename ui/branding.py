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
        <style>
        .afripay-sidebar-logo-wrap {
            display: flex;
            justify-content: center;
            margin-top: 0.25rem;
            margin-bottom: 0.75rem;
        }

        .afripay-sidebar-divider {
            border: none;
            border-top: 1px solid rgba(255,255,255,0.08);
            margin: 1rem 0;
        }

        .afripay-sidebar-app-name {
            text-align: center;
            margin: 0 0 0.35rem 0;
            color: #FFFFFF;
            font-size: 1.9rem;
            font-weight: 800;
            line-height: 1.2;
            letter-spacing: -0.4px;
        }

        .afripay-sidebar-tagline {
            text-align: center;
            font-size: 1rem;
            font-weight: 700;
            margin: 0;
            color: #F59E0B;
            line-height: 1.5;
            text-shadow: 0 0 10px rgba(245,158,11,0.25);
        }

        .afripay-security-card {
            background: linear-gradient(180deg, #0F1B3D 0%, #0B1633 100%);
            padding: 14px 14px 12px 14px;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.08);
            margin-top: 0.5rem;
            box-shadow: 0 8px 18px rgba(0,0,0,0.18);
        }

        .afripay-security-title {
            text-align: center;
            font-weight: 800;
            font-size: 1.1rem;
            color: #22C55E;
            margin: 0 0 0.85rem 0;
        }

        .afripay-security-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .afripay-security-list li {
            color: #E2E8F0;
            font-size: 0.98rem;
            line-height: 1.55;
            margin-bottom: 0.35rem;
        }

        .afripay-security-list li:last-child {
            margin-bottom: 0;
        }

        .afripay-security-check {
            color: #22C55E;
            font-weight: 700;
            margin-right: 0.45rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        "<div style='padding-top:0.25rem;'></div>",
        unsafe_allow_html=True,
    )

    if LOGO_PATH.exists():
        st.sidebar.markdown("<div class='afripay-sidebar-logo-wrap'>", unsafe_allow_html=True)
        st.sidebar.image(str(LOGO_PATH), width=190)
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    st.sidebar.markdown("<hr class='afripay-sidebar-divider'>", unsafe_allow_html=True)

    st.sidebar.markdown(
        f"""
        <div class="afripay-sidebar-app-name">
            {APP_NAME}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        f"""
        <div class="afripay-sidebar-tagline">
            ✨ {APP_TAGLINE}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
    """
    <p style="
        text-align:center;
        font-size:11px;
        color:#94a3b8;
        margin-top:4px;
        margin-bottom:0;
        letter-spacing:0.5px;
    ">
        Powered by <b style="color:#22c55e;">AfriDIGID</b>
    </p>
    """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<hr class='afripay-sidebar-divider'>", unsafe_allow_html=True)

    st.sidebar.markdown(
        """
        <div class="afripay-security-card">
            <div class="afripay-security-title">🔒 Plateforme sécurisée</div>
            <ul class="afripay-security-list">
                <li><span class="afripay-security-check">✔</span>Vérification téléphone (OTP)</li>
                <li><span class="afripay-security-check">✔</span>Paiements vérifiés</li>
                <li><span class="afripay-security-check">✔</span>Infrastructure protégée</li>
                <li><span class="afripay-security-check">✔</span>Connexion HTTPS sécurisée</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("<hr class='afripay-sidebar-divider'>", unsafe_allow_html=True)