import streamlit as st

from afribooks_btw.engine.fiscal_health_engine import calculate_fiscal_health_score
from afribooks_btw.engine.session_service import get_afribooks_language


TEXTS = {
    "nl": {
        "title": "Fiscale gezondheidsscore AfriBooks",
        "status": "Status",
        "fiscal": "Fiscaal",
        "financial": "Financieel",
        "economic": "Economisch",
        "invoices": "FACTUREN",
        "gross": "OMZET",
        "vat": "BTW",
        "charges": "ANDERE KOSTEN",
        "net": "NETTO RESULTAAT",
    },
    "fr": {
        "title": "Score de sante fiscale AfriBooks",
        "status": "Statut",
        "fiscal": "Fiscal",
        "financial": "Financier",
        "economic": "Economique",
        "invoices": "FACTURES",
        "gross": "CHIFFRE D'AFFAIRES",
        "vat": "TVA",
        "charges": "AUTRES CHARGES",
        "net": "RESULTAT NET",
    },
    "en": {
        "title": "AfriBooks Fiscal Health Score",
        "status": "Status",
        "fiscal": "Fiscal",
        "financial": "Financial",
        "economic": "Economic",
        "invoices": "INVOICES",
        "gross": "GROSS",
        "vat": "VAT",
        "charges": "OTHER CHARGES",
        "net": "NET RESULT",
    },
}

def render_result_widget_ui(
    invoices_count: int = 0,
    gross: float = 0.0,
    vat: float = 0.0,
    other_charges: float = 0.0,
    net: float = 0.0,
) -> None:
    lang = get_afribooks_language()
    labels = TEXTS.get(lang, TEXTS["nl"])

    score = calculate_fiscal_health_score(
        invoices_count=invoices_count,
        gross=gross,
        vat=vat,
        other_charges=other_charges,
        net=net,
    )

    chip = "padding:8px 10px;border-radius:12px;font-weight:900;font-size:0.78rem;"
    mini = "padding:6px 9px;border-radius:10px;font-weight:900;font-size:0.78rem;"
    net_display = f"{score.net:+.2f} EUR"

    html = f"""
<div style="border-radius:18px;padding:18px 22px;background:#F8D24A;margin:18px 0;">
  <div style="font-size:0.92rem;color:#374151;font-weight:800;">{labels["title"]}</div>
  <div style="font-size:2.2rem;font-weight:950;color:#111827;">{score.global_score}/100</div>

  <div style="margin-top:8px;">
    <span style="{mini}background:#dcfce7;color:#166534;">{labels["status"]}: {score.status}</span>
  </div>

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;">
    <span style="{mini}background:#dcfce7;color:#166534;">{labels["fiscal"]}: {score.fiscal_score}/100</span>
    <span style="{mini}background:#dbeafe;color:#1d4ed8;">{labels["financial"]}: {score.financial_score}/100</span>
    <span style="{mini}background:#ffedd5;color:#c2410c;">{labels["economic"]}: {score.economic_score}/100</span>
  </div>

  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:14px;">
    <span style="{chip}background:#dbeafe;color:#1d4ed8;">{labels["invoices"]}: {score.invoices_count}</span>
    <span style="{chip}background:#dcfce7;color:#166534;">{labels["gross"]}: {score.gross:.2f} EUR</span>
    <span style="{chip}background:#ffedd5;color:#c2410c;">{labels["vat"]}: {score.vat:.2f} EUR</span>
    <span style="{chip}background:#ede9fe;color:#6d28d9;">{labels["charges"]}: {score.other_charges:.2f} EUR</span>
    <span style="{chip}background:#bbf7d0;color:#14532d;font-weight:950;">{labels["net"]}: {net_display}</span>
  </div>
</div>
"""

    st.markdown(html, unsafe_allow_html=True)


