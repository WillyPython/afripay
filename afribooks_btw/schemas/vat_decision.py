from dataclasses import dataclass


@dataclass(frozen=True)
class VatDecision:
    vat_applicable: bool
    vat_rate: float
    vat_type: str
    treatment: str
    reverse_charge: bool
    report_box: str | None
    reason: str
    