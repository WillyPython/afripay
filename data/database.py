import os
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL est introuvable dans les variables d'environnement.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_conn():
    """
    Alias de compatibilité avec l'ancien code.
    Certains services importent encore get_conn.
    """
    return get_connection()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        phone TEXT UNIQUE NOT NULL,
        name TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_id TEXT UNIQUE,
        client_phone TEXT,
        merchant TEXT,
        product TEXT,
        amount_eur DOUBLE PRECISION,
        amount_xaf INTEGER,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()