import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# CONNEXION
# =========================
def get_connection():
    """
    Ouvre une connexion PostgreSQL.
    """
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL est introuvable dans les variables d'environnement."
        )

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
    )


def get_conn():
    """
    Alias historique utilisé dans le projet.
    """
    return get_connection()


@contextmanager
def get_cursor(commit: bool = False):
    """
    Gestion propre des connexions/curseurs.

    Usage:
        with get_cursor(commit=True) as cur:
            cur.execute(...)
    """
    conn = get_conn()
    cur = conn.cursor()

    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================
# OUTILS SCHEMA / MIGRATION
# =========================
def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = %s
        LIMIT 1
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


def column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cur.fetchone() is not None


def add_column_if_missing(cur, table_name: str, column_name: str, column_sql: str):
    """
    Ajoute une colonne si elle n'existe pas déjà.
    """
    if not column_exists(cur, table_name, column_name):
        cur.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
        )


def index_exists(cur, index_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname = %s
        LIMIT 1
        """,
        (index_name,),
    )
    return cur.fetchone() is not None


def add_index_if_missing(cur, index_name: str, table_name: str, columns_sql: str):
    """
    Ajoute un index simple si absent.
    Exemple columns_sql: "(user_id)"
    """
    if not index_exists(cur, index_name):
        cur.execute(
            f"CREATE INDEX {index_name} ON {table_name} {columns_sql}"
        )


# =========================
# INITIALISATION BASE
# =========================
def init_db():
    """
    Initialise les tables principales et applique les migrations progressives.
    """
    conn = get_conn()
    cur = conn.cursor()

    try:
        # -------------------------
        # USERS
        # -------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                phone TEXT UNIQUE NOT NULL,
                name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # -------------------------
        # SETTINGS
        # -------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )

        # -------------------------
        # ORDERS (base minimale)
        # -------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # -------------------------
        # MIGRATION PROGRESSIVE ORDERS
        # -------------------------
        add_column_if_missing(cur, "orders", "order_code", "TEXT")
        add_column_if_missing(cur, "orders", "user_id", "INTEGER")
        add_column_if_missing(cur, "orders", "country_code", "TEXT DEFAULT 'CM'")
        add_column_if_missing(cur, "orders", "site_name", "TEXT")
        add_column_if_missing(cur, "orders", "product_url", "TEXT")
        add_column_if_missing(cur, "orders", "product_title", "TEXT")
        add_column_if_missing(cur, "orders", "product_name", "TEXT")
        add_column_if_missing(cur, "orders", "product_specs", "TEXT")

        # montant d'origine marchand / multi-devise
        add_column_if_missing(
            cur,
            "orders",
            "merchant_total_amount",
            "DOUBLE PRECISION DEFAULT 0"
        )
        add_column_if_missing(
            cur,
            "orders",
            "merchant_currency",
            "TEXT DEFAULT 'EUR'"
        )

        # ancien modèle encore toléré
        add_column_if_missing(
            cur,
            "orders",
            "product_price_eur",
            "DOUBLE PRECISION DEFAULT 0"
        )
        add_column_if_missing(
            cur,
            "orders",
            "shipping_estimate_eur",
            "DOUBLE PRECISION DEFAULT 0"
        )

        # modèle métier AfriPay
        add_column_if_missing(
            cur,
            "orders",
            "total_to_pay_eur",
            "DOUBLE PRECISION DEFAULT 0"
        )
        add_column_if_missing(cur, "orders", "total_xaf", "INTEGER DEFAULT 0")
        add_column_if_missing(cur, "orders", "seller_fee_xaf", "INTEGER DEFAULT 0")
        add_column_if_missing(cur, "orders", "afripay_fee_xaf", "INTEGER DEFAULT 0")

        add_column_if_missing(cur, "orders", "delivery_address", "TEXT")
        add_column_if_missing(cur, "orders", "momo_provider", "TEXT")
        add_column_if_missing(cur, "orders", "order_status", "TEXT DEFAULT 'CREEE'")
        add_column_if_missing(
            cur,
            "orders",
            "payment_status",
            "TEXT DEFAULT 'EN_ATTENTE'"
        )

        # tracking marchand
        add_column_if_missing(cur, "orders", "merchant_status", "TEXT")
        add_column_if_missing(cur, "orders", "merchant_order_number", "TEXT")
        add_column_if_missing(cur, "orders", "merchant_confirmation_url", "TEXT")
        add_column_if_missing(cur, "orders", "merchant_tracking_url", "TEXT")
        add_column_if_missing(cur, "orders", "merchant_purchase_date", "TEXT")
        add_column_if_missing(cur, "orders", "merchant_notes", "TEXT")
        add_column_if_missing(
            cur,
            "orders",
            "updated_at",
            "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )

        # préparation règles AfriPay métier
        add_column_if_missing(cur, "orders", "freight_forwarder_name", "TEXT")
        add_column_if_missing(cur, "orders", "freight_forwarder_address", "TEXT")
        add_column_if_missing(cur, "orders", "merchant_delivery_address", "TEXT")

        # -------------------------
        # NORMALISATION DONNEES EXISTANTES
        # -------------------------
        cur.execute(
            """
            UPDATE orders
            SET product_name = product_title
            WHERE (product_name IS NULL OR TRIM(product_name) = '')
              AND product_title IS NOT NULL
              AND TRIM(product_title) <> ''
            """
        )

        cur.execute(
            """
            UPDATE orders
            SET merchant_total_amount = total_to_pay_eur
            WHERE (merchant_total_amount IS NULL OR merchant_total_amount = 0)
              AND total_to_pay_eur IS NOT NULL
              AND total_to_pay_eur > 0
            """
        )

        cur.execute(
            """
            UPDATE orders
            SET merchant_currency = 'EUR'
            WHERE merchant_currency IS NULL
               OR TRIM(merchant_currency) = ''
            """
        )

        cur.execute(
            """
            UPDATE orders
            SET updated_at = created_at
            WHERE updated_at IS NULL
            """
        )

        # -------------------------
        # CONTRAINTE UNIQUE order_code
        # -------------------------
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'orders_order_code_key'
                ) THEN
                    BEGIN
                        ALTER TABLE orders
                        ADD CONSTRAINT orders_order_code_key UNIQUE (order_code);
                    EXCEPTION
                        WHEN duplicate_object THEN
                            NULL;
                    END;
                END IF;
            END
            $$;
            """
        )

        # -------------------------
        # INDEX ORDERS
        # -------------------------
        add_index_if_missing(cur, "idx_orders_user_id", "orders", "(user_id)")
        add_index_if_missing(cur, "idx_orders_order_code", "orders", "(order_code)")
        add_index_if_missing(cur, "idx_orders_order_status", "orders", "(order_status)")
        add_index_if_missing(cur, "idx_orders_payment_status", "orders", "(payment_status)")
        add_index_if_missing(cur, "idx_orders_created_at", "orders", "(created_at)")
        add_index_if_missing(cur, "idx_orders_country_code", "orders", "(country_code)")
        add_index_if_missing(cur, "idx_orders_merchant_status", "orders", "(merchant_status)")
        add_index_if_missing(cur, "idx_orders_merchant_currency", "orders", "(merchant_currency)")

        # -------------------------
        # USER SESSIONS
        # -------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_token TEXT NOT NULL UNIQUE,
                phone TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        add_index_if_missing(cur, "idx_user_sessions_user_id", "user_sessions", "(user_id)")
        add_index_if_missing(cur, "idx_user_sessions_token", "user_sessions", "(session_token)")
        add_index_if_missing(cur, "idx_user_sessions_active", "user_sessions", "(is_active)")

        # -------------------------
        # ACTION LOGS
        # -------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS action_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                actor_type TEXT,
                action_type TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                description TEXT,
                meta_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        add_index_if_missing(cur, "idx_action_logs_user_id", "action_logs", "(user_id)")
        add_index_if_missing(cur, "idx_action_logs_action_type", "action_logs", "(action_type)")
        add_index_if_missing(cur, "idx_action_logs_created_at", "action_logs", "(created_at)")

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()