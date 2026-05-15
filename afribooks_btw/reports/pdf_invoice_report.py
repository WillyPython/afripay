from pathlib import Path
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def render_pdf_invoice(
    output_path: str,
    company_profile,
    partner,
    invoice_data: dict,
) -> str:
    output_file = Path(output_path)

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
    )

    styles = getSampleStyleSheet()

    elements = []

    logo_path = getattr(company_profile, "logo_path", "")

    if logo_path and Path(logo_path).exists():
        logo = Image(
            logo_path,
            width=120,
            height=60,
        )
        elements.append(logo)
        elements.append(Spacer(1, 12))

    company_name = getattr(
        company_profile,
        "company_name",
        "",
    )

    elements.append(
        Paragraph(
            f"<b>{company_name}</b>",
            styles["Title"],
        )
    )

    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"Invoice ID: {invoice_data.get('invoice_id', '-')}",
            styles["BodyText"],
        )
    )

    elements.append(
        Paragraph(
            f"Client: {getattr(partner, 'company_name', '-')}",
            styles["BodyText"],
        )
    )

    elements.append(
        Paragraph(
            f"Designation: {invoice_data.get('designation', '-')}",
            styles["BodyText"],
        )
    )

    elements.append(
        Paragraph(
            f"Quantity: {invoice_data.get('quantity', 0)}",
            styles["BodyText"],
        )
    )

    elements.append(
        Paragraph(
            f"Unit price: {invoice_data.get('unit_price', 0)} EUR",
            styles["BodyText"],
        )
    )

    elements.append(Spacer(1, 18))

    legal_mentions = invoice_data.get(
        "legal_mentions",
        [],
    )

    if legal_mentions:
        elements.append(
            Paragraph(
                "<b>Legal mentions</b>",
                styles["Heading2"],
            )
        )

        for mention in legal_mentions:
            elements.append(
                Paragraph(
                    f"- {mention}",
                    styles["BodyText"],
                )
            )

    footer = getattr(
        company_profile,
        "invoice_footer",
        "",
    )

    if footer:
        elements.append(Spacer(1, 18))

        elements.append(
            Paragraph(
                footer,
                styles["Italic"],
            )
        )

    doc.build(elements)

    return str(output_file)
