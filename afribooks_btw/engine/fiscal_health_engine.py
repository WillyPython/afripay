from dataclasses import dataclass


@dataclass
class FiscalHealthScore:
    invoices_count: int
    gross: float
    vat: float
    other_charges: float
    net: float
    fiscal_score: int
    financial_score: int
    economic_score: int
    global_score: int
    status: str


def _clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def calculate_fiscal_health_score(
    invoices_count: int,
    gross: float,
    vat: float,
    other_charges: float,
    net: float,
) -> FiscalHealthScore:
    invoices = int(invoices_count or 0)
    gross_value = float(gross or 0)
    vat_value = float(vat or 0)
    charges_value = float(other_charges or 0)
    net_value = float(net or 0)

    if gross_value <= 0:
        fiscal_score = 0
        financial_score = 0
    else:
        vat_ratio = vat_value / gross_value
        charges_ratio = charges_value / gross_value
        net_ratio = net_value / gross_value

        fiscal_score = _clamp_score(100 - (vat_ratio * 100))
        financial_score = _clamp_score((net_ratio * 100) - (charges_ratio * 20))

    economic_score = _clamp_score(min(invoices, 20) / 20 * 100)

    global_score = _clamp_score(
        (fiscal_score * 0.30)
        + (financial_score * 0.45)
        + (economic_score * 0.25)
    )

    if global_score >= 75:
        status = "STRONG"
    elif global_score >= 50:
        status = "STABLE"
    elif global_score >= 25:
        status = "WATCH"
    else:
        status = "RISK"

    return FiscalHealthScore(
        invoices_count=invoices,
        gross=round(gross_value, 2),
        vat=round(vat_value, 2),
        other_charges=round(charges_value, 2),
        net=round(net_value, 2),
        fiscal_score=fiscal_score,
        financial_score=financial_score,
        economic_score=economic_score,
        global_score=global_score,
        status=status,
    )

