import streamlit as st
from datetime import date, timedelta

from afribooks_btw.builders.zzp_invoice_builder import create_zzp_invoice
from afribooks_btw.engine.legal_invoice_mentions_engine import (
    get_legal_invoice_mentions,
    get_mentions_for_language,
)
from afribooks_btw.engine.partner_profile_engine import create_partner_profile
from afribooks_btw.engine.session_service import (
    get_afribooks_language,
    get_company_profile,
    init_afribooks_session,
    set_afribooks_language,
)
from afribooks_btw.ui.invoice_preview_ui import render_invoice_preview


def render_zzp_invoice_ui() -> None:
    init_afribooks_session()

    language_options = {
        "Nederlands": "nl",
        "Francais": "fr",
        "English": "en",
    }

    current_lang = get_afribooks_language()

    selected_language_label = st.selectbox(
        "Kies uw taal / Choisissez votre langue / Choose your language",
        list(language_options.keys()),
        index=list(language_options.values()).index(current_lang),
        key="afribooks_language_selector",
    )

    lang = language_options[selected_language_label]
    set_afribooks_language(lang)

    st.markdown("## Universal Invoice / Facture universelle")
    st.caption(
        "Create a professional invoice with client/company type, account number, VAT number, dates, line item, discount, shipping and legal VAT mentions."
    )

    with st.form("universal_invoice_form"):
        st.markdown("### Invoice information")

        col_date, col_due = st.columns(2)

        with col_date:
            invoice_date = st.date_input(
                "Invoice date / Date facture",
                value=date.today(),
            )

        with col_due:
            due_date = st.date_input(
                "Due date / Date echeance",
                value=date.today() + timedelta(days=14),
            )

        st.markdown("### Client information")

        col_client, col_country = st.columns(2)

        with col_client:
            client_name = st.text_input("Client name / Nom du client")

        with col_country:
            client_country = st.selectbox(
                "Client country / Pays du client",
                ["NL", "BE", "DE", "FR", "CM"],
                index=0,
            )

        client_type_label = st.radio(
            "Client type / Type de client",
            ["Particulier", "Entreprise"],
            horizontal=True,
            index=0,
        )

        client_type = (
            "ENTREPRISE"
            if client_type_label == "Entreprise"
            else "PARTICULIER"
        )

        col_suffix, col_vat = st.columns(2)

        with col_suffix:
            client_account_suffix = st.text_input(
                "Client account suffix / Suite compte client",
                placeholder="Example: 0001, 0Peter, 111Peter",
            )

        with col_vat:
            client_vat_number = st.text_input(
                "VAT/fiscal number / Numero TVA ou fiscal",
                help=(
                    "Fill this only when the client is a company. "
                    "/ A remplir seulement si le client est une entreprise."
                ),
                placeholder="Example: NL999999999B01",
            )

        st.markdown("### Invoice line")

        col_ref, col_designation = st.columns([1, 3])

        with col_ref:
            line_reference = st.text_input("Reference")

        with col_designation:
            designation = st.text_input("Designation")

        col_unit, col_qty, col_type = st.columns(3)

        with col_unit:
            unit_price = st.number_input(
                "Unit price / Prix unitaire",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            )

        with col_qty:
            quantity = st.number_input(
                "Quantity / Quantite",
                min_value=0.0,
                step=1.0,
                value=1.0,
                format="%.2f",
            )

        with col_type:
            amount_type = st.radio(
                "Amount type / Type montant",
                ["HT", "TTC"],
                horizontal=True,
                index=0,
            )

        st.markdown("### Discount and shipping")

        col_discount, col_shipping = st.columns(2)

        with col_discount:
            discount = st.number_input(
                "Discount / Remise",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            )

        with col_shipping:
            shipping = st.number_input(
                "Shipping / Transport",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            )

        submitted = st.form_submit_button("Create invoice / Creer la facture")

    if not submitted:
        return

    if not client_name.strip():
        st.error("Client name is required.")
        return

    if not designation.strip():
        st.error("Designation is required.")
        return

    if unit_price <= 0:
        st.error("Unit price must be greater than 0.")
        return

    if quantity <= 0:
        st.error("Quantity must be greater than 0.")
        return

    partner = create_partner_profile(
        partner_type="CUSTOMER",
        company_name=client_name,
        custom_suffix=client_account_suffix or None,
        vat_number=client_vat_number,
        country_code=client_country,
        is_company=(client_type == "ENTREPRISE"),
    )

    final_reference = line_reference.strip()

    if partner.account_number:
        final_reference = (
            f"{partner.account_number} - {final_reference}"
            if final_reference
            else partner.account_number
        )

    try:
        invoice_id = create_zzp_invoice(
            client_name=client_name,
            client_country=client_country,
            designation=designation,
            unit_price=unit_price,
            quantity=quantity,
            amount_type=amount_type,
            client_type=client_type,
            client_vat_number=client_vat_number,
            line_reference=final_reference,
            invoice_date=invoice_date,
            due_date=due_date,
            discount=discount,
            shipping=shipping,
            language=lang,
        )

        partner_type = "B2B" if client_type == "ENTREPRISE" else "B2C"

        expected_vat_rate = 0.21

        if client_country != "NL" and partner_type == "B2B" and client_vat_number:
            expected_vat_rate = 0.0

        if client_country == "CM":
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
            language=lang,
        )

        invoice_data = {
            "invoice_id": invoice_id,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "client_type": client_type,
            "line_reference": final_reference,
            "designation": designation,
            "unit_price": unit_price,
            "quantity": quantity,
            "amount_type": amount_type,
            "discount": discount,
            "shipping": shipping,
            "legal_mentions": legal_mention_texts,
        }

        st.success("Invoice created successfully.")
        st.info(f"Invoice ID : {invoice_id}")
        st.caption(f"Client account number: {partner.account_number}")

        render_invoice_preview(
            company_profile=get_company_profile(),
            partner=partner,
            invoice_data=invoice_data,
        )

    except Exception as exc:
        st.error(f"Unable to create invoice: {exc}")
