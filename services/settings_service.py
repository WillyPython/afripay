from data.database import get_conn


def ensure_settings_table():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def get_setting(key: str, default=None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key = %s LIMIT 1",
        (key,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        if isinstance(row, dict):
            return row.get("value", default)
        return row[0]

    return default


def set_setting(key: str, value: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM settings WHERE key = %s LIMIT 1",
        (key,)
    )
    row = cur.fetchone()

    if row:
        cur.execute(
            "UPDATE settings SET value = %s WHERE key = %s",
            (value, key)
        )
    else:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (%s, %s)",
            (key, value)
        )

    conn.commit()
    cur.close()
    conn.close()


def ensure_defaults():
    ensure_settings_table()

    defaults = {
        "exchange_rate_eur_xaf": "655",
        "service_fee_percent": "0",
        "app_name": "AfriPay Afrika",
    }

    for key, value in defaults.items():
        existing = get_setting(key)
        if existing is None:
            set_setting(key, value)