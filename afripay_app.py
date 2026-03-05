import os
import sqlite3
import secrets
import hashlib
import hmac
from datetime import datetime

import streamlit as st

APP_TITLE = "AfriPay Afrika"


# =========================
# DB (Cloud safe)
# =========================

def is_streamlit_cloud():
    return os.getenv("STREAMLIT_SERVER_HEADLESS", "").lower() == "true"


def get_db_path():

    if is_streamlit_cloud():
        return "/tmp/afripay_v13.db"

    return "afripay.db"


DB_PATH = get_db_path()


def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def get_conn():

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    return conn


# =========================
# PASSWORD HASH
# =========================

def hash_password(password):

    salt = secrets.token_bytes(16)

    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)

    return salt.hex() + "$" + dk.hex()


def verify_password(password, stored):

    salt, hashed = stored.split("$")

    salt = bytes.fromhex(salt)

    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)

    return hmac.compare_digest(dk.hex(), hashed)


# =========================
# DB INIT
# =========================

def init_db():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        name TEXT,
        email TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        created_at TEXT,
        product_name TEXT,
        amount_xaf REAL,
        seller_fee_xaf REAL,
        afripay_fee_xaf REAL,
        total_xaf REAL,
        delivery_address TEXT,
        tracking_number TEXT,
        tracking_url TEXT,
        payment_status TEXT,
        order_status TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT,
        value TEXT
    )
    """)

    # reset admin table to avoid schema conflicts
    cur.execute("DROP TABLE IF EXISTS admin_auth")

    cur.execute("""
    CREATE TABLE admin_auth(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        password_hash TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# =========================
# SETTINGS
# =========================

def set_setting(key, value):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE settings SET value=? WHERE key=?", (value, key))

    if cur.rowcount == 0:
        cur.execute("INSERT INTO settings(key,value) VALUES (?,?)", (key, value))

    conn.commit()
    conn.close()


def get_setting(key):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()

    conn.close()

    if row:
        return row["value"]

    return None


# =========================
# ADMIN
# =========================

def ensure_admin():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as n FROM admin_auth")

    if cur.fetchone()["n"] == 0:

        pw = os.getenv("ADMIN_PASSWORD") or "admin123"

        hashed = hash_password(pw)

        cur.execute(
            "INSERT INTO admin_auth(password_hash,created_at) VALUES (?,?)",
            (hashed, now_iso())
        )

        conn.commit()

    conn.close()


def get_admin_hash():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT password_hash FROM admin_auth LIMIT 1")

    row = cur.fetchone()

    conn.close()

    return row["password_hash"]


# =========================
# SESSION
# =========================

def init_session():

    if "logged" not in st.session_state:

        st.session_state.logged = False
        st.session_state.user_id = None
        st.session_state.admin = False


def logout():

    st.session_state.logged = False
    st.session_state.user_id = None


# =========================
# USERS
# =========================

def upsert_user(phone, name, email):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE phone=?", (phone,))
    row = cur.fetchone()

    if row:

        uid = row["id"]

        cur.execute(
            "UPDATE users SET name=?,email=? WHERE id=?",
            (name, email, uid)
        )

    else:

        cur.execute(
            "INSERT INTO users(phone,name,email,created_at) VALUES (?,?,?,?)",
            (phone, name, email, now_iso())
        )

        uid = cur.lastrowid

    conn.commit()
    conn.close()

    return uid


# =========================
# ORDERS
# =========================

def create_order(user_id, product, amount, seller_fee, afripay_fee, address):

    total = amount + seller_fee + afripay_fee

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO orders(
        user_id,created_at,
        product_name,amount_xaf,
        seller_fee_xaf,afripay_fee_xaf,total_xaf,
        delivery_address,
        payment_status,order_status
    )
    VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        user_id,
        now_iso(),
        product,
        amount,
        seller_fee,
        afripay_fee,
        total,
        address,
        "EN_ATTENTE",
        "CREÉE"
    ))

    conn.commit()
    conn.close()


# =========================
# SIDEBAR
# =========================

def sidebar():

    st.sidebar.image("assets/logo.png", use_container_width=True)

    st.sidebar.markdown(f"## {APP_TITLE}")

    st.sidebar.caption("MVP — Facilitateur de paiement international")

    if st.session_state.logged:

        st.sidebar.success("Connecté ✅")

        if st.sidebar.button("Déconnexion"):
            logout()
            st.rerun()

    else:

        st.sidebar.info("Non connecté")

    return st.sidebar.radio(
        "Menu",
        ["Connexion", "Simuler", "Créer commande", "Mes commandes", "Admin"]
    )


# =========================
# LOGIN
# =========================

def page_login():

    st.title("Connexion")

    phone = st.text_input("Téléphone")

    if st.button("Envoyer OTP"):

        otp = str(secrets.randbelow(900000) + 100000)

        st.session_state.otp = otp
        st.session_state.otp_phone = phone

        st.info(f"OTP TEST : {otp}")

    otp_input = st.text_input("Entrer OTP")

    name = st.text_input("Nom")
    email = st.text_input("Email")

    if st.button("Se connecter"):

        if otp_input == st.session_state.get("otp"):

            uid = upsert_user(phone, name, email)

            st.session_state.logged = True
            st.session_state.user_id = uid

            st.success("Connexion réussie")

            st.rerun()

        else:

            st.error("OTP incorrect")


# =========================
# CREATE ORDER
# =========================

def page_create():

    if not st.session_state.logged:

        st.warning("Connecte-toi")
        return

    st.title("Créer commande")

    product = st.text_input("Produit")

    amount = st.number_input("Montant produit", 0)

    seller_fee = st.number_input("Frais vendeur (site)", 0)

    afripay_fee = st.number_input("Frais service AfriPay", 0)

    address = st.text_area("Adresse agence/transitaire")

    if st.button("Créer commande"):

        if not address:

            st.error("Adresse obligatoire")
            return

        create_order(
            st.session_state.user_id,
            product,
            amount,
            seller_fee,
            afripay_fee,
            address
        )

        st.success("Commande créée")


# =========================
# MY ORDERS
# =========================

def page_orders():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",
        (st.session_state.user_id,)
    )

    rows = cur.fetchall()

    conn.close()

    for r in rows:

        st.write(
            f"Commande #{r['id']} — {r['order_status']} — {r['total_xaf']} XAF"
        )


# =========================
# ADMIN
# =========================

def page_admin():

    st.title("Admin")

    pw = st.text_input("Mot de passe admin", type="password")

    if st.button("Login"):

        stored = get_admin_hash()

        if verify_password(pw, stored):

            st.session_state.admin = True

        else:

            st.error("Mot de passe incorrect")

    if st.session_state.admin:

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as n FROM users")
        users = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM orders")
        orders = cur.fetchone()["n"]

        conn.close()

        st.metric("Utilisateurs", users)
        st.metric("Commandes", orders)


# =========================
# MAIN
# =========================

def main():

    st.set_page_config(page_title=APP_TITLE)

    init_db()
    ensure_admin()
    init_session()

    menu = sidebar()

    if menu == "Connexion":
        page_login()

    elif menu == "Simuler":
        st.title("Simulation")

    elif menu == "Créer commande":
        page_create()

    elif menu == "Mes commandes":
        page_orders()

    elif menu == "Admin":
        page_admin()


if __name__ == "__main__":
    main()