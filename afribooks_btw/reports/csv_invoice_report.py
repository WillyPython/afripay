import csv
from pathlib import Path


def render_csv_invoice(
    output_path: str,
    company_profile,
    partner,
    invoice_data: dict,
) -> str:
    output_file = Path(output_path)

    legal_mentions = invoice_data.get("legal_mentions", [])

    row = {
        "invoice_id": invoice_data.get("invoice_id", ""),
        "invoice_date": invoice_data.get("invoice_date", ""),
        "due_date": invoice_data.get("due_date", ""),
        "company_name": getattr(company_profile, "company_name", ""),
        "company_vat_number": getattr(company_profile, "btw_number", ""),
        "client_account_number": getattr(partner, "account_number", ""),
        "client_name": getattr(partner, "company_name", ""),
        "client_country": getattr(partner, "country_code", ""),
        "client_vat_number": getattr(partner, "vat_number", "") or "",
        "client_fiscal_number": getattr(partner, "fiscal_number", "") or "",
        "client_type": invoice_data.get("client_type", ""),
        "reference": invoice_data.get("line_reference", ""),
        "designation": invoice_data.get("designation", ""),
        "unit_price": invoice_data.get("unit_price", 0),
        "quantity": invoice_data.get("quantity", 0),
        "amount_type": invoice_data.get("amount_type", ""),
        "discount": invoice_data.get("discount", 0),
        "shipping": invoice_data.get("shipping", 0),
        "legal_mentions": " | ".join(legal_mentions),
    }

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=list(row.keys()),
        )

        writer.writeheader()
        writer.writerow(row)

    return str(output_file)
