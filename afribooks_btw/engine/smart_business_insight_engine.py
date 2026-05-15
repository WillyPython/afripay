from dataclasses import dataclass


@dataclass
class SmartBusinessInsight:
    level: str
    icon: str
    title: str
    message: str


def build_smart_business_insights(
    gross_trend: float,
    vat_trend: float,
    charges_trend: float,
    net_trend: float,
    current_gross: float,
    current_charges: float,
    current_net: float,
) -> list[SmartBusinessInsight]:
    insights: list[SmartBusinessInsight] = []

    gross_value = float(current_gross or 0)
    charges_value = float(current_charges or 0)
    net_value = float(current_net or 0)

    if gross_trend >= 15:
        insights.append(
            SmartBusinessInsight(
                level="success",
                icon="[UP]",
                title="Croissance forte",
                message="Votre chiffre d'affaires progresse fortement par rapport à la période précédente.",
            )
        )

    if net_trend >= 15:
        insights.append(
            SmartBusinessInsight(
                level="success",
                icon="[PROFIT]",
                title="Résultat net en hausse",
                message="Votre résultat net progresse nettement. Votre activité gagne en performance.",
            )
        )

    if net_trend < -10:
        insights.append(
            SmartBusinessInsight(
                level="danger",
                icon="[RISK]",
                title="Rentabilité en baisse",
                message="Votre résultat net diminue. Vérifiez vos charges et votre marge.",
            )
        )

    if charges_trend > gross_trend and charges_trend >= 20:
        insights.append(
            SmartBusinessInsight(
                level="warning",
                icon="[WARNING]",
                title="Charges en hausse rapide",
                message="Vos charges augmentent plus vite que votre chiffre d'affaires.",
            )
        )

    if vat_trend >= 20:
        insights.append(
            SmartBusinessInsight(
                level="info",
                icon="[VAT]",
                title="TVA en hausse",
                message="La TVA augmente fortement. Vérifiez aussi votre TVA récupérable.",
            )
        )

    if gross_value > 0 and charges_value / gross_value <= 0.25 and net_value > 0:
        insights.append(
            SmartBusinessInsight(
                level="success",
                icon="[OK]",
                title="Structure de charges saine",
                message="Vos charges restent maîtrisées par rapport à votre chiffre d'affaires.",
            )
        )

    if not insights:
        insights.append(
            SmartBusinessInsight(
                level="neutral",
                icon="[INFO]",
                title="Situation stable",
                message="Aucune variation majeure détectée sur cette période.",
            )
        )

    return insights

