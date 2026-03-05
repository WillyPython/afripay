import os
import sqlite3
import secrets
from datetime import datetime
import streamlit as st

APP_TITLE = "AfriPay Afrika"


# =========================
# DB PATH (Cloud compatible)
# =========================

def get_db_path():

    if os.getenv("STREAMLIT_SERVER_HEADLESS"):
        return "/tmp/afripay.db"

    return "afripay.db"


DB_PATH = get_db_path()


def get_conn():

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    return conn


def now():

    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


# =========================
# INIT DB
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

    conn.commit()
    conn.close()


# =========================
# SESSION
# =========================

def init_session():

    if "logged" not in st.session_state:

        st.session_state.logged = False
        st.session_state.user_id = None


def logout():

    st.session_state.logged = False
    st.session_state.user_id = None


# =========================
# USER UPSERT
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
            (phone, name, email, now())
        )

        uid = cur.lastrowid

    conn.commit()
    conn.close()

    return uid


# =========================
# CREATE ORDER
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
    """,
    (
        user_id,
        now(),
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

    # logo pro (taille fixée)
    st.sidebar.image("assets/logo.png", width=220)

    # séparation
    st.sidebar.markdown("---")

    st.sidebar.markdown(f"## {APP_TITLE}")

    st.sidebar.caption("MVP — Facilitateur de paiement international")

    if st.session_state.logged:

        st.sidebar.success("Connecté ✅")

        if st.sidebar.button("Déconnexion"):

            logout()
            st.rerun()

    else:

        st.sidebar.info("Non connecté")

    st.sidebar.markdown("---")

    return st.sidebar.radio(
        "Menu",
        [
            "Connexion",
            "Simuler",
            "Créer commande",
            "Mes commandes",
            "Admin"
        ]
    )


# =========================
# LOGIN PAGE
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
# CREATE ORDER PAGE
# =========================

def page_create():

    if not st.session_state.logged:

        st.warning("Connecte-toi")
        return

    st.title("Créer commande")

    product = st.text_input("Produit")

    amount = st.number_input("Montant produit XAF", 0)

    seller_fee = st.number_input("Frais vendeur (site)", 0)

    afripay_fee = st.number_input("Frais de service AfriPay", 0)

    address = st.text_area("Adresse agence / transitaire")

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

    if not st.session_state.logged:

        st.warning("Connecte-toi")
        return

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
# ADMIN PAGE
# =========================

def page_admin():

    st.title("Admin")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as n FROM users")
    users = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM orders")
    orders = cur.fetchone()["n"]

    conn.close()

    col1, col2 = st.columns(2)

    col1.metric("Utilisateurs", users)
    col2.metric("Commandes", orders)


# =========================
# MAIN
# =========================

def main():

    st.set_page_config(page_title=APP_TITLE)

    init_db()
    init_session()

    menu = sidebar()

    if menu == "Connexion":
        page_login()

    elif menu == "Simuler":
        st.title("Simulation paiement")

    elif menu == "Créer commande":
        page_create()

    elif menu == "Mes commandes":
        page_orders()

    elif menu == "Admin":
        page_admin()


if __name__ == "__main__":
    main()