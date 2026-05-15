import streamlit as st

from afribooks_btw.engine.session_service import (
    get_afribooks_language,
    init_afribooks_session,
)
from afribooks_btw.ui.company_profile_ui import render_company_profile_ui
from afribooks_btw.ui.dashboard_ui import render_dashboard_ui
from afribooks_btw.ui.hero_ui import render_global_hero
from afribooks_btw.ui.invoice_history_ui import render_invoice_history_ui
from afribooks_btw.ui.fiscal_assistant_ui import render_fiscal_assistant_ui
from afribooks_btw.ui.zzp_invoice_ui import render_zzp_invoice_ui


TEXTS = {
    "nl": {
        "app_title": "AfriBooks BTW",
        "dashboard_tab": "Smart Business OS",
        "profile_tab": "Bedrijfsprofiel",
        "invoice_tab": "Slimme factuurmaker",
        "history_tab": "Factuurgeschiedenis",
        "assistant_tab": "Financial Companion AI",
        "sidebar_companion": "Financial Companion AI",
        "sidebar_language": "Taal",
        "sidebar_plan": "Plan",
        "sidebar_mode": "Modus",
        "sidebar_plan_value": "PREMIUM_PLUS klaar",
        "sidebar_mode_value": "Smart Business OS",
        "sidebar_premium_msg": "Zet uw Financial Companion AI-ervaring voort met PREMIUM PLUS.",
    },
    "fr": {
        "app_title": "AfriBooks BTW",
        "dashboard_tab": "Smart Business OS",
        "profile_tab": "Profil entreprise",
        "invoice_tab": "Createur intelligent de facture",
        "history_tab": "Historique des factures",
        "assistant_tab": "Financial Companion AI",
        "sidebar_companion": "Financial Companion AI",
        "sidebar_language": "Langue",
        "sidebar_plan": "Plan",
        "sidebar_mode": "Mode",
        "sidebar_plan_value": "PREMIUM_PLUS pret",
        "sidebar_mode_value": "Smart Business OS",
        "sidebar_premium_msg": "Continuez votre experience Financial Companion AI avec PREMIUM PLUS.",
    },
    "en": {
        "app_title": "AfriBooks BTW",
        "dashboard_tab": "Smart Business OS",
        "profile_tab": "Company Profile",
        "invoice_tab": "Smart Invoice Creator",
        "history_tab": "Invoice History",
        "assistant_tab": "Financial Companion AI",
        "sidebar_companion": "Financial Companion AI",
        "sidebar_language": "Language",
        "sidebar_plan": "Plan",
        "sidebar_mode": "Mode",
        "sidebar_plan_value": "PREMIUM_PLUS ready",
        "sidebar_mode_value": "Smart Business OS",
        "sidebar_premium_msg": "Continue your Financial Companion AI experience with PREMIUM PLUS.",
    },
}

def render_global_sidebar(labels: dict, lang: str) -> None:
    with st.sidebar:
        st.markdown("## AfriBooks BTW")
        st.caption(labels["sidebar_companion"])

        st.markdown("---")

        st.markdown(f"**{labels['sidebar_language']}**: `{lang.upper()}`")
        st.markdown(f"**{labels['sidebar_plan']}**: `{labels['sidebar_plan_value']}`")
        st.markdown(f"**{labels['sidebar_mode']}**: `{labels['sidebar_mode_value']}`")

        st.markdown("---")

        st.info(labels["sidebar_premium_msg"])

def main() -> None:
    st.set_page_config(
        page_title="AfriBooks BTW",
        page_icon="AB",
        layout="wide",
    )

    init_afribooks_session()

    lang = get_afribooks_language()
    labels = TEXTS.get(lang, TEXTS["nl"])

    render_global_sidebar(labels, lang)

    st.markdown(f"# {labels['app_title']}")
    render_global_hero()

    tab_dashboard, tab_profile, tab_invoice, tab_history, tab_assistant = st.tabs(
        [
            labels["dashboard_tab"],
            labels["profile_tab"],
            labels["invoice_tab"],
            labels["history_tab"],
            labels["assistant_tab"],
        ]
    )

    with tab_dashboard:
        render_dashboard_ui()

    with tab_profile:
        render_company_profile_ui()

    with tab_invoice:
        render_zzp_invoice_ui()

    with tab_history:
        render_invoice_history_ui()

    with tab_assistant:
        render_fiscal_assistant_ui()


if __name__ == "__main__":
    main()














