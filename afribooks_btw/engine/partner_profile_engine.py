from dataclasses import dataclass


CUSTOMER_PREFIX = "41"
SUPPLIER_PREFIX = "40"


@dataclass
class PartnerProfile:
    partner_type: str
    account_number: str
    company_name: str
    vat_number: str | None = None
    fiscal_number: str | None = None
    country_code: str = "NL"
    is_company: bool = False


def _get_partner_prefix(partner_type: str) -> str:
    clean_type = str(partner_type).upper().strip()

    if clean_type == "SUPPLIER":
        return SUPPLIER_PREFIX

    return CUSTOMER_PREFIX


def generate_partner_account_number(
    partner_type: str,
    sequence: int | None = None,
    custom_suffix: str | None = None,
) -> str:
    """
    Generate accounting partner account number.

    Customers  -> must start with 41
    Suppliers  -> must start with 40

    If custom_suffix is provided, AfriBooks keeps the accounting prefix
    and appends the user's configured suffix.
    """

    prefix = _get_partner_prefix(partner_type)
    clean_suffix = str(custom_suffix or "").strip().replace(" ", "")

    if clean_suffix:
        if clean_suffix.startswith(prefix):
            return clean_suffix

        return f"{prefix}{clean_suffix}"

    if sequence is None:
        sequence = 1

    return f"{prefix}{int(sequence):04d}"


def create_partner_profile(
    partner_type: str,
    company_name: str,
    sequence: int | None = None,
    custom_suffix: str | None = None,
    vat_number: str | None = None,
    fiscal_number: str | None = None,
    country_code: str = "NL",
    is_company: bool = False,
) -> PartnerProfile:
    """
    Create normalized partner profile.

    Future:
    - DB persistence
    - automatic sequence
    - duplicate detection
    - VAT validation
    - EU VIES validation
    """

    account_number = generate_partner_account_number(
        partner_type=partner_type,
        sequence=sequence,
        custom_suffix=custom_suffix,
    )

    return PartnerProfile(
        partner_type=str(partner_type).upper().strip(),
        account_number=account_number,
        company_name=company_name.strip(),
        vat_number=(vat_number or "").strip() or None,
        fiscal_number=(fiscal_number or "").strip() or None,
        country_code=(country_code or "NL").upper(),
        is_company=bool(is_company),
    )
