import streamlit as st
from pathlib import Path

from afribooks_btw.reports.csv_invoice_report import render_csv_invoice
from afribooks_btw.reports.pdf_invoice_report import render_pdf_invoice


def render_invoice_preview(
    company_profile,
    partner,
    invoice_data: dict,
) -> None:
    st.markdown("## Invoice preview / Apercu facture")

    st.markdown("---")

    col_company, col_invoice = st.columns(2)

    with col_company:
        st.markdown("### Company")
        if company_profile:
            logo_path = getattr(company_profile, "logo_path", "")

            if logo_path and Path(logo_path).exists():
                st.image(
                    logo_path,
                    width=160,
                    caption="Company logo",
                )

            st.write(getattr(company_profile, "company_name", ""))
            st.write(getattr(company_profile, "trade_name", ""))
            st.write(getattr(company_profile, "address", ""))
            st.write(
                f"{getattr(company_profile, 'postal_code', '')} "
                f"{getattr(company_profile, 'city', '')}"
            )
            st.write(getattr(company_profile, "country", ""))
            st.write(f"KvK: {getattr(company_profile, 'kvk_number', '')}")
            st.write(f"BTW: {getattr(company_profile, 'btw_number', '')}")
            st.write(f"IBAN: {getattr(company_profile, 'iban', '')}")
        else:
            st.warning(
                "No company profile found. Please save your company profile first."
            )

    with col_invoice:
        st.markdown("### Invoice")
        st.write(f"Invoice ID: {invoice_data.get('invoice_id', '-')}")
        st.write(f"Invoice date: {invoice_data.get('invoice_date', '-')}")
        st.write(f"Due date: {invoice_data.get('due_date', '-')}")
        st.write(f"Client account: {getattr(partner, 'account_number', '-')}")
        st.write(f"Client type: {invoice_data.get('client_type', '-')}")

    st.markdown("---")

    st.markdown("### Client")

    st.write(getattr(partner, "company_name", "-"))
    st.write(f"Country: {getattr(partner, 'country_code', '-')}")
    st.write(
        "VAT/Fiscal: "
        f"{getattr(partner, 'vat_number', None) or getattr(partner, 'fiscal_number', None) or '-'}"
    )

    st.markdown("---")

    st.markdown("### Invoice line")

    line_amount = (
        float(invoice_data.get("unit_price", 0))
        * float(invoice_data.get("quantity", 0))
    )

    st.table(
        [
            {
                "Reference": invoice_data.get("line_reference", ""),
                "Designation": invoice_data.get("designation", ""),
                "Unit price": invoice_data.get("unit_price", 0),
                "Quantity": invoice_data.get("quantity", 0),
                "Amount": round(line_amount, 2),
            }
        ]
    )

    discount = float(invoice_data.get("discount", 0) or 0)
    shipping = float(invoice_data.get("shipping", 0) or 0)
    subtotal = line_amount
    total_before_vat = subtotal - discount + shipping

    st.markdown("### Totals")

    col_sub, col_discount, col_shipping, col_total = st.columns(4)

    with col_sub:
        st.metric("Subtotal", f"{subtotal:.2f} EUR")

    with col_discount:
        st.metric("Discount", f"{discount:.2f} EUR")

    with col_shipping:
        st.metric("Shipping", f"{shipping:.2f} EUR")

    with col_total:
        st.metric("Before VAT", f"{total_before_vat:.2f} EUR")

    legal_mentions = invoice_data.get("legal_mentions", [])

    if legal_mentions:
        st.markdown("### Legal mentions")
        for mention in legal_mentions:
            st.info(mention)

    footer = getattr(company_profile, "invoice_footer", "") if company_profile else ""

    if footer:
        st.markdown("---")
        st.caption(footer)

    st.markdown("---")
    st.markdown("### Export")

    export_dir = Path("afribooks_btw") / "reports" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    invoice_id = str(invoice_data.get("invoice_id", "invoice"))

    pdf_path = export_dir / f"invoice_{invoice_id}.pdf"
    csv_path = export_dir / f"invoice_{invoice_id}.csv"

    try:
        render_pdf_invoice(
            output_path=str(pdf_path),
            company_profile=company_profile,
            partner=partner,
            invoice_data=invoice_data,
        )

        render_csv_invoice(
            output_path=str(csv_path),
            company_profile=company_profile,
            partner=partner,
            invoice_data=invoice_data,
        )

        col_pdf, col_csv = st.columns(2)

        with col_pdf:
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    "Download PDF",
                    data=pdf_file,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                )

        with col_csv:
            with open(csv_path, "rb") as csv_file:
                st.download_button(
                    "Download CSV",
                    data=csv_file,
                    file_name=csv_path.name,
                    mime="text/csv",
                )

    except Exception as exc:
        st.error(f"Unable to generate exports: {exc}")
