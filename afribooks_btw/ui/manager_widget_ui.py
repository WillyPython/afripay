import streamlit as st

from afribooks_btw.engine.fiscal_health_engine import calculate_fiscal_health_score
from afribooks_btw.engine.smart_fiscal_alerts_engine import build_smart_fiscal_alerts
from afribooks_btw.engine.session_service import get_afribooks_language


TEXTS = {
    "nl": {
        "companion": "Financial Companion AI",
        "score": "Fiscale gezondheidsscore",
        "status": "Status",
        "gross": "Omzet",
        "vat": "BTW",
        "charges": "Kosten",
        "net": "Netto",
        "feeling": "Uw gevoel?",
        "alerts": "Slimme waarschuwingen",
    },
    "fr": {
        "companion": "Financial Companion AI",
        "score": "Score de sante fiscale",
        "status": "Statut",
        "gross": "Chiffre d'affaires",
        "vat": "TVA",
        "charges": "Charges",
        "net": "Net",
        "feeling": "Uw gevoel?",
        "alerts": "Alertes intelligentes",
    },
    "en": {
        "companion": "Financial Companion AI",
        "score": "Fiscal Health Score",
        "status": "Status",
        "gross": "Gross",
        "vat": "VAT",
        "charges": "Charges",
        "net": "Net",
        "feeling": "How do you feel?",
        "alerts": "Slimme waarschuwingen",
    },
}

def render_manager_widget_ui(
    invoices_count: int = 0,
    gross: float = 0.0,
    vat: float = 0.0,
    other_charges: float = 0.0,
    net: float = 0.0,
    compact: bool = False,
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

    alerts = build_smart_fiscal_alerts(
        invoices_count=invoices_count,
        gross=gross,
        vat=vat,
        other_charges=other_charges,
        net=net,
    )

    width = "230px" if compact else "320px"
    top = "105px" if compact else "92px"
    net_display = f"{score.net:+.2f} EUR"

    alert_html = ""

    if not compact:
        alert_html = "".join(
            [
                f'<div style="margin-top:8px;padding:8px;border-radius:12px;background:#f8fafc;border:1px solid #e5e7eb;">'
                f'<div style="font-size:0.76rem;font-weight:900;color:#0f172a;">{alert.icon} {alert.title}</div>'
                f'<div style="font-size:0.72rem;color:#475569;margin-top:3px;">{alert.message}</div>'
                f'</div>'
                for alert in alerts[:3]
            ]
        )

    details_html = ""

    if not compact:
        details_html = f"""
  <div style="margin-top:12px;font-size:0.78rem;color:#475569;">
    <div style="display:grid;grid-template-columns:105px 1fr;gap:4px;">
      <div>{labels["gross"]}</div><div style="text-align:right;font-weight:800;">{score.gross:.2f} EUR</div>
      <div>{labels["vat"]}</div><div style="text-align:right;font-weight:800;">{score.vat:.2f} EUR</div>
      <div>{labels["charges"]}</div><div style="text-align:right;font-weight:800;">{score.other_charges:.2f} EUR</div>
      <div>{labels["net"]}</div><div style="text-align:right;font-weight:900;color:#111827;">{net_display}</div>
    </div>
  </div>

  <div style="margin-top:12px;font-size:0.82rem;font-weight:800;color:#0f172a;">{labels["feeling"]}</div>
  <div style="margin-top:8px;display:flex;gap:8px;">
    <span style="padding:7px 9px;border-radius:12px;background:#dcfce7;">😀</span>
    <span style="padding:7px 9px;border-radius:12px;background:#fef9c3;">🙂</span>
    <span style="padding:7px 9px;border-radius:12px;background:#fee2e2;">😟</span>
  </div>

  <div style="margin-top:12px;font-size:0.82rem;font-weight:900;color:#0f172a;">{labels["alerts"]}</div>
  {alert_html}
"""

    compact_html = ""

    if compact:
        compact_html = f"""
  <div style="margin-top:8px;font-size:0.76rem;color:#475569;">
    {labels["net"]} <strong>{net_display}</strong>
  </div>
  <div style="margin-top:8px;font-size:1.1rem;">😀 🙂 😟</div>
"""

    html = f"""
<div style="position:fixed;top:{top};right:22px;z-index:9999;width:{width};border-radius:18px;padding:16px;background:#ffffff;box-shadow:0 10px 28px rgba(15,23,42,0.20);border:1px solid rgba(15,23,42,0.12);">
  <div style="font-size:0.82rem;font-weight:900;color:#0f172a;">{labels["companion"]}</div>
  <div style="font-size:0.76rem;font-weight:800;color:#64748b;">{labels["score"]}</div>
  <div style="font-size:2rem;font-weight:950;color:#111827;line-height:1.1;margin-top:4px;">{score.global_score}/100</div>
  <div style="font-size:0.82rem;font-weight:800;color:#475569;margin-top:4px;">{labels["status"]}: {score.status}</div>
  {details_html}
  {compact_html}
</div>
"""

    st.markdown(html, unsafe_allow_html=True)




