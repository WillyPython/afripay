import streamlit as st

from afribooks_btw.engine.business_kpi_service import get_business_kpis
from afribooks_btw.engine.fiscal_assistant_engine import (
    build_fiscal_assistant_response,
)
from afribooks_btw.engine.session_service import get_afribooks_language


TEXTS = {
    "nl": {
        "title": "Financial Companion AI",
        "subtitle": "Uw zachte fiscale en zakelijke assistent.",
        "alerts": "Fiscale signalen",
        "insights": "Business inzichten",
        "empty": "Geen kritisch signaal op dit moment.",
    },
    "fr": {
        "title": "Financial Companion AI",
        "subtitle": "Votre assistant fiscal et business anti-stress.",
        "alerts": "Signaux fiscaux",
        "insights": "Insights business",
        "empty": "Aucun signal critique pour le moment.",
    },
    "en": {
        "title": "Financial Companion AI",
        "subtitle": "Your calm fiscal and business assistant.",
        "alerts": "Fiscal signals",
        "insights": "Business insights",
        "empty": "No critical signal for now.",
    },
}


def render_fiscal_assistant_ui() -> None:
    lang = get_afribooks_language()
    labels = TEXTS.get(lang, TEXTS["nl"])

    kpis = get_business_kpis()

    assistant = build_fiscal_assistant_response(
        invoices_count=kpis["invoices_count"],
        gross=kpis["gross"],
        vat=kpis["vat"],
        other_charges=kpis["other_charges"],
        net=kpis["net"],
    )

    st.markdown(f"## {labels['title']}")
    st.caption(labels["subtitle"])

    col_alerts, col_insights = st.columns(2)

    with col_alerts:
        st.markdown(f"### {labels['alerts']}")

        if not assistant.fiscal_alerts:
            st.info(labels["empty"])

        for alert in assistant.fiscal_alerts:
            st.info(f"{alert.icon} **{alert.title}** — {alert.message}")

    with col_insights:
        st.markdown(f"### {labels['insights']}")

        if not assistant.business_insights:
            st.info(labels["empty"])

        for insight in assistant.business_insights:
            st.info(f"{insight.icon} **{insight.title}** — {insight.message}")
