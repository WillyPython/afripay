import base64
import hashlib
import hmac
import os

import streamlit as st

from data.database import get_conn


DEFAULT_EUR_XAF_RATE = "655.957"
DEFAULT_ADMIN_PASSWORD = "Afripay2026!"


def pbkdf2_hash_password(password, salt=None, iterations=120_000):
    password = str(password or "")

    if salt is None:
        salt = os.urandom(16)

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
    )

    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(dk).decode("utf-8")

    return f"pbkdf2_sha256${int(iterations)}${salt_b64}${hash_b64}"


def pbkdf2_verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_b64, hash_b64 = str(stored_hash).split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected_hash = base64.b64decode(hash_b64.encode("utf-8"))

        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(candidate_hash, expected_hash)
    except Exception:
        return False


def get_secret_admin_password():
    """
    Priorité :
    1) variable d'environnement Render
    2) Streamlit secrets
    3) valeur par défaut
    """
    env_value = os.getenv("ADMIN_PASSWORD")
    if env_value:
        return str(env_value)

    try:
        secret_value = st.secrets.get("ADMIN_PASSWORD")
        if secret_value:
            return str(secret_value)
    except Exception:
        pass

    return DEFAULT_ADMIN_PASSWORD


def ensure_admin_settings_table():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def get_setting(key, default=None):
    ensure_admin_settings_table()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key = %s LIMIT 1",
        (str(key),),
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

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
    ensure_admin_settings_table()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO settings(key, value)
        VALUES(%s, %s)
        ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value
        """,
        (str(key), str(value)),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_admin_hash():
    return get_setting("admin_password_hash", None)


def set_admin_password(new_password):
    new_hash = pbkdf2_hash_password(str(new_password or ""))
    set_setting("admin_password_hash", new_hash)
    return new_hash


def ensure_defaults():
    """
    Initialise :
    - taux EUR/XAF
    - hash admin
    - met à jour le hash si ADMIN_PASSWORD existe mais qu'aucun hash n'est stocké
    """
    ensure_admin_settings_table()

    current_rate = get_setting("eur_xaf_rate", None)
    if not current_rate:
        set_setting("eur_xaf_rate", DEFAULT_EUR_XAF_RATE)

    current_admin_hash = get_admin_hash()
    if not current_admin_hash:
        admin_password = get_secret_admin_password()
        set_setting("admin_password_hash", pbkdf2_hash_password(admin_password))


def get_stats():
    conn = get_conn()
    cur = conn.cursor()

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

    cur.close()
    conn.close()

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