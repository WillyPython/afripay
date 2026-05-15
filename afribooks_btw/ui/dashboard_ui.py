import streamlit as st

from afribooks_btw.engine.business_kpi_service import get_business_kpis
from afribooks_btw.engine.notification_engine import build_security_notifications
from afribooks_btw.engine.session_service import get_afribooks_language
from afribooks_btw.ui.result_widget_ui import render_result_widget_ui


TEXTS = {
    "nl": {
        "title": "AfriBooks Smart Business OS",
        "caption": "Een zachte cockpit voor BTW, facturen, kosten en bedrijfsresultaat.",
        "badge": "SMART BUSINESS OPERATING SYSTEM",
        "hero_title": "Beheer uw bedrijf met rust, overzicht en fiscale intelligentie.",
        "hero_text": "AfriBooks helpt u uw facturen, BTW, kosten, resultaat en zakelijke signalen duidelijk te begrijpen.",
        "reminders": "Slimme herinneringen",
        "empty": "Geen kritieke herinneringen op dit moment.",
        "status": "SaaS cockpit actief",
        "vat": "BTW-ready",
        "assistant": "Financial Companion AI",
    },
    "fr": {
        "title": "AfriBooks Smart Business OS",
        "caption": "Un cockpit doux pour la TVA, les factures, les charges et le resultat business.",
        "badge": "SMART BUSINESS OPERATING SYSTEM",
        "hero_title": "Pilotez votre entreprise avec calme, visibilite et intelligence fiscale.",
        "hero_text": "AfriBooks vous aide a comprendre clairement vos factures, votre TVA, vos charges, votre resultat et vos signaux business.",
        "reminders": "Rappels intelligents",
        "empty": "Aucun rappel critique pour le moment.",
        "status": "Cockpit SaaS actif",
        "vat": "TVA-ready",
        "assistant": "Financial Companion AI",
    },
    "en": {
        "title": "AfriBooks Smart Business OS",
        "caption": "A soft cockpit for VAT, invoices, expenses and business results.",
        "badge": "SMART BUSINESS OPERATING SYSTEM",
        "hero_title": "Run your business with clarity, calm and fiscal intelligence.",
        "hero_text": "AfriBooks helps you understand your invoices, VAT, expenses, result and business signals clearly.",
        "reminders": "Smart reminders",
        "empty": "No critical reminders for now.",
        "status": "SaaS cockpit active",
        "vat": "VAT-ready",
        "assistant": "Financial Companion AI",
    },
}


def render_dashboard_ui() -> None:
    lang = get_afribooks_language()
    labels = TEXTS.get(lang, TEXTS["nl"])

    st.markdown(f"## {labels['title']}")
    st.caption(labels["caption"])

    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.markdown(
            f"""
            <div style="
                border-radius:22px;
                padding:24px 26px;
                background:linear-gradient(135deg,#0f172a,#1e293b);
                color:#ffffff;
                box-shadow:0 12px 30px rgba(15,23,42,0.20);
                border:1px solid rgba(255,255,255,0.08);
                margin-bottom:18px;
            ">
                <div style="font-size:0.78rem; color:#F8D24A; font-weight:900; letter-spacing:0.08em;">
                    {labels["badge"]}
                </div>

                <h2 style="margin:10px 0 8px 0; color:#ffffff;">
                    {labels["hero_title"]}
                </h2>

                <p style="font-size:1rem; color:#e5e7eb; margin-bottom:16px; line-height:1.5;">
                    {labels["hero_text"]}
                </p>

                <div style="display:flex;flex-wrap:wrap;gap:8px;">
                    <span style="padding:7px 11px;border-radius:999px;background:#ecfdf5;color:#047857;font-weight:900;font-size:0.76rem;">
                        {labels["status"]}
                    </span>
                    <span style="padding:7px 11px;border-radius:999px;background:#eff6ff;color:#1d4ed8;font-weight:900;font-size:0.76rem;">
                        {labels["vat"]}
                    </span>
                    <span style="padding:7px 11px;border-radius:999px;background:#fef3c7;color:#92400e;font-weight:900;font-size:0.76rem;">
                        {labels["assistant"]}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(f"### {labels['reminders']}")

        notifications = build_security_notifications()

        if not notifications:
            st.info(labels["empty"])

        for notification in notifications:
            st.info(notification.message)

    business_kpis = get_business_kpis()

    with right_col:
        render_result_widget_ui(
            invoices_count=business_kpis["invoices_count"],
            gross=business_kpis["gross"],
            vat=business_kpis["vat"],
            other_charges=business_kpis["other_charges"],
            net=business_kpis["net"],
        )


