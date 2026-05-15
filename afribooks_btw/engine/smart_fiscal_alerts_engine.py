from dataclasses import dataclass


@dataclass
class SmartFiscalAlert:
    level: str
    icon: str
    title: str
    message: str


def build_smart_fiscal_alerts(
    invoices_count: int,
    gross: float,
    vat: float,
    other_charges: float,
    net: float,
) -> list[SmartFiscalAlert]:
    alerts: list[SmartFiscalAlert] = []

    invoices = int(invoices_count or 0)
    gross_value = float(gross or 0)
    vat_value = float(vat or 0)
    charges_value = float(other_charges or 0)
    net_value = float(net or 0)

    if net_value < 0:
        alerts.append(
            SmartFiscalAlert(
                level="danger",
                icon="🚨",
                title="Résultat négatif",
                message="Votre résultat net est négatif. Vérifiez vos charges et votre niveau de revenus.",
            )
        )

    if gross_value > 0 and charges_value / gross_value >= 0.35:
        alerts.append(
            SmartFiscalAlert(
                level="warning",
                icon="⚠️",
                title="Charges élevées",
                message="Vos charges représentent une part importante de votre chiffre d'affaires.",
            )
        )

    if vat_value > 250:
        alerts.append(
            SmartFiscalAlert(
                level="info",
                icon="⚠️",
                title="TVA à surveiller",
                message="Le montant de TVA est significatif. Vérifiez la TVA récupérable sur vos achats et services.",
            )
        )

    if invoices < 3:
        alerts.append(
            SmartFiscalAlert(
                level="warning",
                icon="⚠️",
                title="Peu de factures",
                message="Votre volume de facturation est faible sur la période sélectionnée.",
            )
        )

    if gross_value > 0 and net_value / gross_value >= 0.60:
        alerts.append(
            SmartFiscalAlert(
                level="success",
                icon="🎯",
                title="Bonne rentabilité nette",
                message="Votre marge nette est solide sur cette période.",
            )
        )

    if gross_value > 1000 and net_value > 0:
        alerts.append(
            SmartFiscalAlert(
                level="success",
                icon="📈",
                title="Bon niveau d'activité",
                message="Votre activité montre un bon volume économique sur la période.",
            )
        )

    if gross_value > 0 and vat_value / gross_value <= 0.20:
        alerts.append(
            SmartFiscalAlert(
                level="success",
                icon="✅",
                title="TVA maîtrisée",
                message="Votre niveau de TVA reste cohérent par rapport au chiffre d'affaires.",
            )
        )

    return alerts

