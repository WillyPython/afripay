import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "afripay.db"


def get_conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cur, table_name, column_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = cur.fetchall()

    for col in columns:
        try:
            if col["name"] == column_name:
                return True
        except Exception:
            if len(col) > 1 and col[1] == column_name:
                return True

    return False


def _ensure_column(cur, table_name, column_name, column_sql):
    if not _column_exists(cur, table_name, column_name):
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    cur = conn.cursor()

    # =========================
    # TABLE USERS
    # =========================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL UNIQUE,
            name TEXT,
            email TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    # =========================
    # TABLE ORDERS
    # =========================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,

            order_code TEXT UNIQUE,

            site_name TEXT,
            product_url TEXT,
            product_title TEXT,
            product_specs TEXT,
            product_image_path TEXT,

            product_price_eur REAL DEFAULT 0,
            shipping_estimate_eur REAL DEFAULT 0,
            commission_eur REAL DEFAULT 0,
            total_to_pay_eur REAL DEFAULT 0,
            eur_xaf_rate_used REAL DEFAULT 0,
            total_to_pay_xaf REAL DEFAULT 0,

            seller_fee_xaf REAL DEFAULT 0,
            afripay_fee_xaf REAL DEFAULT 0,
            total_xaf REAL DEFAULT 0,

            delivery_address TEXT,
            client_ack INTEGER DEFAULT 0,

            payment_reference TEXT,
            payment_status TEXT DEFAULT 'EN_ATTENTE',
            momo_provider TEXT,
            momo_tx_id TEXT,
            payment_proof_path TEXT,
            purchase_proof_path TEXT,

            tracking_number TEXT,
            tracking_url TEXT,
            order_status TEXT DEFAULT 'CREEE',

            merchant_order_number TEXT,
            merchant_confirmation_url TEXT,
            merchant_tracking_url TEXT,
            merchant_purchase_date TEXT,
            merchant_status TEXT,

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    # =========================
    # TABLE SETTINGS
    # =========================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    # =========================
    # MIGRATIONS DE SÉCURITÉ
    # =========================

    # USERS
    _ensure_column(cur, "users", "name", "TEXT")
    _ensure_column(cur, "users", "email", "TEXT")
    _ensure_column(cur, "users", "created_at", "TEXT NOT NULL DEFAULT ''")

    # ORDERS - champs principaux
    _ensure_column(cur, "orders", "order_code", "TEXT")
    _ensure_column(cur, "orders", "site_name", "TEXT")
    _ensure_column(cur, "orders", "product_url", "TEXT")
    _ensure_column(cur, "orders", "product_title", "TEXT")
    _ensure_column(cur, "orders", "product_specs", "TEXT")
    _ensure_column(cur, "orders", "product_image_path", "TEXT")

    # ORDERS - devise EUR
    _ensure_column(cur, "orders", "product_price_eur", "REAL DEFAULT 0")
    _ensure_column(cur, "orders", "shipping_estimate_eur", "REAL DEFAULT 0")
    _ensure_column(cur, "orders", "commission_eur", "REAL DEFAULT 0")
    _ensure_column(cur, "orders", "total_to_pay_eur", "REAL DEFAULT 0")
    _ensure_column(cur, "orders", "eur_xaf_rate_used", "REAL DEFAULT 0")
    _ensure_column(cur, "orders", "total_to_pay_xaf", "REAL DEFAULT 0")

    # ORDERS - devise XAF
    _ensure_column(cur, "orders", "seller_fee_xaf", "REAL DEFAULT 0")
    _ensure_column(cur, "orders", "afripay_fee_xaf", "REAL DEFAULT 0")
    _ensure_column(cur, "orders", "total_xaf", "REAL DEFAULT 0")

    # ORDERS - client / paiement / logistique
    _ensure_column(cur, "orders", "delivery_address", "TEXT")
    _ensure_column(cur, "orders", "client_ack", "INTEGER DEFAULT 0")
    _ensure_column(cur, "orders", "payment_reference", "TEXT")
    _ensure_column(cur, "orders", "payment_status", "TEXT DEFAULT 'EN_ATTENTE'")
    _ensure_column(cur, "orders", "momo_provider", "TEXT")
    _ensure_column(cur, "orders", "momo_tx_id", "TEXT")
    _ensure_column(cur, "orders", "payment_proof_path", "TEXT")
    _ensure_column(cur, "orders", "purchase_proof_path", "TEXT")
    _ensure_column(cur, "orders", "tracking_number", "TEXT")
    _ensure_column(cur, "orders", "tracking_url", "TEXT")
    _ensure_column(cur, "orders", "order_status", "TEXT DEFAULT 'CREEE'")

    # ORDERS - infos marchand
    _ensure_column(cur, "orders", "merchant_order_number", "TEXT")
    _ensure_column(cur, "orders", "merchant_confirmation_url", "TEXT")
    _ensure_column(cur, "orders", "merchant_tracking_url", "TEXT")
    _ensure_column(cur, "orders", "merchant_purchase_date", "TEXT")
    _ensure_column(cur, "orders", "merchant_status", "TEXT")

    # ORDERS - dates
    _ensure_column(cur, "orders", "created_at", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(cur, "orders", "updated_at", "TEXT NOT NULL DEFAULT ''")

    # =========================
    # INDEXES
    # =========================
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_order_code ON orders(order_code)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_order_status ON orders(order_status)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)"
    )

    conn.commit()
    conn.close()