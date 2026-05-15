import streamlit as st
from pathlib import Path

from afribooks_btw.engine.company_profile_engine import create_company_profile
from afribooks_btw.engine.fiscal_profile_engine import build_fiscal_profile
from afribooks_btw.engine.session_service import (
    get_afribooks_language,
    set_afribooks_language,
    set_company_profile,
    set_fiscal_profile,
)


LABELS = {
    "nl": {
        "title": "Bedrijfsprofiel",
        "caption": "Configureer uw bedrijfsgegevens, logo, factuurgegevens, taal, valuta en BTW-periode.",
        "language_first": "Taal",
        "identity": "Bedrijfsidentiteit",
        "legal_name": "Officiele bedrijfsnaam",
        "trade_name": "Handelsnaam",
        "kvk": "KvK-nummer",
        "vat": "BTW-nummer",
        "contact": "Contact en adres",
        "email": "E-mail",
        "phone": "Telefoon",
        "website": "Website",
        "address": "Adres",
        "postal_code": "Postcode",
        "city": "Stad",
        "country": "Fiscaal land",
        "banking": "Bankgegevens",
        "branding": "Factuurbranding",
        "upload_logo": "Bedrijfslogo uploaden",
        "upload_logo_title": "Bedrijfslogo toevoegen",
        "upload_logo_help": "Sleep uw logo in het uploadvak hieronder of klik op Browse files. PNG, JPG of JPEG.",
        "upload_logo_secure": "Uw logo wordt alleen gebruikt voor uw facturen en bedrijfsdocumenten.",
        "footer": "Factuurvoet",
        "footer_placeholder": "Voorbeeld: Bedankt voor uw vertrouwen.",
        "preferences": "Fiscale voorkeuren",
        "currency": "Valuta",
        "periodicity": "BTW-periode",
        "save": "Bedrijfsprofiel opslaan",
        "required": "Officiele bedrijfsnaam is verplicht.",
        "saved": "Bedrijfsprofiel opgeslagen.",
        "logo_ok": "Bedrijfslogo succesvol geupload.",
        "generated": "Fiscaal profiel gegenereerd",
        "technical_company": "Technisch bedrijfsprofiel",
        "technical_fiscal": "Technisch fiscaal profiel",
    },
    "fr": {
        "title": "Profil de l'entreprise",
        "caption": "Configurez l'identite, le logo, les donnees fiscales, les factures, la langue, la devise et la periode TVA.",
        "language_first": "Langue",
        "identity": "Identite de l'entreprise",
        "legal_name": "Nom legal de l'entreprise",
        "trade_name": "Nom commercial",
        "kvk": "Numero KvK",
        "vat": "Numero TVA",
        "contact": "Contact et adresse",
        "email": "E-mail",
        "phone": "Telephone",
        "website": "Site web",
        "address": "Adresse",
        "postal_code": "Code postal",
        "city": "Ville",
        "country": "Pays fiscal",
        "banking": "Coordonnees bancaires",
        "branding": "Presentation de la facture",
        "upload_logo": "Ajouter le logo de l'entreprise",
        "upload_logo_title": "Ajouter le logo de votre entreprise",
        "upload_logo_help": "Glissez votre logo dans la zone de telechargement ci-dessous ou cliquez sur Browse files. PNG, JPG ou JPEG.",
        "upload_logo_secure": "Votre logo sera utilise uniquement pour vos factures et documents professionnels.",
        "footer": "Pied de facture",
        "footer_placeholder": "Exemple : Merci pour votre confiance.",
        "preferences": "Preferences fiscales",
        "currency": "Devise",
        "periodicity": "Periodicite TVA",
        "save": "Enregistrer le profil",
        "required": "Le nom legal de l'entreprise est obligatoire.",
        "saved": "Profil de l'entreprise enregistre.",
        "logo_ok": "Logo de l'entreprise ajoute avec succes.",
        "generated": "Profil fiscal genere",
        "technical_company": "Profil entreprise technique",
        "technical_fiscal": "Profil fiscal technique",
    },
    "en": {
        "title": "Company Profile",
        "caption": "Configure your company identity, logo, fiscal data, invoice details, language, currency and VAT period.",
        "language_first": "Language",
        "identity": "Company identity",
        "legal_name": "Legal company name",
        "trade_name": "Trade name",
        "kvk": "KvK number",
        "vat": "VAT number",
        "contact": "Contact and address",
        "email": "Email",
        "phone": "Phone",
        "website": "Website",
        "address": "Address",
        "postal_code": "Postal code",
        "city": "City",
        "country": "Fiscal country",
        "banking": "Banking",
        "branding": "Invoice branding",
        "upload_logo": "Upload company logo",
        "upload_logo_title": "Add your company logo",
        "upload_logo_help": "Drag your logo into the upload area below or click Browse files. PNG, JPG or JPEG.",
        "upload_logo_secure": "Your logo is only used for your invoices and business documents.",
        "footer": "Invoice footer",
        "footer_placeholder": "Example: Thank you for your business.",
        "preferences": "Fiscal preferences",
        "currency": "Currency",
        "periodicity": "VAT period",
        "save": "Save company profile",
        "required": "Legal company name is required.",
        "saved": "Company profile saved.",
        "logo_ok": "Company logo uploaded successfully.",
        "generated": "Fiscal profile generated",
        "technical_company": "Technical company profile",
        "technical_fiscal": "Technical fiscal profile",
    },
}

LANGUAGE_OPTIONS = {
    "nl": "NL · Nederlands",
    "fr": "FR · Français",
    "en": "EN · English",
}

PERIODICITY_LABELS = {
    "nl": {
        "MONTHLY": "Maandelijks",
        "QUARTERLY": "Per kwartaal",
        "ANNUAL": "Jaarlijks",
    },
    "fr": {
        "MONTHLY": "Mensuelle",
        "QUARTERLY": "Trimestrielle",
        "ANNUAL": "Annuelle",
    },
    "en": {
        "MONTHLY": "Monthly",
        "QUARTERLY": "Quarterly",
        "ANNUAL": "Annual",
    },
}


def format_language_label(language_code: str) -> str:
    return LANGUAGE_OPTIONS.get(language_code, language_code.upper())


def format_periodicity_label(periodicity: str, language_code: str) -> str:
    labels = PERIODICITY_LABELS.get(language_code, PERIODICITY_LABELS["nl"])
    return labels.get(periodicity, periodicity)


def render_language_badge(language_code: str) -> str:
    badges = {
        "nl": "NL · Nederlands",
        "fr": "FR · Français",
        "en": "EN · English",
    }
    return badges.get(language_code, language_code.upper())

def render_company_profile_ui() -> None:
    current_language = get_afribooks_language()

    selected_language = st.selectbox(
        "Language / Langue / Taal",
        ["nl", "fr", "en"],
        index=["nl", "fr", "en"].index(current_language)
        if current_language in ["nl", "fr", "en"]
        else 0,
        format_func=format_language_label,
        key="company_profile_language_selector",
    )

    set_afribooks_language(selected_language)

    labels = LABELS.get(selected_language, LABELS["nl"])

    language_badges_html = ""
    for code in ["nl", "fr", "en"]:
        is_active = code == selected_language
        background = "#111827" if is_active else "#f8fafc"
        color = "#ffffff" if is_active else "#374151"
        border = "#111827" if is_active else "#e5e7eb"

        language_badges_html += (
            f"<span style='display:inline-block;padding:7px 12px;margin-right:8px;"
            f"border-radius:999px;border:1px solid {border};background:{background};"
            f"color:{color};font-size:13px;font-weight:700;'>"
            f"{render_language_badge(code)}</span>"
        )

    st.markdown(
        f"<div style='margin:6px 0 14px 0;'>{language_badges_html}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"## {labels['title']}")
    st.caption(labels["caption"])

    logo_directory = (
        Path(__file__).resolve().parent / "assets" / "company_logo"
    )

    logo_directory.mkdir(parents=True, exist_ok=True)

    with st.form("company_profile_form"):
        st.markdown(f"### {labels['identity']}")

        company_name = st.text_input(labels["legal_name"])
        trade_name = st.text_input(labels["trade_name"])

        col_kvk, col_btw = st.columns(2)

        with col_kvk:
            kvk_number = st.text_input(labels["kvk"])

        with col_btw:
            btw_number = st.text_input(labels["vat"])

        st.markdown(f"### {labels['contact']}")

        col_email, col_phone = st.columns(2)

        with col_email:
            email = st.text_input(labels["email"])

        with col_phone:
            phone = st.text_input(labels["phone"])

        website = st.text_input(labels["website"])
        address = st.text_input(labels["address"])

        col_postal, col_city = st.columns(2)

        with col_postal:
            postal_code = st.text_input(labels["postal_code"])

        with col_city:
            city = st.text_input(labels["city"])

        country = st.selectbox(
            labels["country"],
            ["NL", "BE", "FR", "DE", "HU", "CM"],
            index=0,
        )

        st.markdown(f"### {labels['banking']}")

        col_iban, col_bic = st.columns(2)

        with col_iban:
            iban = st.text_input("IBAN")

        with col_bic:
            bic = st.text_input("BIC")

        st.markdown(f"### {labels['branding']}")

        st.markdown(
            f"""
            <div style="
                border: 1.5px dashed #d0d7de;
                border-radius: 18px;
                padding: 22px;
                background: linear-gradient(135deg, #f8fafc, #ffffff);
                text-align: center;
                margin-bottom: 12px;
            ">
                <div style="font-size: 34px; margin-bottom: 8px;">&#128188;</div>
                <div style="font-size: 18px; font-weight: 700; color: #111827;">
                    {labels["upload_logo_title"]}
                </div>
                <div style="font-size: 14px; color: #4b5563; margin-top: 6px;">
                    {labels["upload_logo_help"]}
                </div>
                <div style="font-size: 12px; color: #6b7280; margin-top: 10px;">
                    &#128274; {labels["upload_logo_secure"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_logo = st.file_uploader(
            labels["upload_logo"],
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
        )

        if uploaded_logo is not None:
            st.image(
                uploaded_logo,
                width=160,
                caption=labels["logo_ok"],
            )

        invoice_footer = st.text_area(
            labels["footer"],
            placeholder=labels["footer_placeholder"],
        )

        st.markdown(f"### {labels['preferences']}")

        col_currency, col_period = st.columns(2)

        with col_currency:
            preferred_currency = st.selectbox(
                labels["currency"],
                ["EUR", "XAF"],
                index=0,
            )

        with col_period:
            fiscal_periodicity = st.selectbox(
                labels["periodicity"],
                ["MONTHLY", "QUARTERLY", "ANNUAL"],
                index=1,
                format_func=lambda value: format_periodicity_label(
                    value,
                    selected_language,
                ),
            )

        submitted = st.form_submit_button(labels["save"])

    if not submitted:
        return

    if not company_name.strip():
        st.error(labels["required"])
        return

    logo_path = ""

    if uploaded_logo is not None:
        safe_company_name = (
            company_name.strip()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        logo_filename = f"{safe_company_name}_{uploaded_logo.name}"
        saved_logo_path = logo_directory / logo_filename

        with open(saved_logo_path, "wb") as f:
            f.write(uploaded_logo.getbuffer())

        logo_path = str(saved_logo_path)

    profile = create_company_profile(
        company_name=company_name,
        trade_name=trade_name,
        kvk_number=kvk_number,
        btw_number=btw_number,
        iban=iban,
        bic=bic,
        address=address,
        postal_code=postal_code,
        city=city,
        country=country,
        email=email,
        phone=phone,
        website=website,
        logo_path=logo_path,
        invoice_footer=invoice_footer,
        preferred_language=selected_language,
        preferred_currency=preferred_currency,
        fiscal_periodicity=fiscal_periodicity,
    )

    fiscal_profile = build_fiscal_profile(profile.__dict__)

    set_company_profile(profile)
    set_fiscal_profile(fiscal_profile)

    st.success(labels["saved"])

    if logo_path:
        st.image(
            logo_path,
            width=180,
            caption=labels["logo_ok"],
        )

    st.markdown(f"### {labels['generated']}")

    col_country, col_periodicity, col_language, col_currency = st.columns(4)

    with col_country:
        st.metric(labels["country"], fiscal_profile.fiscal_country)

    with col_periodicity:
        st.metric(labels["periodicity"], format_periodicity_label(fiscal_profile.fiscal_periodicity, selected_language))

    with col_language:
        st.metric(labels["language_first"], format_language_label(fiscal_profile.preferred_language))

    with col_currency:
        st.metric(labels["currency"], fiscal_profile.preferred_currency)

    with st.expander(labels["technical_company"]):
        st.json(profile.__dict__)

    with st.expander(labels["technical_fiscal"]):
        st.json(fiscal_profile.__dict__)



















