from dataclasses import dataclass


@dataclass
class SmartTrend:
    label: str
    icon: str
    value: float
    trend_percent: float
    direction: str
    message: str


def calculate_trend_percent(
    current_value: float,
    previous_value: float,
) -> float:
    current = float(current_value or 0)
    previous = float(previous_value or 0)

    if previous <= 0:
        return 0.0

    return round(((current - previous) / previous) * 100, 2)


def build_smart_trends(
    current_gross: float,
    previous_gross: float,
    current_vat: float,
    previous_vat: float,
    current_charges: float,
    previous_charges: float,
    current_net: float,
    previous_net: float,
) -> list[SmartTrend]:
    trends: list[SmartTrend] = []

    gross_trend = calculate_trend_percent(
        current_gross,
        previous_gross,
    )

    vat_trend = calculate_trend_percent(
        current_vat,
        previous_vat,
    )

    charges_trend = calculate_trend_percent(
        current_charges,
        previous_charges,
    )

    net_trend = calculate_trend_percent(
        current_net,
        previous_net,
    )

    trends.append(
        SmartTrend(
            label="Revenue",
            icon="📈" if gross_trend >= 0 else "📉",
            value=current_gross,
            trend_percent=gross_trend,
            direction="UP" if gross_trend >= 0 else "DOWN",
            message="Revenue trend analysis",
        )
    )

    trends.append(
        SmartTrend(
            label="VAT",
            icon="⚠️" if vat_trend > 20 else "✅",
            value=current_vat,
            trend_percent=vat_trend,
            direction="UP" if vat_trend >= 0 else "DOWN",
            message="VAT trend analysis",
        )
    )

    trends.append(
        SmartTrend(
            label="Charges",
            icon="📉" if charges_trend > 25 else "✅",
            value=current_charges,
            trend_percent=charges_trend,
            direction="UP" if charges_trend >= 0 else "DOWN",
            message="Operating charges trend",
        )
    )

    trends.append(
        SmartTrend(
            label="Net",
            icon="🔥" if net_trend >= 0 else "🚨",
            value=current_net,
            trend_percent=net_trend,
            direction="UP" if net_trend >= 0 else "DOWN",
            message="Net profitability trend",
        )
    )

    return trends
