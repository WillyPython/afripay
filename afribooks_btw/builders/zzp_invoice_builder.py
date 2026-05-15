from datetime import date, timedelta
from decimal import Decimal

from services.finance_service import create_invoice_with_lines
from afribooks_btw.engine.legal_invoice_mentions_engine import (
    get_legal_invoice_mentions,
    get_mentions_for_language,
)
from afribooks_btw.engine.vat_calculator import compute_vat_from_gross


def _to_decimal(value: float | int | str | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _net_from_amount(amount: Decimal, amount_type: str) -> Decimal:
    if str(amount_type).upper() == "TTC":
        calc = compute_vat_from_gross(float(amount), 0.21)
        return _to_decimal(calc["net_amount"])

    return amount


def create_zzp_invoice(
    client_name: str,
    client_country: str,
    designation: str,
    unit_price: float,
    quantity: float = 1,
    amount_type: str = "HT",
    client_type: str = "PARTICULIER",
    client_vat_number: str | None = None,
    line_reference: str | None = None,
    invoice_date: date | None = None,
    due_date: date | None = None,
    discount: float = 0,
    shipping: float = 0,
    language: str = "nl",
) -> int:
    """
    Universal AfriBooks BTW invoice builder V1.

    Compatible with the current backend:
    - stores reference inside description
    - stores due date inside note
    - stores legal mentions inside note
    - handles discount as negative invoice line
    - handles shipping as positive invoice line
    """

    invoice_date = invoice_date or date.today()
    due_date = due_date or (invoice_date + timedelta(days=14))

    client_country = (client_country or "NL").upper()
    client_type = (client_type or "PARTICULIER").upper()

    partner_type = "B2B" if client_type in ("ENTREPRISE", "COMPANY", "B2B") else "B2C"

    unit_price_dec = _to_decimal(unit_price)
    quantity_dec = Decimal(str(quantity or 1))
    discount_dec = _to_decimal(discount)
    shipping_dec = _to_decimal(shipping)

    unit_price_net = _net_from_amount(unit_price_dec, amount_type)

    clean_ref = (line_reference or "").strip()
    clean_designation = (designation or "").strip()

    description = clean_designation
    if clean_ref:
        description = f"[{clean_ref}] {clean_designation}"

    lines = [
        {
            "description": description,
            "quantity": quantity_dec,
            "unit_price_net_eur": str(unit_price_net),
            "vat_category": "STANDARD",
        }
    ]

    if discount_dec > 0:
        discount_net = _net_from_amount(discount_dec, amount_type)
        lines.append(
            {
                "description": "Discount / Remise",
                "quantity": 1,
                "unit_price_net_eur": str(-discount_net),
                "vat_category": "STANDARD",
            }
        )

    if shipping_dec > 0:
        shipping_net = _net_from_amount(shipping_dec, amount_type)
        lines.append(
            {
                "description": "Shipping / Transport",
                "quantity": 1,
                "unit_price_net_eur": str(shipping_net),
                "vat_category": "STANDARD",
            }
        )

    expected_vat_rate = 0.21

    if client_country != "NL" and partner_type == "B2B" and client_vat_number:
        expected_vat_rate = 0.0

    if client_country not in {
        "NL", "BE", "DE", "FR", "LU", "ES", "IT", "PT", "IE", "AT",
        "DK", "SE", "FI", "PL", "CZ", "SK", "SI", "HR", "HU", "RO",
        "BG", "GR", "CY", "MT", "EE", "LV", "LT",
    }:
        expected_vat_rate = 0.0

    legal_mentions = get_legal_invoice_mentions(
        vat_rate=expected_vat_rate,
        partner_country_code=client_country,
        partner_type=partner_type,
        has_partner_vat_number=bool(client_vat_number),
        invoice_type="SALE",
    )

    legal_mention_texts = get_mentions_for_language(
        legal_mentions,
        language=language,
    )

    invoice_number = f"ZZP-{invoice_date.strftime('%Y%m%d-%H%M%S')}"

    note_parts = [
        "Universal invoice V1",
        f"Due date: {due_date.isoformat()}",
        f"Client type: {client_type}",
        f"Amount type: {amount_type}",
    ]

    if legal_mention_texts:
        note_parts.append(
            "Legal mentions: " + " | ".join(legal_mention_texts)
        )

    note = " | ".join(note_parts)

    invoice_id = create_invoice_with_lines(
        invoice_number=invoice_number,
        invoice_type="SALE",
        invoice_date=invoice_date,
        partner_name=client_name,
        partner_vat_number=client_vat_number,
        partner_country_code=client_country,
        partner_type=partner_type,
        lines=lines,
        source="ZZP_UNIVERSAL_MODE",
        note=note,
    )

    return invoice_id
