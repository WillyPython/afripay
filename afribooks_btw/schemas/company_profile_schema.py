from dataclasses import dataclass


@dataclass
class CompanyProfileSchema:
    company_name: str
    kvk_number: str
    btw_number: str
    iban: str
    bic: str
    address: str
    postal_code: str
    city: str
    country: str
    preferred_language: str
    preferred_currency: str
    fiscal_periodicity: str
