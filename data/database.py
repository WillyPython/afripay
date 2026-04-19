import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


# =========================
# CONFIG / CONNEXION
# =========================
def get_database_url() -> str:
    """
    Récupère DATABASE_URL depuis les variables d'environnement.
    """
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL est introuvable dans les variables d'environnement."
        )

    return database_url


def get_connection():
    """
    Ouvre une connexion PostgreSQL.
    """
    return psycopg2.connect(
        get_database_url(),
        cursor_factory=RealDictCursor,
        connect_timeout=5,
        sslmode="require",
    )


def get_conn():
    """
    Retourne une connexion PostgreSQL ou lève une erreur métier claire.
    """
    try:
        return get_connection()
    except Exception as e:
        print("❌ Erreur connexion DB :", e)
        raise RuntimeError("Connexion DB indisponible") from e


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


def constraint_exists(cur, constraint_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND constraint_name = %s
        LIMIT 1
        """,
        (constraint_name,),
    )
    return cur.fetchone() is not None


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


def add_column_if_missing(cur, table_name: str, column_name: str, column_sql: str):
    """
    Ajoute une colonne si elle n'existe pas déjà.
    """
    if not column_exists(cur, table_name, column_name):
        cur.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
        )


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
# HELPERS SETTINGS
# =========================
def get_setting_value_db(key: str, default: str = "") -> str:
    """
    Lit une valeur dans la table settings.
    """
    key = str(key or "").strip()
    if not key:
        return default

    try:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT value
                FROM settings
                WHERE key = %s
                LIMIT 1
                """,
                (key,),
            )
            row = cur.fetchone()
            if not row:
                return default

            if isinstance(row, dict):
                value = row.get("value", default)
            else:
                value = row[0] if row[0] is not None else default

            return str(value or "").strip()
    except Exception:
        return default


def set_setting_value_db(key: str, value: str) -> bool:
    """
    Crée ou met à jour une clé settings.
    """
    key = str(key or "").strip()
    if not key:
        return False

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
                """,
                (key, str(value or "").strip()),
            )
        return True
    except Exception:
        return False


def ensure_setting_key(cur, key: str, default_value: str = ""):
    """
    Garantit qu'une clé existe dans settings sans écraser une valeur déjà présente.
    """
    cur.execute(
        """
        INSERT INTO settings (key, value)
        VALUES (%s, %s)
        ON CONFLICT (key) DO NOTHING
        """,
        (str(key or "").strip(), str(default_value or "").strip()),
    )


# =========================
# INITIALISATION BASE
# =========================
def init_db():
    """
    Initialise les tables principales et applique les migrations progressives.
    """
    try:
        with get_cursor(commit=True) as cur:
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

            add_column_if_missing(cur, "users", "plan", "TEXT DEFAULT 'FREE'")
            add_column_if_missing(cur, "users", "free_orders_used", "INTEGER DEFAULT 0")

            # Champs abonnement PREMIUM_PLUS
            add_column_if_missing(cur, "users", "subscription_duration", "TEXT")
            add_column_if_missing(cur, "users", "subscription_paid", "BOOLEAN DEFAULT FALSE")
            add_column_if_missing(cur, "users", "subscription_payment_status", "TEXT")
            add_column_if_missing(cur, "users", "subscription_start_date", "TIMESTAMP")
            add_column_if_missing(cur, "users", "subscription_end_date", "TIMESTAMP")

            # Compatibilité / lecture souple PREMIUM_PLUS
            add_column_if_missing(cur, "users", "subscription_status", "TEXT")
            add_column_if_missing(cur, "users", "subscription_active", "BOOLEAN DEFAULT FALSE")
            add_column_if_missing(cur, "users", "premium_plus_active", "BOOLEAN DEFAULT FALSE")
            add_column_if_missing(cur, "users", "premium_plus_status", "TEXT")

            # Normalisation users existants
            cur.execute(
                """
                UPDATE users
                SET plan = 'FREE'
                WHERE plan IS NULL
                   OR TRIM(plan) = ''
                """
            )

            cur.execute(
                """
                UPDATE users
                SET free_orders_used = 0
                WHERE free_orders_used IS NULL
                """
            )

            cur.execute(
                """
                UPDATE users
                SET subscription_paid = FALSE
                WHERE subscription_paid IS NULL
                """
            )

            cur.execute(
                """
                UPDATE users
                SET subscription_active = FALSE
                WHERE subscription_active IS NULL
                """
            )

            cur.execute(
                """
                UPDATE users
                SET premium_plus_active = FALSE
                WHERE premium_plus_active IS NULL
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

            # Clés système minimales
            ensure_setting_key(cur, "default_country_code", "CM")
            ensure_setting_key(cur, "eur_xaf_rate", "655.957")
            ensure_setting_key(cur, "brand_name", "AfriPay Afrika")

            # Clés WhatsApp prévues par l'architecture
            # Valeurs laissées volontairement vides tant qu'elles ne sont pas configurées.
            ensure_setting_key(cur, "support_whatsapp_number", "")
            ensure_setting_key(cur, "whatsapp_default", "")
            ensure_setting_key(cur, "whatsapp_number_cm", "")

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

            # snapshot client
            add_column_if_missing(cur, "orders", "client_name", "TEXT")
            add_column_if_missing(cur, "orders", "client_phone", "TEXT")
            add_column_if_missing(cur, "orders", "client_email", "TEXT")

            add_column_if_missing(cur, "orders", "country_code", "TEXT DEFAULT 'CM'")
            add_column_if_missing(cur, "orders", "site_name", "TEXT")
            add_column_if_missing(cur, "orders", "product_url", "TEXT")
            add_column_if_missing(cur, "orders", "product_title", "TEXT")
            add_column_if_missing(cur, "orders", "product_name", "TEXT")
            add_column_if_missing(cur, "orders", "product_specs", "TEXT")

            # montant d'origine marchand / multi-devise
            add_column_if_missing(cur, "orders", "merchant_total_amount", "DOUBLE PRECISION DEFAULT 0")
            add_column_if_missing(cur, "orders", "merchant_currency", "TEXT DEFAULT 'EUR'")
            add_column_if_missing(cur, "orders", "merchant_total_xaf", "INTEGER DEFAULT 0")

            # ancien modèle encore toléré
            add_column_if_missing(cur, "orders", "product_price_eur", "DOUBLE PRECISION DEFAULT 0")
            add_column_if_missing(cur, "orders", "shipping_estimate_eur", "DOUBLE PRECISION DEFAULT 0")

            # modèle métier AfriPay
            add_column_if_missing(cur, "orders", "total_to_pay_eur", "DOUBLE PRECISION DEFAULT 0")
            add_column_if_missing(cur, "orders", "total_xaf", "INTEGER DEFAULT 0")
            add_column_if_missing(cur, "orders", "seller_fee_xaf", "INTEGER DEFAULT 0")
            add_column_if_missing(cur, "orders", "afripay_fee_xaf", "INTEGER DEFAULT 0")

            add_column_if_missing(cur, "orders", "delivery_address", "TEXT")
            add_column_if_missing(cur, "orders", "momo_provider", "TEXT")
            add_column_if_missing(cur, "orders", "payment_method", "TEXT")
            add_column_if_missing(cur, "orders", "order_status", "TEXT DEFAULT 'CREEE'")
            add_column_if_missing(cur, "orders", "payment_status", "TEXT DEFAULT 'PENDING'")

            # nouveaux champs paiement fintech
            add_column_if_missing(cur, "orders", "payment_provider", "TEXT")
            add_column_if_missing(cur, "orders", "proof_sent_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "proof_received_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "payment_confirmed_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "payment_rejected_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "payment_admin_note", "TEXT")

            # compatibilité avec afripay_app_REBUILD.py
            add_column_if_missing(cur, "orders", "payment_proof_sent_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "payment_proof_received_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "admin_note", "TEXT")

            # tracking marchand
            add_column_if_missing(cur, "orders", "merchant_status", "TEXT")
            add_column_if_missing(cur, "orders", "merchant_order_number", "TEXT")
            add_column_if_missing(cur, "orders", "merchant_confirmation_url", "TEXT")
            add_column_if_missing(cur, "orders", "merchant_tracking_url", "TEXT")
            add_column_if_missing(cur, "orders", "merchant_purchase_date", "TEXT")
            add_column_if_missing(cur, "orders", "merchant_notes", "TEXT")
            add_column_if_missing(cur, "orders", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            add_column_if_missing(cur, "orders", "delivered_at", "TIMESTAMP")

            # préparation règles AfriPay métier
            add_column_if_missing(cur, "orders", "freight_forwarder_name", "TEXT")
            add_column_if_missing(cur, "orders", "freight_forwarder_address", "TEXT")
            add_column_if_missing(cur, "orders", "merchant_delivery_address", "TEXT")

            # préparation remboursements / conformité test privé
            add_column_if_missing(cur, "orders", "refund_status", "TEXT DEFAULT 'NONE'")
            add_column_if_missing(cur, "orders", "refund_amount_xaf", "INTEGER DEFAULT 0")
            add_column_if_missing(cur, "orders", "refund_amount_eur", "DOUBLE PRECISION DEFAULT 0")
            add_column_if_missing(cur, "orders", "refund_reason", "TEXT")
            add_column_if_missing(cur, "orders", "refund_proof_url", "TEXT")
            add_column_if_missing(cur, "orders", "refund_requested_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "refund_processed_at", "TIMESTAMP")

            # compatibilité avec pipeline remboursement UI admin
            add_column_if_missing(cur, "orders", "refund_proof_sent_at", "TIMESTAMP")
            add_column_if_missing(cur, "orders", "refund_confirmed_at", "TIMESTAMP")

            # -------------------------
            # NORMALISATION DONNEES EXISTANTES - ORDERS
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

            cur.execute(
                """
                UPDATE orders
                SET order_status = 'CREEE'
                WHERE order_status IS NULL
                   OR TRIM(order_status) = ''
                """
            )

            # ancienne logique paiement -> nouvelle logique fintech
            cur.execute(
                """
                UPDATE orders
                SET payment_status = 'PENDING'
                WHERE payment_status IS NULL
                   OR TRIM(payment_status) = ''
                   OR payment_status = 'EN_ATTENTE'
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET payment_status = 'CONFIRMED'
                WHERE payment_status = 'PAYE'
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET payment_status = 'REJECTED'
                WHERE payment_status = 'ECHEC'
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET payment_provider = momo_provider
                WHERE (payment_provider IS NULL OR TRIM(payment_provider) = '')
                  AND momo_provider IS NOT NULL
                  AND TRIM(momo_provider) <> ''
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET payment_method = momo_provider
                WHERE (payment_method IS NULL OR TRIM(payment_method) = '')
                  AND momo_provider IS NOT NULL
                  AND TRIM(momo_provider) <> ''
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET refund_status = 'NONE'
                WHERE refund_status IS NULL
                   OR TRIM(refund_status) = ''
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET refund_amount_xaf = 0
                WHERE refund_amount_xaf IS NULL
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET refund_amount_eur = 0
                WHERE refund_amount_eur IS NULL
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET payment_proof_sent_at = proof_sent_at
                WHERE payment_proof_sent_at IS NULL
                  AND proof_sent_at IS NOT NULL
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET payment_proof_received_at = proof_received_at
                WHERE payment_proof_received_at IS NULL
                  AND proof_received_at IS NOT NULL
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET admin_note = payment_admin_note
                WHERE (admin_note IS NULL OR TRIM(admin_note) = '')
                  AND payment_admin_note IS NOT NULL
                  AND TRIM(payment_admin_note) <> ''
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET merchant_total_xaf = total_xaf
                WHERE (merchant_total_xaf IS NULL OR merchant_total_xaf = 0)
                  AND total_xaf IS NOT NULL
                  AND total_xaf > 0
                """
            )

            cur.execute(
                """
                UPDATE orders
                SET freight_forwarder_address = delivery_address
                WHERE (freight_forwarder_address IS NULL OR TRIM(freight_forwarder_address) = '')
                  AND delivery_address IS NOT NULL
                  AND TRIM(delivery_address) <> ''
                """
            )

            # backfill snapshot client depuis users si vide
            cur.execute(
                """
                UPDATE orders o
                SET client_name = u.name
                FROM users u
                WHERE o.user_id = u.id
                  AND (o.client_name IS NULL OR TRIM(o.client_name) = '')
                  AND u.name IS NOT NULL
                  AND TRIM(u.name) <> ''
                """
            )

            cur.execute(
                """
                UPDATE orders o
                SET client_phone = u.phone
                FROM users u
                WHERE o.user_id = u.id
                  AND (o.client_phone IS NULL OR TRIM(o.client_phone) = '')
                  AND u.phone IS NOT NULL
                  AND TRIM(u.phone) <> ''
                """
            )

            cur.execute(
                """
                UPDATE orders o
                SET client_email = u.email
                FROM users u
                WHERE o.user_id = u.id
                  AND (o.client_email IS NULL OR TRIM(o.client_email) = '')
                  AND u.email IS NOT NULL
                  AND TRIM(u.email) <> ''
                """
            )

            # -------------------------
            # CONTRAINTES / SECURISATION
            # -------------------------
            if not constraint_exists(cur, "orders_order_code_key"):
                cur.execute(
                    """
                    DO $$
                    BEGIN
                        BEGIN
                            ALTER TABLE orders
                            ADD CONSTRAINT orders_order_code_key UNIQUE (order_code);
                        EXCEPTION
                            WHEN duplicate_object THEN
                                NULL;
                        END;
                    END
                    $$;
                    """
                )

            if not constraint_exists(cur, "users_phone_key"):
                cur.execute(
                    """
                    DO $$
                    BEGIN
                        BEGIN
                            ALTER TABLE users
                            ADD CONSTRAINT users_phone_key UNIQUE (phone);
                        EXCEPTION
                            WHEN duplicate_object THEN
                                NULL;
                        END;
                    END
                    $$;
                    """
                )

            # -------------------------
            # INDEX USERS
            # -------------------------
            add_index_if_missing(cur, "idx_users_phone", "users", "(phone)")
            add_index_if_missing(cur, "idx_users_plan", "users", "(plan)")
            add_index_if_missing(cur, "idx_users_subscription_end_date", "users", "(subscription_end_date)")

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
            add_index_if_missing(cur, "idx_orders_payment_provider", "orders", "(payment_provider)")
            add_index_if_missing(cur, "idx_orders_payment_method", "orders", "(payment_method)")
            add_index_if_missing(cur, "idx_orders_client_phone", "orders", "(client_phone)")
            add_index_if_missing(cur, "idx_orders_refund_status", "orders", "(refund_status)")

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

        return True

    except Exception as e:
        print("❌ init_db échoué :", e)
        return False