from data.database import (
    get_cursor,
    get_setting_value_db,
    set_setting_value_db,
)


# =========================
# TABLE SETTINGS
# =========================
def ensure_settings_table():
    """
    Garantit l'existence de la table settings.
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )


# =========================
# LECTURE / ECRITURE
# =========================
def get_setting(key: str, default=None):
    """
    Lit une valeur depuis settings.
    """
    value = get_setting_value_db(key, default if default is not None else "")
    if value == "" and default is not None:
        return default
    return value


def set_setting(key: str, value: str):
    """
    Crée ou met à jour une clé settings.
    """
    return set_setting_value_db(key, value)


# =========================
# HELPERS DEFAULTS
# =========================
def ensure_default_setting(key: str, value: str):
    """
    Insère une valeur par défaut uniquement si la clé n'existe pas encore.
    """
    existing = get_setting(key, None)
    if existing is None:
        set_setting(key, value)


def ensure_defaults():
    """
    Prépare les paramètres minimums nécessaires à l'application.
    Ne remplace jamais une valeur déjà configurée.
    """
    ensure_settings_table()

    defaults = {
        # Branding / app
        "app_name": "AfriPay Afrika",
        "brand_name": "AfriPay Afrika",

        # Pays / devise
        "default_country_code": "CM",
        "eur_xaf_rate": "655.957",

        # Compatibilité ancienne clé
        "exchange_rate_eur_xaf": "655.957",

        # Frais
        "service_fee_percent": "20",

        # WhatsApp / support
        # Valeurs vides par défaut : architecture propre, pas de numéro en dur.
        "support_whatsapp_number": "",
        "whatsapp_default": "",
        "whatsapp_number_cm": "",

        # Admin
        "admin_password": "",
    }

    for key, value in defaults.items():
        ensure_default_setting(key, value)
        