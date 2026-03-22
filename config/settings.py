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


APP_NAME = "AfriPay Afrika"
APP_TITLE = APP_NAME
APP_TAGLINE = "Paiements internationaux simplifiés pour l'Afrique"

DEFAULT_EUR_TO_XAF_RATE = 655.957
SESSION_DURATION_DAYS = 30


def get_app_env() -> str:
    """
    Retourne l'environnement applicatif normalisé.
    """
    value = _clean_env(os.getenv("APP_ENV", "production")).lower()
    return value or "production"


def is_production() -> bool:
    return get_app_env() == "production"


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