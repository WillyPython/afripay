from dataclasses import dataclass

from afribooks_btw.engine.smart_business_insight_engine import (
    build_smart_business_insights,
)
from afribooks_btw.engine.smart_fiscal_alerts_engine import (
    build_smart_fiscal_alerts,
)


@dataclass
class FiscalAssistantResponse:
    fiscal_alerts: list
    business_insights: list


def build_fiscal_assistant_response(
    invoices_count: int,
    gross: float,
    vat: float,
    other_charges: float,
    net: float,
    gross_trend: float = 0.0,
    vat_trend: float = 0.0,
    charges_trend: float = 0.0,
    net_trend: float = 0.0,
) -> FiscalAssistantResponse:
    fiscal_alerts = build_smart_fiscal_alerts(
        invoices_count=invoices_count,
        gross=gross,
        vat=vat,
        other_charges=other_charges,
        net=net,
    )

    business_insights = build_smart_business_insights(
        gross_trend=gross_trend,
        vat_trend=vat_trend,
        charges_trend=charges_trend,
        net_trend=net_trend,
        current_gross=gross,
        current_charges=other_charges,
        current_net=net,
    )

    return FiscalAssistantResponse(
        fiscal_alerts=fiscal_alerts,
        business_insights=business_insights,
    )
