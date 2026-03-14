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

APP_ENV = _clean_env(os.getenv("APP_ENV", "production"))
DATABASE_URL = _clean_env(os.getenv("DATABASE_URL"))
ADMIN_PASSWORD = _clean_env(os.getenv("ADMIN_PASSWORD"))

DEFAULT_EUR_TO_XAF_RATE = 655.957
SESSION_DURATION_DAYS = 30


def is_admin_configured() -> bool:
    """
    Retourne True si le mot de passe admin est bien défini.
    """
    return ADMIN_PASSWORD != ""