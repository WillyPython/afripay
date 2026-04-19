from pathlib import Path

import streamlit as st

from config.settings import (
    APP_NAME,
    PARENT_COMPANY_NAME,
    COMPANY_EMAIL_SUPPORT,
    COMPANY_KVK,
    COMPANY_VAT_ID,
)


BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


def render_sidebar_branding():
    """
    Affiche le branding AfriPay dans la sidebar.
    """
    lang = st.session_state.get("language", "fr")

    tagline = (
        "Achat de produits et services internationaux simplifiés depuis l’Afrique"
        if lang == "fr"
        else "Simplified purchase of international products and services from Africa"
    )

    security_title = (
        "🔒 Plateforme sécurisée et fiable"
        if lang == "fr"
        else "🔒 Trusted & secure platform"
    )

    security_items = (
        [
            "Vérification téléphone (OTP)",
            "Commandes vérifiées",
            "Infrastructure protégée",
            "Connexion HTTPS sécurisée",
        ]
        if lang == "fr"
        else [
            "Secure OTP login",
            "Verified orders",
            "Protected infrastructure",
            "Secure HTTPS connection",
        ]
    )

    support_label = (
        f"Support : {COMPANY_EMAIL_SUPPORT}"
        if lang == "fr"
        else f"Support: {COMPANY_EMAIL_SUPPORT}"
    )

    kvk_label = (
        f"KVK : {COMPANY_KVK}"
        if lang == "fr"
        else f"KVK: {COMPANY_KVK}"
    )

    vat_label = (
        f"BTW : {COMPANY_VAT_ID}"
        if lang == "fr"
        else f"VAT: {COMPANY_VAT_ID}"
    )

    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #06122E 0%, #081735 100%) !important;
        }

        [data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, #06122E 0%, #081735 100%) !important;
        }

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

        .afripay-sidebar-powered {
            text-align: center;
            font-size: 11px;
            color: #94A3B8;
            margin-top: 4px;
            margin-bottom: 0;
            letter-spacing: 0.5px;
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

        .afripay-sidebar-support {
            text-align: center;
            font-size: 0.82rem;
            color: #CBD5E1;
            line-height: 1.6;
            margin-top: 0.85rem;
        }

        .afripay-sidebar-support b {
            color: #FFFFFF;
        }

        .afripay-sidebar-fiscal-line {
            margin-top: 0.2rem;
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
        st.sidebar.markdown(
            "<div class='afripay-sidebar-logo-wrap'>",
            unsafe_allow_html=True,
        )
        st.sidebar.image(str(LOGO_PATH), width=190)
        st.sidebar.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    st.sidebar.markdown(
        "<hr class='afripay-sidebar-divider'>",
        unsafe_allow_html=True,
    )

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
            ✨ {tagline}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        f"""
        <p class="afripay-sidebar-powered">
            Powered by <b style="color:#22C55E;">{PARENT_COMPANY_NAME}</b>
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        "<hr class='afripay-sidebar-divider'>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        f"""
        <div class="afripay-security-card">
            <div class="afripay-security-title">{security_title}</div>
            <ul class="afripay-security-list">
                {''.join([f'<li><span class="afripay-security-check">✔</span>{item}</li>' for item in security_items])}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        f"""
        <div class="afripay-sidebar-support">
            <div><b>{support_label}</b></div>
            <div class="afripay-sidebar-fiscal-line">{kvk_label}</div>
            <div class="afripay-sidebar-fiscal-line">{vat_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        "<hr class='afripay-sidebar-divider'>",
        unsafe_allow_html=True,
    )
    