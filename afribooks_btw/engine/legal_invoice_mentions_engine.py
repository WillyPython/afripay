from dataclasses import dataclass


@dataclass
class LegalInvoiceMention:
    code: str
    nl: str
    fr: str
    en: str


def get_legal_invoice_mentions(
    vat_rate: float,
    partner_country_code: str = "NL",
    partner_type: str = "B2C",
    has_partner_vat_number: bool = False,
    invoice_type: str = "SALE",
    is_credit_note: bool = False,
    original_invoice_number: str | None = None,
) -> list[LegalInvoiceMention]:
    mentions: list[LegalInvoiceMention] = []

    country = (partner_country_code or "NL").upper()
    p_type = (partner_type or "B2C").upper()
    inv_type = (invoice_type or "SALE").upper()

    eu_countries = {
        "NL", "BE", "DE", "FR", "LU", "ES", "IT", "PT", "IE", "AT",
        "DK", "SE", "FI", "PL", "CZ", "SK", "SI", "HR", "HU", "RO",
        "BG", "GR", "CY", "MT", "EE", "LV", "LT",
    }

    if is_credit_note and original_invoice_number:
        mentions.append(
            LegalInvoiceMention(
                code="CREDIT_NOTE_REFERENCE",
                nl=f"Creditnota verwijst naar factuur nr. {original_invoice_number}.",
                fr=f"Avoir relatif a la facture no {original_invoice_number}.",
                en=f"Credit note referring to invoice no. {original_invoice_number}.",
            )
        )

    if country != "NL" and country in eu_countries and p_type == "B2B" and has_partner_vat_number:
        mentions.append(
            LegalInvoiceMention(
                code="VAT_REVERSE_CHARGE",
                nl="Btw verlegd.",
                fr="Autoliquidation de la TVA.",
                en="VAT reverse-charged.",
            )
        )

    if country != "NL" and country in eu_countries and p_type == "B2B":
        mentions.append(
            LegalInvoiceMention(
                code="INTRA_EU_SUPPLY",
                nl="Intracommunautaire levering/dienst.",
                fr="Livraison/prestation intracommunautaire.",
                en="Intra-EU supply/service.",
            )
        )

    if country not in eu_countries:
        mentions.append(
            LegalInvoiceMention(
                code="EXPORT_OUTSIDE_EU",
                nl="Export buiten de EU.",
                fr="Export hors Union europeenne.",
                en="Export outside the EU.",
            )
        )

    if float(vat_rate or 0) == 0:
        mentions.append(
            LegalInvoiceMention(
                code="ZERO_VAT",
                nl="0% btw toegepast.",
                fr="TVA a 0% appliquee.",
                en="0% VAT applied.",
            )
        )

    if inv_type == "PURCHASE":
        mentions.append(
            LegalInvoiceMention(
                code="PURCHASE_INVOICE",
                nl="Inkoopfactuur geregistreerd voor boekhouding.",
                fr="Facture fournisseur enregistree pour la comptabilite.",
                en="Purchase invoice recorded for bookkeeping.",
            )
        )

    return mentions


def get_mentions_for_language(
    mentions: list[LegalInvoiceMention],
    language: str = "nl",
) -> list[str]:
    lang = (language or "nl").lower()

    result = []

    for mention in mentions:
        if lang == "fr":
            result.append(mention.fr)
        elif lang == "en":
            result.append(mention.en)
        else:
            result.append(mention.nl)

    return result
