from datetime import datetime, timezone


APP_NAME = "AfriPay Afrika"
APP_TITLE = "AfriPay Afrika - Facilitateur des paiements internationaux"
APP_TAGLINE = "Facilitateur des paiements internationaux"

DEFAULT_CURRENCY_XAF = "XAF"
DEFAULT_CURRENCY_EUR = "EUR"

DEFAULT_EUR_XAF_RATE = 655.957

ORDER_STATUS_DEFAULT = "CREEE"
PAYMENT_STATUS_DEFAULT = "EN_ATTENTE"


def now_utc():
    """
    Retourne la date/heure UTC actuelle.
    """
    return datetime.now(timezone.utc)


def now_iso():
    """
    Retourne une date/heure ISO propre en UTC.
    Exemple :
    2026-03-08T12:30:45+00:00
    """
    return now_utc().isoformat()


def today_iso():
    """
    Retourne la date du jour au format ISO.
    Exemple :
    2026-03-08
    """
    return now_utc().date().isoformat()