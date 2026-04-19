import hmac

from config.settings import get_admin_password
from data.database import (
    get_cursor,
    get_setting_value_db,
    set_setting_value_db,
)


DEFAULT_EUR_XAF_RATE = "655.957"


# ------------------------------
# AUTH ADMIN
# ------------------------------
def admin_is_configured() -> bool:
    """
    Retourne True si ADMIN_PASSWORD est bien défini.
    """
    return get_admin_password() != ""


def verify_admin_password(password) -> bool:
    """
    Vérifie le mot de passe admin saisi.
    """
    admin_password = get_admin_password()

    if admin_password == "":
        return False

    if password is None:
        return False

    provided_password = str(password).strip()
    return hmac.compare_digest(provided_password, admin_password)


# ------------------------------
# TABLE SETTINGS
# ------------------------------
def ensure_settings_table():
    """
    Garde-fou léger pour s'assurer que la table settings existe.
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


def get_setting(key, default=None):
    """
    Lit une valeur de configuration dans la table settings.
    Retourne default si la clé n'existe pas.
    """
    ensure_settings_table()

    value = get_setting_value_db(str(key), "" if default is None else str(default))

    if value == "" and default is not None:
        return default

    return value


def set_setting(key, value):
    """
    Crée ou met à jour une valeur de configuration.
    """
    ensure_settings_table()
    return set_setting_value_db(str(key), str(value))


def ensure_default_setting(key: str, value: str):
    """
    Insère une valeur par défaut seulement si la clé est absente.
    """
    existing = get_setting(key, None)
    if existing is None:
        set_setting(key, value)


def ensure_defaults():
    """
    Initialise uniquement les réglages généraux nécessaires.

    L'auth admin reste gérée par ADMIN_PASSWORD dans l'environnement.
    """
    ensure_settings_table()

    defaults = {
        "eur_xaf_rate": DEFAULT_EUR_XAF_RATE,
        "default_country_code": "CM",
        "brand_name": "AfriPay Afrika",

        # Compatibilité ancienne lecture éventuelle
        "exchange_rate_eur_xaf": DEFAULT_EUR_XAF_RATE,
        "app_name": "AfriPay Afrika",

        # WhatsApp / support
        "support_whatsapp_number": "",
        "whatsapp_default": "",
        "whatsapp_number_cm": "",
    }

    for key, value in defaults.items():
        ensure_default_setting(key, value)


# ------------------------------
# HELPERS STATS
# ------------------------------
def _safe_int(value, default=0):
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return float(default)


def _row_get(row, key, default=None):
    if not row:
        return default

    if isinstance(row, dict):
        return row.get(key, default)

    try:
        return row[key]
    except Exception:
        return default


# ------------------------------
# STATS ADMIN GLOBALES
# ------------------------------
def get_stats():
    """
    Retourne un résumé admin global simple.

    Notes métier :
    - total_volume_xaf : somme des total_xaf commandes
    - total_volume_eur : somme des total_to_pay_eur
    - paid_orders : commandes PAYEE
    - in_progress_orders : commandes EN_COURS
    - delivered_orders : commandes LIVREE
    - cancelled_orders : commandes ANNULEE
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS total_users
            FROM users
            """
        )
        users_row = cur.fetchone()
        total_users = _safe_int(_row_get(users_row, "total_users", 0))

        cur.execute(
            """
            SELECT
                COUNT(*) AS total_orders,
                SUM(CASE WHEN order_status = 'PAYEE' THEN 1 ELSE 0 END) AS paid_orders,
                SUM(CASE WHEN order_status = 'EN_COURS' THEN 1 ELSE 0 END) AS in_progress_orders,
                SUM(CASE WHEN order_status = 'LIVREE' THEN 1 ELSE 0 END) AS delivered_orders,
                SUM(CASE WHEN order_status = 'ANNULEE' THEN 1 ELSE 0 END) AS cancelled_orders,
                COALESCE(SUM(total_xaf), 0) AS total_volume_xaf,
                COALESCE(SUM(total_to_pay_eur), 0) AS total_volume_eur
            FROM orders
            """
        )
        row = cur.fetchone()

    if not row:
        return {
            "total_users": total_users,
            "total_orders": 0,
            "paid_orders": 0,
            "in_progress_orders": 0,
            "delivered_orders": 0,
            "cancelled_orders": 0,
            "total_volume_xaf": 0.0,
            "total_volume_eur": 0.0,
        }

    return {
        "total_users": total_users,
        "total_orders": _safe_int(_row_get(row, "total_orders", 0)),
        "paid_orders": _safe_int(_row_get(row, "paid_orders", 0)),
        "in_progress_orders": _safe_int(_row_get(row, "in_progress_orders", 0)),
        "delivered_orders": _safe_int(_row_get(row, "delivered_orders", 0)),
        "cancelled_orders": _safe_int(_row_get(row, "cancelled_orders", 0)),
        "total_volume_xaf": _safe_float(_row_get(row, "total_volume_xaf", 0)),
        "total_volume_eur": _safe_float(_row_get(row, "total_volume_eur", 0.0)),
    }
