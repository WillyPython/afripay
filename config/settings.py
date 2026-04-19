import os


def _clean_env(value: str | None) -> str:
    """
    Nettoie une variable d'environnement :
    - None -> ""
    - supprime les espaces en début/fin
    """
    if value is None:
        return ""
    return value.strip()


# =========================================================
# IDENTITÉ PRODUIT / ENTREPRISE
# =========================================================
APP_NAME = "AfriPay Afrika"
APP_TITLE = APP_NAME
APP_TAGLINE = "Paiements internationaux simplifiés pour l'Afrique"

PARENT_COMPANY_NAME = "AfriDIGID"
PARENT_DOMAIN = "afridigid.io"
COMPANY_KVK = "42034307"
COMPANY_VAT_ID = "NL005445291B55"

COMPANY_EMAIL_OFFICE = "office@afridigid.io"
COMPANY_EMAIL_SUPPORT = "support@afridigid.io"


# =========================================================
# CONSTANTES GLOBALES APP
# =========================================================
DEFAULT_EUR_TO_XAF_RATE = 655.957
SESSION_DURATION_DAYS = 30
DEFAULT_COUNTRY_CODE = "CM"
DEFAULT_LANGUAGE = "fr"


# =========================================================
# ENVIRONNEMENT
# =========================================================
def get_app_env() -> str:
    """
    Retourne l'environnement applicatif normalisé.
    """
    value = _clean_env(os.getenv("APP_ENV", "production")).lower()
    return value or "production"


def is_production() -> bool:
    """
    Retourne True si l'application tourne en production.
    """
    return get_app_env() == "production"


# =========================================================
# VARIABLES D'ENVIRONNEMENT
# =========================================================
def get_database_url() -> str:
    """
    Retourne DATABASE_URL nettoyé.
    """
    return _clean_env(os.getenv("DATABASE_URL"))


def get_admin_password() -> str:
    """
    Retourne ADMIN_PASSWORD nettoyé.
    """
    return _clean_env(os.getenv("ADMIN_PASSWORD"))


def is_admin_configured() -> bool:
    """
    Retourne True si le mot de passe admin est bien défini.
    """
    return get_admin_password() != ""


# =========================================================
# HELPERS BRANDING / LÉGAL
# =========================================================
def get_company_identity() -> dict:
    """
    Retourne l'identité entreprise structurée pour affichage.
    """
    return {
        "app_name": APP_NAME,
        "app_title": APP_TITLE,
        "app_tagline": APP_TAGLINE,
        "parent_company_name": PARENT_COMPANY_NAME,
        "parent_domain": PARENT_DOMAIN,
        "company_kvk": COMPANY_KVK,
        "company_vat_id": COMPANY_VAT_ID,
        "company_email_office": COMPANY_EMAIL_OFFICE,
        "company_email_support": COMPANY_EMAIL_SUPPORT,
    }


def get_support_email() -> str:
    """
    Retourne l'email principal de support.
    """
    return COMPANY_EMAIL_SUPPORT


def get_office_email() -> str:
    """
    Retourne l'email principal administratif.
    """
    return COMPANY_EMAIL_OFFICE
