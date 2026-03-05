import os
import sqlite3
import secrets
import hashlib
import hmac
from datetime import datetime

import streamlit as st

APP_TITLE = "AfriPay Afrika"


# =========================
# ENV / DB PATH
# =========================
def is_cloud() -> bool:
    return os.getenv("STREAMLIT_SERVER_HEADLESS", "").lower() == "true"


def db_path() -> str:
    # New file name avoids old schema conflicts on Streamlit Cloud
    return "/tmp/afripay_v17.db" if is_cloud() else "afripay.db"


DB_PATH = db_path()


def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def year_str() -> str:
    return datetime.utcnow().strftime("%Y")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# ADMIN PASSWORD (PBKDF2)
# =========================
def pbkdf2_hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    iterations = 200_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def pbkdf2_verify_password(password: str, stored: str) -> bool:
    try:
        algo, it_str, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(it_str)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# =========================
# DB INIT + MIGRATIONS
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

    # Orders with professional numbering
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT,                 -- AFR-YYYY-00001
        user_id INTEGER,
        created_at TEXT,

        product_name TEXT,
        amount_xaf REAL,

        seller_fee_xaf REAL,
        afripay_fee_xaf REAL,
        total_xaf REAL,

        delivery_address TEXT,           -- required
        client_ack INTEGER DEFAULT 0,

        tracking_number TEXT,
        tracking_url TEXT,

        payment_status TEXT,
        order_status TEXT,

        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT,
        value TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_auth(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        password_hash TEXT,
        created_at TEXT
    )
    """)

    # ---- safe add columns if old db exists locally ----
    def add_col(table: str, col_def: str):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass

    add_col("orders", "order_code TEXT")
    add_col("orders", "seller_fee_xaf REAL")
    add_col("orders", "afripay_fee_xaf REAL")
    add_col("orders", "total_xaf REAL")
    add_col("orders", "delivery_address TEXT")
    add_col("orders", "client_ack INTEGER DEFAULT 0")
    add_col("orders", "tracking_number TEXT")
    add_col("orders", "tracking_url TEXT")
    add_col("orders", "payment_status TEXT")
    add_col("orders", "order_status TEXT")

    conn.commit()
    conn.close()


# =========================
# SETTINGS
# =========================
def set_setting(key: str, value: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO settings(key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_setting(key: str, default: str | None = None) -> str | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=? ORDER BY rowid DESC LIMIT 1", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default


# =========================
# ADMIN INIT
# =========================
def ensure_admin_exists():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM admin_auth")
    n = cur.fetchone()["n"]
    if n == 0:
        # Use Streamlit Secrets if available
        admin_pw = None
        try:
            admin_pw = st.secrets.get("ADMIN_PASSWORD", None)
        except Exception:
            admin_pw = None
        if not admin_pw:
            admin_pw = os.getenv("ADMIN_PASSWORD") or "admin123"

        ph = pbkdf2_hash_password(admin_pw)
        cur.execute(
            "INSERT INTO admin_auth(password_hash, created_at) VALUES (?, ?)",
            (ph, now_iso())
        )
        conn.commit()
    conn.close()


def get_admin_hash() -> str | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM admin_auth ORDER BY id LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row["password_hash"] if row else None


def ensure_defaults():
    if get_setting("eur_xaf_rate") is None:
        set_setting("eur_xaf_rate", "655.957")
    ensure_admin_exists()


# =========================
# SESSION
# =========================
def init_session():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("otp_code", None)
    st.session_state.setdefault("otp_phone", None)
    st.session_state.setdefault("admin_logged_in", False)


def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["user_id"] = None
    st.session_state["otp_code"] = None
    st.session_state["otp_phone"] = None


def logout_admin():
    st.session_state["admin_logged_in"] = False


# =========================
# BUSINESS: USERS / ORDERS
# =========================
def upsert_user(phone: str, name: str, email: str) -> int:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE phone=?", (phone,))
    row = cur.fetchone()
    if row:
        uid = int(row["id"])
        cur.execute("UPDATE users SET name=?, email=? WHERE id=?", (name, email, uid))
    else:
        cur.execute(
            "INSERT INTO users(phone, name, email, created_at) VALUES (?, ?, ?, ?)",
            (phone, name, email, now_iso()),
        )
        uid = cur.lastrowid

    conn.commit()
    conn.close()
    return int(uid)


def next_order_code(cur: sqlite3.Cursor) -> str:
    y = year_str()
    prefix = f"AFR-{y}-"
    cur.execute("SELECT order_code FROM orders WHERE order_code LIKE ? ORDER BY id DESC LIMIT 1", (prefix + "%",))
    row = cur.fetchone()
    if not row or not row["order_code"]:
        return prefix + "00001"
    last = row["order_code"].split("-")[-1]
    try:
        n = int(last) + 1
    except Exception:
        n = 1
    return prefix + str(n).zfill(5)


def create_order(
    user_id: int,
    product_name: str,
    amount_xaf: float,
    seller_fee_xaf: float,
    afripay_fee_xaf: float,
    delivery_address: str
) -> str:
    total = float(amount_xaf) + float(seller_fee_xaf) + float(afripay_fee_xaf)

    conn = get_conn()
    cur = conn.cursor()

    code = next_order_code(cur)

    cur.execute("""
        INSERT INTO orders(
            order_code, user_id, created_at,
            product_name, amount_xaf,
            seller_fee_xaf, afripay_fee_xaf, total_xaf,
            delivery_address,
            tracking_number, tracking_url,
            payment_status, order_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        code, user_id, now_iso(),
        product_name, amount_xaf,
        seller_fee_xaf, afripay_fee_xaf, total,
        delivery_address,
        "", "",
        "EN_ATTENTE", "CREÉE"
    ))

    conn.commit()
    conn.close()
    return code


def list_orders_for_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def list_orders_all(limit: int = 200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.*, u.phone AS user_phone, u.name AS user_name
        FROM orders o
        LEFT JOIN users u ON u.id = o.user_id
        ORDER BY o.id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_order_admin(order_id: int, tracking_number: str, tracking_url: str,
                       payment_status: str, order_status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE orders
        SET tracking_number=?,
            tracking_url=?,
            payment_status=?,
            order_status=?
        WHERE id=?
    """, (tracking_number, tracking_url, payment_status, order_status, order_id))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS n FROM users")
    users_n = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM orders")
    orders_n = cur.fetchone()["n"]

    cur.execute("SELECT COALESCE(SUM(total_xaf), 0) AS s FROM orders")
    total_sum = cur.fetchone()["s"]

    conn.close()
    return users_n, orders_n, total_sum


# =========================
# UI: SIDEBAR
# =========================
def sidebar():
    # Logo centered + fintech sizing
    st.sidebar.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
    st.sidebar.image("assets/logo.png", width=180)
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    st.sidebar.markdown("---")

    # Title + slogan centered
    st.sidebar.markdown(
        """
        <div style='text-align:center'>
          <h3 style='margin-bottom:0'>AfriPay Afrika</h3>
          <p style='font-size:12px;color:gray;margin-top:4px'>
            Facilitateur de paiement international
          </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.markdown("")

    if st.session_state.get("logged_in"):
        st.sidebar.success("Connecté ✅")
        if st.sidebar.button("Déconnexion"):
            logout_user()
            st.rerun()
    else:
        st.sidebar.info("Non connecté")

    st.sidebar.markdown("---")

    return st.sidebar.radio(
        "Menu",
        ["Connexion", "Simuler", "Créer commande", "Mes commandes", "Admin"],
        index=0
    )


# =========================
# UI: PAGES
# =========================
def page_connexion():
    st.title("Connexion")

    phone = st.text_input("Téléphone", placeholder="+2376...")
    if st.button("Envoyer OTP"):
        if not phone.strip():
            st.error("Entre ton numéro.")
            return
        otp = f"{secrets.randbelow(900000) + 100000}"
        st.session_state["otp_code"] = otp
        st.session_state["otp_phone"] = phone.strip()
        st.info(f"OTP TEST : **{otp}**")

    otp_in = st.text_input("Entrer OTP", type="password")
    name = st.text_input("Nom", placeholder="Optionnel")
    email = st.text_input("Email", placeholder="Optionnel")

    if st.button("Se connecter"):
        if not st.session_state.get("otp_code"):
            st.error("Demande d'abord un OTP.")
            return
        if phone.strip() != st.session_state.get("otp_phone"):
            st.error("Téléphone différent de celui utilisé pour l’OTP.")
            return
        if otp_in.strip() != st.session_state.get("otp_code"):
            st.error("OTP incorrect.")
            return

        uid = upsert_user(phone.strip(), name.strip(), email.strip())
        st.session_state["logged_in"] = True
        st.session_state["user_id"] = uid
        st.success("Connexion OK ✅")
        st.rerun()


def page_simuler():
    st.title("Simuler paiement")
    amount_xaf = st.number_input("Montant produit (XAF)", min_value=0.0, value=0.0, step=1000.0)
    seller_fee = st.number_input("Frais vendeur (site) (XAF)", min_value=0.0, value=0.0, step=500.0)
    afripay_fee = st.number_input("Frais de service AfriPay (XAF)", min_value=0.0, value=0.0, step=500.0)
    total = amount_xaf + seller_fee + afripay_fee
    st.metric("Total à payer (XAF)", f"{total:,.0f}".replace(",", " "))


def page_creer_commande():
    st.title("Créer commande")

    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté.")
        return

    st.info("📌 Transparence : AfriPay facilite uniquement le paiement. Le client fournit l’adresse de son agence/transitaire et gère livraison + dédouanement.")

    with st.form("create_order_form"):
        product_name = st.text_input("Nom du produit / commande")
        amount_xaf = st.number_input("Montant produit (XAF)", min_value=0.0, value=0.0, step=1000.0)

        col1, col2 = st.columns(2)
        with col1:
            seller_fee = st.number_input("Frais vendeur (site) (XAF)", min_value=0.0, value=0.0, step=500.0)
        with col2:
            afripay_fee = st.number_input("Frais de service AfriPay (XAF)", min_value=0.0, value=0.0, step=500.0)

        delivery_address = st.text_area("Adresse agence/transitaire (obligatoire)")
        total = amount_xaf + seller_fee + afripay_fee
        st.caption(f"Total estimé: {total:,.0f} XAF".replace(",", " "))

        submitted = st.form_submit_button("Créer la commande")

    if submitted:
        if not product_name.strip():
            st.error("Nom obligatoire.")
            return
        if total <= 0:
            st.error("Total doit être > 0.")
            return
        if not delivery_address.strip():
            st.error("Adresse agence/transitaire obligatoire.")
            return

        code = create_order(
            int(st.session_state["user_id"]),
            product_name.strip(),
            float(amount_xaf),
            float(seller_fee),
            float(afripay_fee),
            delivery_address.strip(),
        )
        st.success(f"Commande créée ✅ Numéro: **{code}**")


def page_mes_commandes():
    st.title("Mes commandes")

    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté.")
        return

    rows = list_orders_for_user(int(st.session_state["user_id"]))
    if not rows:
        st.info("Aucune commande.")
        return

    for r in rows:
        code = r.get("order_code") or f"#{r['id']}"
        total = float(r.get("total_xaf", 0) or 0)
        title = f"{code} — {r.get('order_status','')} — {total:,.0f} XAF".replace(",", " ")
        with st.expander(title):
            st.write(f"**Créée le :** {r.get('created_at','')}")
            st.write(f"**Produit :** {r.get('product_name','')}")
            st.write(f"**Montant :** {float(r.get('amount_xaf',0) or 0):,.0f} XAF".replace(",", " "))
            st.write(f"**Frais vendeur (site) :** {float(r.get('seller_fee_xaf',0) or 0):,.0f} XAF".replace(",", " "))
            st.write(f"**Frais de service AfriPay :** {float(r.get('afripay_fee_xaf',0) or 0):,.0f} XAF".replace(",", " "))
            st.write(f"**Total :** {total:,.0f} XAF".replace(",", " "))
            st.write(f"**Adresse agence/transitaire :** {r.get('delivery_address','')}")
            st.write(f"**Paiement :** {r.get('payment_status','')}")
            st.write(f"**Statut :** {r.get('order_status','')}")

            tr_num = (r.get("tracking_number") or "").strip()
            tr_url = (r.get("tracking_url") or "").strip()
            if tr_num or tr_url:
                st.write("**Tracking :**")
                if tr_num:
                    st.write(f"- Numéro : `{tr_num}`")
                if tr_url:
                    st.write(f"- Lien : {tr_url}")


def page_admin():
    st.title("Dashboard Admin")

    if not st.session_state.get("admin_logged_in"):
        st.subheader("Connexion Admin")
        pw = st.text_input("Mot de passe admin", type="password")
        if st.button("Se connecter (Admin)"):
            stored = get_admin_hash()
            if not stored:
                st.error("Admin non configuré.")
                return
            if pbkdf2_verify_password(pw, stored):
                st.session_state["admin_logged_in"] = True
                st.success("Admin connecté ✅")
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.caption("Conseil : définis ADMIN_PASSWORD dans Streamlit Secrets.")
        return

    st.success("Admin connecté ✅")
    if st.button("Déconnexion Admin"):
        logout_admin()
        st.rerun()

    users_n, orders_n, total_sum = get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Utilisateurs", users_n)
    c2.metric("Commandes", orders_n)
    c3.metric("Total (XAF)", f"{float(total_sum):,.0f}".replace(",", " "))

    st.divider()
    st.subheader("Mettre à jour Tracking / Statuts")

    orders = list_orders_all(limit=200)
    if not orders:
        st.info("Aucune commande.")
        return

    options = {}
    for o in orders:
        label = f"{o.get('order_code') or ('#' + str(o['id']))} — {o.get('user_phone','')} — {o.get('product_name','')}"
        options[label] = int(o["id"])

    selected_label = st.selectbox("Choisir une commande", list(options.keys()))
    order_id = options[selected_label]

    selected = next((o for o in orders if int(o["id"]) == int(order_id)), None)

    tracking_number = st.text_input("Tracking number", value=(selected.get("tracking_number") or ""))
    tracking_url = st.text_input("Tracking URL", value=(selected.get("tracking_url") or ""))

    payment_options = ["EN_ATTENTE", "PAYÉ", "ÉCHEC", "REMBOURSÉ"]
    order_options = ["CREÉE", "PAYÉE", "EN_COURS", "EXPÉDIÉE", "LIVRÉE", "ANNULÉE"]

    payment_current = (selected.get("payment_status") or "EN_ATTENTE")
    order_current = (selected.get("order_status") or "CREÉE")

    payment_status = st.selectbox(
        "Payment status",
        payment_options,
        index=payment_options.index(payment_current) if payment_current in payment_options else 0
    )
    order_status = st.selectbox(
        "Order status",
        order_options,
        index=order_options.index(order_current) if order_current in order_options else 0
    )

    if st.button("Enregistrer mise à jour"):
        update_order_admin(int(order_id), tracking_number.strip(), tracking_url.strip(), payment_status, order_status)
        st.success("Mise à jour enregistrée ✅")
        st.rerun()


# =========================
# MAIN
# =========================
def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    init_db()
    ensure_defaults()
    init_session()

    menu = sidebar()

    if menu == "Connexion":
        page_connexion()
    elif menu == "Simuler":
        page_simuler()
    elif menu == "Créer commande":
        page_creer_commande()
    elif menu == "Mes commandes":
        page_mes_commandes()
    elif menu == "Admin":
        page_admin()


if __name__ == "__main__":
    main()