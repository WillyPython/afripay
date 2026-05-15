from typing import Any
from afribooks_btw.schemas.vat_decision import VatDecision


EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "PL",
    "PT", "RO", "SK", "SI", "ES", "SE"
}

VAT_RATE_STANDARD = 0.21
VAT_RATE_REDUCED = 0.09
VAT_RATE_ZERO = 0.00


def normalize_country(value: str | None) -> str:
    return (value or "").strip().upper()


def normalize_text(value: str | None) -> str:
    return (value or "").strip().upper()


def determine_vat_treatment(form_data: dict[str, Any], profile: dict[str, Any]) -> VatDecision:
    """
    AfriBooks BTW - VAT ENGINE (Language Ready)

    Cette version :
    ✔ utilise des codes de traduction (PAS de texte direct)
    ✔ reste indépendante du UI
    ✔ est prête pour FR / EN / NL
    """

    transaction_type = normalize_text(form_data.get("transaction_type"))  # SALE / PURCHASE
    vat_category = normalize_text(form_data.get("vat_category"))          # STANDARD / REDUCED / ZERO / EXEMPT

    partner_country = normalize_country(profile.get("country_code"))
    partner_type = normalize_text(profile.get("partner_type"))            # B2B / B2C
    has_vat = bool(profile.get("vat_number"))

    # =========================
    # 1. EXEMPT
    # =========================
    if vat_category == "EXEMPT":
        return VatDecision(
            vat_applicable=False,
            vat_rate=VAT_RATE_ZERO,
            vat_type="EXEMPT",
            treatment="VAT_EXEMPT",
            reverse_charge=False,
            report_box=None,
            reason="VAT_EXEMPT_REASON",
        )

    # =========================
    # 2. NL DOMESTIC
    # =========================
    if partner_country == "NL":
        rate = VAT_RATE_STANDARD

        if vat_category == "REDUCED":
            rate = VAT_RATE_REDUCED
        elif vat_category == "ZERO":
            rate = VAT_RATE_ZERO

        return VatDecision(
            vat_applicable=True,
            vat_rate=rate,
            vat_type="COLLECTED" if transaction_type == "SALE" else "DEDUCTIBLE",
            treatment="NL_DOMESTIC",
            reverse_charge=False,
            report_box="1a" if rate == VAT_RATE_STANDARD else "1b",
            reason="NL_TRANSACTION",
        )

    # =========================
    # 3. EU B2B (Reverse charge)
    # =========================
    if partner_country in EU_COUNTRIES and partner_type == "B2B" and has_vat:
        return VatDecision(
            vat_applicable=False,
            vat_rate=VAT_RATE_ZERO,
            vat_type="REVERSE_CHARGE",
            treatment="EU_B2B",
            reverse_charge=True,
            report_box="3b",
            reason="EU_REVERSE_CHARGE",
        )

    # =========================
    # 4. EXPORT NON EU
    # =========================
    if partner_country not in EU_COUNTRIES and partner_country != "NL":
        return VatDecision(
            vat_applicable=True,
            vat_rate=VAT_RATE_ZERO,
            vat_type="ZERO_EXPORT",
            treatment="EXPORT",
            reverse_charge=False,
            report_box="3a",
            reason="EXPORT_NON_EU",
        )

    # =========================
    # 5. FALLBACK
    # =========================
    return VatDecision(
        vat_applicable=True,
        vat_rate=VAT_RATE_STANDARD,
        vat_type="REVIEW",
        treatment="UNKNOWN",
        reverse_charge=False,
        report_box=None,
        reason="REVIEW_REQUIRED",
    )
