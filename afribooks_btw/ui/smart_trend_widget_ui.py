import streamlit as st

from afribooks_btw.engine.smart_business_insight_engine import (
    build_smart_business_insights,
)
from afribooks_btw.engine.smart_trend_engine import (
    build_smart_trends,
)
from afribooks_btw.engine.session_service import get_afribooks_language



TEXTS = {
    "nl": {
        "premium_label": "PREMIUM_PLUS · FINANCIAL COMPANION AI",
        "title": "Moderne analyse / Slimme bedrijfsinzichten",
        "subtitle": "Zachte analyse van uw trends, kosten, BTW en netto resultaat.",
        "business_status": "Bedrijfsstatus",
        "current_value": "Huidige waarde",
        "smart_insights": "Slimme bedrijfsinzichten",
        "ai_insight": "AI-inzicht",
        "up": "OMHOOG",
        "down": "OMLAAG",
    },
    "fr": {
        "premium_label": "PREMIUM_PLUS · FINANCIAL COMPANION AI",
        "title": "Analyse moderne / Insights business intelligents",
        "subtitle": "Analyse douce de vos tendances, charges, TVA et resultat net.",
        "business_status": "Statut business",
        "current_value": "Valeur actuelle",
        "smart_insights": "Insights business intelligents",
        "ai_insight": "Insight AI",
        "up": "HAUSSE",
        "down": "BAISSE",
    },
    "en": {
        "premium_label": "PREMIUM_PLUS · FINANCIAL COMPANION AI",
        "title": "Modern Analytics / Smart Business Insights",
        "subtitle": "Soft analysis of your trends, charges, VAT and net result.",
        "business_status": "Business status",
        "current_value": "Current value",
        "smart_insights": "Smart Business Insights",
        "ai_insight": "AI Insight",
        "up": "UP",
        "down": "DOWN",
    },
}

def get_business_state(current_net: float, net_trend: float, charges_trend: float, vat_trend: float) -> dict:
    if current_net < 0:
        return {
            "label": "Attention",
            "bg": "#fff7ed",
            "color": "#c2410c",
            "message": "Votre resultat net demande une attention particuliere."
        }

    if charges_trend > 25:
        return {
            "label": "Charges a surveiller",
            "bg": "#fef2f2",
            "color": "#b91c1c",
            "message": "Vos charges progressent rapidement. Une verification peut proteger votre marge."
        }

    if vat_trend > 20:
        return {
            "label": "TVA active",
            "bg": "#fffbeb",
            "color": "#b45309",
            "message": "Votre TVA augmente. Pensez a preparer votre prochaine declaration."
        }

    if net_trend > 10:
        return {
            "label": "Growth",
            "bg": "#eff6ff",
            "color": "#1d4ed8",
            "message": "Votre activite montre une dynamique positive."
        }

    return {
        "label": "Stable",
        "bg": "#ecfdf5",
        "color": "#047857",
        "message": "Votre activite semble stable et sous controle."
    }


def get_trend_style(label: str, percent: float) -> dict:
    label_upper = (label or "").upper()

    if label_upper == "CHARGES":
        positive = percent <= 0
    else:
        positive = percent >= 0

    if positive:
        return {
            "bg": "#ecfdf5",
            "color": "#047857",
            "direction": "GOOD",
        }

    return {
        "bg": "#fef2f2",
        "color": "#b91c1c",
        "direction": "WATCH",
    }

def render_smart_trend_widget_ui(
    current_gross: float = 0.0,
    previous_gross: float = 0.0,
    current_vat: float = 0.0,
    previous_vat: float = 0.0,
    current_charges: float = 0.0,
    previous_charges: float = 0.0,
    current_net: float = 0.0,
    previous_net: float = 0.0,
) -> None:
    lang = get_afribooks_language()
    labels = TEXTS.get(lang, TEXTS["nl"])

    trends = build_smart_trends(
        current_gross=current_gross,
        previous_gross=previous_gross,
        current_vat=current_vat,
        previous_vat=previous_vat,
        current_charges=current_charges,
        previous_charges=previous_charges,
        current_net=current_net,
        previous_net=previous_net,
    )

    trend_map = {trend.label.upper(): trend for trend in trends}

    gross_trend = trend_map.get("REVENUE").trend_percent if trend_map.get("REVENUE") else 0
    vat_trend = trend_map.get("VAT").trend_percent if trend_map.get("VAT") else 0
    charges_trend = trend_map.get("CHARGES").trend_percent if trend_map.get("CHARGES") else 0
    net_trend = trend_map.get("NET").trend_percent if trend_map.get("NET") else 0

    insights = build_smart_business_insights(
        gross_trend=gross_trend,
        vat_trend=vat_trend,
        charges_trend=charges_trend,
        net_trend=net_trend,
        current_gross=current_gross,
        current_charges=current_charges,
        current_net=current_net,
    )

    business_state = get_business_state(
        current_net=current_net,
        net_trend=net_trend,
        charges_trend=charges_trend,
        vat_trend=vat_trend,
    )

    health_badge = business_state["label"]
    health_bg = business_state["bg"]
    health_color = business_state["color"]
    health_message = business_state["message"]

    st.markdown(
        f"""
        <div style="
            border-radius:22px;
            padding:22px 24px;
            background:linear-gradient(135deg,#0f172a,#1e293b);
            color:white;
            margin-bottom:18px;
            box-shadow:0 12px 30px rgba(15,23,42,0.20);
        ">
            <div style="font-size:0.78rem;font-weight:800;letter-spacing:0.08em;color:#cbd5e1;">
                {labels["premium_label"]}
            </div>
            <div style="font-size:1.35rem;font-weight:950;margin-top:6px;">
                {labels["title"]}
            </div>
            <div style="font-size:0.88rem;color:#cbd5e1;margin-top:6px;">
                {labels["subtitle"]}
            </div>
            <div style="
                display:inline-block;
                margin-top:12px;
                padding:6px 12px;
                border-radius:999px;
                background:{health_bg};
                color:{health_color};
                font-weight:900;
                font-size:0.78rem;
            ">
                {labels["business_status"]} : {health_badge} · {health_message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)

    for index, trend in enumerate(trends[:4]):
        trend_color = "#047857" if trend.trend_percent >= 0 else "#b91c1c"
        trend_bg = "#ecfdf5" if trend.trend_percent >= 0 else "#fef2f2"
        direction = labels["up"] if trend.trend_percent >= 0 else labels["down"]

        with cols[index]:
            st.markdown(
                f"""
                <div style="
                    border-radius:18px;
                    padding:16px 18px;
                    background:#ffffff;
                    border:1px solid #e5e7eb;
                    box-shadow:0 8px 22px rgba(15,23,42,0.08);
                    min-height:145px;
                ">
                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        margin-bottom:10px;
                    ">
                        <div style="font-size:1.35rem;">{trend.icon}</div>
                        <span style="
                            padding:4px 8px;
                            border-radius:999px;
                            background:{trend_bg};
                            color:{trend_color};
                            font-size:0.68rem;
                            font-weight:900;
                        ">
                            {direction}
                        </span>
                    </div>

                    <div style="font-size:0.78rem;color:#64748b;font-weight:900;">
                        {trend.label}
                    </div>

                    <div style="font-size:1.35rem;color:#111827;font-weight:950;margin-top:4px;">
                        {trend.trend_percent:+.2f}%
                    </div>

                    <div style="font-size:0.78rem;color:#475569;margin-top:6px;">
                        {labels["current_value"]} : {trend.value:.2f} EUR
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(f"### {labels['smart_insights']}")

    for insight in insights[:4]:
        st.markdown(
            f"""
            <div style="
                border-radius:18px;
                padding:15px 18px;
                background:#f8fafc;
                border:1px solid #e5e7eb;
                margin-bottom:10px;
                box-shadow:0 5px 16px rgba(15,23,42,0.05);
            ">
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    gap:12px;
                ">
                    <div style="font-weight:950;color:#0f172a;font-size:0.92rem;">
                        {insight.icon} {insight.title}
                    </div>
                    <div style="
                        padding:4px 9px;
                        border-radius:999px;
                        background:#eef2ff;
                        color:#3730a3;
                        font-size:0.68rem;
                        font-weight:900;
                    ">
                        {labels["ai_insight"]}
                    </div>
                </div>

                <div style="color:#475569;font-size:0.82rem;margin-top:7px;line-height:1.45;">
                    {insight.message}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )








