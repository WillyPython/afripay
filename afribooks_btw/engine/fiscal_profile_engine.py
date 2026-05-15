from dataclasses import dataclass
from typing import Any


@dataclass
class FiscalProfile:
    fiscal_country: str
    fiscal_periodicity: str
    preferred_language: str
    preferred_currency: str


def build_fiscal_profile(company_profile: dict[str, Any]) -> FiscalProfile:
    return FiscalProfile(
        fiscal_country=str(company_profile.get("country", "NL")).strip().upper(),
        fiscal_periodicity=str(company_profile.get("fiscal_periodicity", "QUARTERLY")).strip().upper(),
        preferred_language=str(company_profile.get("preferred_language", "nl")).strip().lower(),
        preferred_currency=str(company_profile.get("preferred_currency", "EUR")).strip().upper(),
    )
