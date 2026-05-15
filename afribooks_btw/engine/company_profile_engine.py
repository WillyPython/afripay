from dataclasses import dataclass


@dataclass
class CompanyProfile:
    company_name: str
    trade_name: str
    kvk_number: str
    btw_number: str
    iban: str
    bic: str
    address: str
    postal_code: str
    city: str
    country: str

    email: str
    phone: str
    website: str

    logo_path: str

    invoice_footer: str

    preferred_language: str
    preferred_currency: str
    fiscal_periodicity: str


def create_company_profile(
    company_name: str,
    trade_name: str = "",
    kvk_number: str = "",
    btw_number: str = "",
    iban: str = "",
    bic: str = "",
    address: str = "",
    postal_code: str = "",
    city: str = "",
    country: str = "NL",
    email: str = "",
    phone: str = "",
    website: str = "",
    logo_path: str = "",
    invoice_footer: str = "",
    preferred_language: str = "nl",
    preferred_currency: str = "EUR",
    fiscal_periodicity: str = "QUARTERLY",
) -> CompanyProfile:
    return CompanyProfile(
        company_name=company_name.strip(),
        trade_name=trade_name.strip(),
        kvk_number=kvk_number.strip(),
        btw_number=btw_number.strip(),
        iban=iban.strip(),
        bic=bic.strip(),
        address=address.strip(),
        postal_code=postal_code.strip(),
        city=city.strip(),
        country=country.strip().upper(),
        email=email.strip(),
        phone=phone.strip(),
        website=website.strip(),
        logo_path=logo_path.strip(),
        invoice_footer=invoice_footer.strip(),
        preferred_language=preferred_language.strip().lower(),
        preferred_currency=preferred_currency.strip().upper(),
        fiscal_periodicity=fiscal_periodicity.strip().upper(),
    )
