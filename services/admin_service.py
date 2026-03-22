import hmac

from config.settings import get_admin_password
from data.database import get_cursor


DEFAULT_EUR_XAF_RATE = "655.957"


def admin_is_configured():
    """
    Retourne True si ADMIN_PASSWORD est bien défini dans l'environnement.
    """
    return get_admin_password() != ""


def verify_admin_password(password):
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
    ensure_settings_table()

    with get_cursor() as cur:
        cur.execute(
            "SELECT value FROM settings WHERE key = %s LIMIT 1",
            (str(key),),
        )
        row = cur.fetchone()

    if not row:
        return default

    try:
        return row["value"]
    except Exception:
        try:
            return row[0]
        except Exception:
            return default


def set_setting(key, value):
    ensure_settings_table()

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO settings(key, value)
            VALUES(%s, %s)
            ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value
            """,
            (str(key), str(value)),
        )


def ensure_defaults():
    """
    Initialise uniquement les réglages généraux nécessaires.
    L'admin est géré directement par ADMIN_PASSWORD dans l'environnement.
    """
    ensure_settings_table()

    current_rate = get_setting("eur_xaf_rate", None)
    if not current_rate:
        set_setting("eur_xaf_rate", DEFAULT_EUR_XAF_RATE)


def get_stats():
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total_users FROM users")
        users_row = cur.fetchone()
        total_users = int(users_row["total_users"]) if users_row else 0

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
            "total_volume_xaf": 0,
            "total_volume_eur": 0.0,
        }

    return {
        "total_users": total_users,
        "total_orders": int(row["total_orders"] or 0),
        "paid_orders": int(row["paid_orders"] or 0),
        "in_progress_orders": int(row["in_progress_orders"] or 0),
        "delivered_orders": int(row["delivered_orders"] or 0),
        "cancelled_orders": int(row["cancelled_orders"] or 0),
        "total_volume_xaf": float(row["total_volume_xaf"] or 0),
        "total_volume_eur": float(row["total_volume_eur"] or 0.0),
    }