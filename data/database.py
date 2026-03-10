import os
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL est introuvable dans les variables d'environnement.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_conn():
    return get_connection()


def column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cur.fetchone() is not None


def add_column_if_missing(cur, table_name: str, column_name: str, column_sql: str):
    if not column_exists(cur, table_name, column_name):
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # -------------------------
    # USERS
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            phone TEXT UNIQUE NOT NULL,
            name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -------------------------
    # SETTINGS
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # -------------------------
    # ORDERS (base minimale)
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            order_code TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -------------------------
    # Migration progressive ORDERS
    # -------------------------
    add_column_if_missing(cur, "orders", "user_id", "INTEGER")
    add_column_if_missing(cur, "orders", "site_name", "TEXT")
    add_column_if_missing(cur, "orders", "product_url", "TEXT")
    add_column_if_missing(cur, "orders", "product_title", "TEXT")
    add_column_if_missing(cur, "orders", "product_name", "TEXT")
    add_column_if_missing(cur, "orders", "product_specs", "TEXT")
    add_column_if_missing(cur, "orders", "product_price_eur", "DOUBLE PRECISION DEFAULT 0")
    add_column_if_missing(cur, "orders", "shipping_estimate_eur", "DOUBLE PRECISION DEFAULT 0")
    add_column_if_missing(cur, "orders", "total_to_pay_eur", "DOUBLE PRECISION DEFAULT 0")
    add_column_if_missing(cur, "orders", "total_xaf", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "orders", "seller_fee_xaf", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "orders", "afripay_fee_xaf", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "orders", "delivery_address", "TEXT")
    add_column_if_missing(cur, "orders", "momo_provider", "TEXT")
    add_column_if_missing(cur, "orders", "order_status", "TEXT DEFAULT 'CREEE'")
    add_column_if_missing(cur, "orders", "payment_status", "TEXT DEFAULT 'EN_ATTENTE'")
    add_column_if_missing(cur, "orders", "merchant_status", "TEXT")
    add_column_if_missing(cur, "orders", "merchant_order_number", "TEXT")
    add_column_if_missing(cur, "orders", "merchant_confirmation_url", "TEXT")
    add_column_if_missing(cur, "orders", "merchant_tracking_url", "TEXT")
    add_column_if_missing(cur, "orders", "merchant_purchase_date", "TEXT")

    conn.commit()
    cur.close()
    conn.close()