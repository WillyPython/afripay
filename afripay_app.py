import os
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime
from pathlib import Path

import streamlit as st

APP_TITLE = "AfriPay Afrika"


# ----------------------------
# DB PATH (Cloud-safe)
# ----------------------------
def is_streamlit_cloud() -> bool:
    return os.getenv("STREAMLIT_SERVER_HEADLESS", "").lower() == "true"


def get_db_path() -> str:
    env_path = os.getenv("AFRIPAY_DB_PATH")
    if env_path:
        return env_path
    if is_streamlit_cloud():
        return "/tmp/afripay.db"
    return "afripay.db"


DB_PATH = get_db_path()


def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------
# Admin password hashing
# ----------------------------
def pbkdf2_hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    iterations = 200_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def pbkdf2_verify_password(password: str, stored: str) -> bool:
    # stored hash format OR legacy plaintext fallback handled elsewhere
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


# ----------------------------
# DB INIT
# ----------------------------
def init_db():
    # Optional seed copy on cloud (if you have afripay.db in repo)
    if is_streamlit_cloud():
        seed = Path("afripay.db")
        target = Path(DB_PATH)
        try:
            if seed.exists() and not target.exists():
                target.write_bytes(seed.read_bytes())
        except Exception:
            pass

    conn = get_conn()
    cur = conn.cursor()

    # users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        name TEXT,
        email TEXT,
        created_at TEXT
    )
    """)

    # orders (v1.2 fields)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        created_at TEXT,

        product_name TEXT,
        amount_xaf REAL,

        seller_fee_xaf REAL,
        afripay_fee_xaf REAL,
        total_xaf REAL,

        delivery_address TEXT,
        client_ack INTEGER DEFAULT 0,

        tracking_number TEXT,
        tracking_url TEXT,

        payment_status TEXT,
        order_status TEXT,

        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # settings (keep minimal schema: key/value only, compatible with old DB)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT,
        value TEXT
    )
    """)

    # admin_auth:
    # IMPORTANT: keep minimal + compatible. Some old DB may have password instead of password_hash.
    # We'll create a "best" table if missing; if it exists with different columns, we won't break it.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_auth (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        password_hash TEXT,
        created_at TEXT
    )
    """)

    # safe add columns if missing (ignore errors)
    def add_col(table: str, col_def: str):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass

    # orders migrations
    add_col("orders", "seller_fee_xaf REAL")
    add_col("orders", "afripay_fee_xaf REAL")
    add_col("orders", "total_xaf REAL")
    add_col("orders", "delivery_address TEXT")
    add_col("orders", "client_ack INTEGER DEFAULT 0")
    add_col("orders", "tracking_number TEXT")
    add_col("orders", "tracking_url TEXT")
    add_col("orders", "payment_status TEXT")
    add_col("orders", "order_status TEXT")

    # admin_auth migrations (for older DB)
    add_col("admin_auth", "password_hash TEXT")
    add_col("admin_auth", "created_at TEXT")
    add_col("admin_auth", "password TEXT")  # legacy support, if not exist

    conn.commit()
    conn.close()


# ----------------------------
# SETTINGS (UPSERT without updated_at and without ON CONFLICT)
# ----------------------------
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


# ----------------------------
# ADMIN AUTH (schema-flexible)
# ----------------------------
def admin_auth_columns(cur) -> set[str]:
    cur.execute("PRAGMA table_info(admin_auth)")
    return {r["name"] for r in cur.fetchall()}


def ensure_admin_exists():
    """
    Create an admin credential if missing.
    Works with either:
      - admin_auth(password_hash, created_at)
      - admin_auth(password) legacy
      - admin_auth without created_at
    """
    conn = get_conn()
    cur = conn.cursor()

    cols = admin_auth_columns(cur)

    # check if there's already an admin row (any schema)
    cur.execute("SELECT COUNT(*) AS n FROM admin_auth")
    if cur.fetchone()["n"] > 0:
        conn.close()
        return

    # choose admin password from secrets/env/fallback
    admin_pw = None
    try:
        admin_pw = st.secrets.get("ADMIN_PASSWORD", None)
    except Exception:
        admin_pw = None
    if not admin_pw:
        admin_pw = os.getenv("ADMIN_PASSWORD") or "admin123"

    # insert depending on available columns
    if "password_hash" in cols:
        ph = pbkdf2_hash_password(admin_pw)
        if "created_at" in cols:
            cur.execute(
                "INSERT INTO admin_auth(password_hash, created_at) VALUES (?, ?)",
                (ph, now_iso()),
            )
        else:
            cur.execute(
                "INSERT INTO admin_auth(password_hash) VALUES (?)",
                (ph,),
            )
    elif "password" in cols:
        # legacy plaintext support (not ideal, but avoids crash)
        cur.execute("INSERT INTO admin_auth(password) VALUES (?)", (admin_pw,))
    else:
        # last resort: create row with id only
        cur.execute("INSERT INTO admin_auth DEFAULT VALUES")

    conn.commit()
    conn.close()


def get_admin_credential() -> tuple[str | None, str]:
    """
    Returns (stored_value, mode) where mode is:
      - "hash" (password_hash)
      - "plain" (password)
    """
    conn = get_conn()
    cur = conn.cursor()
    cols = admin_auth_columns(cur)

    if "password_hash" in cols:
        cur.execute("SELECT password_hash AS v FROM admin_auth ORDER BY id LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return (row["v"] if row else None), "hash"

    if "password" in cols:
        cur.execute("SELECT password AS v FROM admin_auth ORDER BY id LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return (row["v"] if row else None), "plain"

    conn.close()
    return None, "none"


def ensure_defaults():
    if get_setting("eur_xaf_rate") is None:
        set_setting("eur_xaf_rate", "655.957")
    ensure_admin_exists()


# ----------------------------
# SESSION
# ----------------------------
def init_session():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("user_phone", "")
    st.session_state.setdefault("user_name", "")
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("otp_code", None)
    st.session_state.setdefault("otp_phone", None)
    st.session_state.setdefault("admin_logged_in", False)


def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["user_id"] = None
    st.session_state["user_phone"] = ""
    st.session_state["user_name"] = ""
    st.session_state["user_email"] = ""
    st.session_state["otp_code"] = None
    st.session_state["otp_phone"] = None


def logout_admin():
    st.session_state["admin_logged_in"] = False


# ----------------------------
# DATA
# ----------------------------
def upsert_user(phone: str, name: str = "", email: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE phone=?", (phone,))
    row = cur.fetchone()

    if row:
        user_id = int(row["id"])
        cur.execute("UPDATE users SET name=?, email=? WHERE id=?", (name, email, user_id))
    else:
        cur.execute(
            "INSERT INTO users(phone, name, email, created_at) VALUES (?, ?, ?, ?)",
            (phone, name, email, now_iso()),
        )
        user_id = cur.lastrowid

    conn.commit()
    conn.close()
    return int(user_id)


def create_order(user_id: int, product_name: str, amount_xaf: float,
                 seller_fee_xaf: float, afripay_fee_xaf: float,
                 delivery_address: str) -> int:
    total = float(amount_xaf) + float(seller_fee_xaf) + float(afripay_fee_xaf)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders(
            user_id, created_at,
            product_name, amount_xaf,
            seller_fee_xaf, afripay_fee_xaf, total_xaf,
            delivery_address, client_ack,
            tracking_number, tracking_url,
            payment_status, order_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, now_iso(),
        product_name, amount_xaf,
        seller_fee_xaf, afripay_fee_xaf, total,
        delivery_address, 0,
        "", "",
        "EN_ATTENTE", "CREÉE"
    ))
    oid = cur.lastrowid
    conn.commit()
    conn.close()
    return int(oid)


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
    sum_total = cur.fetchone()["s"]

    cur.execute("""
        SELECT order_status, COUNT(*) AS n
        FROM orders
        GROUP BY order_status
        ORDER BY n DESC
    """)
    by_status = cur.fetchall()

    cur.execute("""
        SELECT payment_status, COUNT(*) AS n
        FROM orders
        GROUP BY payment_status
        ORDER BY n DESC
    """)
    by_payment = cur.fetchall()

    conn.close()
    return users_n, orders_n, sum_total, by_status, by_payment


# ----------------------------
# UI
# ----------------------------
def sidebar():
    st.sidebar.markdown(f"## {APP_TITLE}")
    st.sidebar.caption("MVP — Facilitateur de paiement international (Phase pilote)")

    if st.session_state.get("logged_in"):
        st.sidebar.success("Connecté ✅")
        if st.sidebar.button("Déconnexion"):
            logout_user()
            st.rerun()
    else:
        st.sidebar.info("Non connecté")

    st.sidebar.markdown("### Menu")
    return st.sidebar.radio("", ["Connexion", "Simuler", "Créer commande", "Mes commandes", "Admin"], index=0)


def page_connexion():
    st.title("Connexion")
    st.write("### 1) Demander OTP (mode test)")
    phone = st.text_input("Téléphone (ex: +2376xxxxxxxx)", placeholder="+2376...")

    if st.button("Envoyer OTP"):
        if not phone.strip():
            st.error("Entre ton numéro de téléphone.")
            return
        otp = f"{secrets.randbelow(900000) + 100000}"
        st.session_state["otp_code"] = otp
        st.session_state["otp_phone"] = phone.strip()
        st.info(f"OTP TEST (affiché uniquement en mode test): **{otp}**")

    st.write("### 2) Valider OTP")
    otp_in = st.text_input("Entrer OTP", type="password")
    name = st.text_input("Nom (optionnel)")
    email = st.text_input("Email (optionnel)")

    if st.button("Se connecter"):
        if not st.session_state.get("otp_code") or not st.session_state.get("otp_phone"):
            st.error("Demande d'abord un OTP.")
            return
        if phone.strip() != st.session_state["otp_phone"]:
            st.error("Le téléphone ne correspond pas à celui utilisé pour l’OTP.")
            return
        if otp_in.strip() != st.session_state["otp_code"]:
            st.error("OTP incorrect.")
            return

        user_id = upsert_user(phone.strip(), name.strip(), email.strip())
        st.session_state["logged_in"] = True
        st.session_state["user_id"] = user_id
        st.session_state["user_phone"] = phone.strip()
        st.session_state["user_name"] = name.strip()
        st.session_state["user_email"] = email.strip()
        st.success("Connexion OK ✅")
        st.rerun()


def page_simuler():
    st.title("Simuler")
    amount_xaf = st.number_input("Montant produit (XAF)", min_value=0.0, value=0.0, step=1000.0)
    seller_fee = st.number_input("Frais vendeur (site) (XAF)", min_value=0.0, value=0.0, step=500.0)
    afripay_fee = st.number_input("Frais de service AfriPay (XAF)", min_value=0.0, value=0.0, step=500.0)
    total = amount_xaf + seller_fee + afripay_fee
    st.metric("Total à payer (XAF)", f"{total:,.0f}".replace(",", " "))


def page_creer_commande():
    st.title("Créer commande")
    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté pour créer une commande.")
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
            st.error("Le nom de la commande est obligatoire.")
            return
        if total <= 0:
            st.error("Le total doit être > 0.")
            return
        if not delivery_address.strip():
            st.error("Adresse agence/transitaire obligatoire avant de créer une commande.")
            return

        oid = create_order(
            int(st.session_state["user_id"]),
            product_name.strip(),
            float(amount_xaf),
            float(seller_fee),
            float(afripay_fee),
            delivery_address.strip(),
        )
        st.success(f"Commande créée ✅ (ID: {oid})")


def page_mes_commandes():
    st.title("Mes commandes")
    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté pour voir tes commandes.")
        return

    rows = list_orders_for_user(int(st.session_state["user_id"]))
    if not rows:
        st.info("Aucune commande pour le moment.")
        return

    for r in rows:
        title = f"Commande #{r['id']} — {r.get('order_status','')} — {float(r.get('total_xaf',0) or 0):,.0f} XAF".replace(",", " ")
        with st.expander(title):
            st.write(f"**Créée le :** {r.get('created_at','')}")
            st.write(f"**Produit :** {r.get('product_name','')}")
            st.write(f"**Montant :** {float(r.get('amount_xaf',0) or 0):,.0f} XAF".replace(",", " "))
            st.write(f"**Frais vendeur (site) :** {float(r.get('seller_fee_xaf',0) or 0):,.0f} XAF".replace(",", " "))
            st.write(f"**Frais de service AfriPay :** {float(r.get('afripay_fee_xaf',0) or 0):,.0f} XAF".replace(",", " "))
            st.write(f"**Total :** {float(r.get('total_xaf',0) or 0):,.0f} XAF".replace(",", " "))
            st.write(f"**Adresse agence/transitaire :** {r.get('delivery_address','')}")
            st.write(f"**Paiement :** {r.get('payment_status','')}")
            st.write(f"**Statut commande :** {r.get('order_status','')}")

            tr_num = (r.get("tracking_number") or "").strip()
            tr_url = (r.get("tracking_url") or "").strip()
            if tr_num or tr_url:
                st.write("**Tracking :**")
                if tr_num:
                    st.write(f"- Numéro : `{tr_num}`")
                if tr_url:
                    st.write(f"- Lien : {tr_url}")
            else:
                st.caption("Tracking non disponible pour l’instant.")


def page_admin():
    st.title("Admin")

    if not st.session_state.get("admin_logged_in"):
        st.subheader("Connexion Admin")
        pw = st.text_input("Mot de passe admin", type="password")

        if st.button("Se connecter (Admin)"):
            stored, mode = get_admin_credential()
            if not stored:
                st.error("Aucun mot de passe admin configuré.")
                return

            ok = False
            if mode == "hash":
                ok = pbkdf2_verify_password(pw, stored)
            elif mode == "plain":
                ok = hmac.compare_digest(pw, stored)

            if ok:
                st.session_state["admin_logged_in"] = True
                st.success("Admin connecté ✅")
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

        st.caption("Conseil : définis ADMIN_PASSWORD dans Streamlit Secrets.")
        return

    colA, colB = st.columns([1, 1])
    with colA:
        st.success("Admin connecté ✅")
    with colB:
        if st.button("Déconnexion Admin"):
            logout_admin()
            st.rerun()

    st.divider()

    st.subheader("Dashboard")
    users_n, orders_n, sum_total, by_status, by_payment = get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Utilisateurs", users_n)
    c2.metric("Commandes", orders_n)
    c3.metric("Total (XAF)", f"{float(sum_total):,.0f}".replace(",", " "))

    st.write("### Commandes par statut")
    st.dataframe([dict(x) for x in by_status] if by_status else [], use_container_width=True)

    st.write("### Paiements par statut")
    st.dataframe([dict(x) for x in by_payment] if by_payment else [], use_container_width=True)

    st.divider()

    st.subheader("Mettre à jour Tracking / Statuts")
    orders = list_orders_all(limit=200)
    if not orders:
        st.info("Aucune commande.")
        return

    options = {f"#{o['id']} — {o.get('user_phone','')} — {o.get('product_name','')}": int(o["id"]) for o in orders}
    selected_label = st.selectbox("Choisir une commande", list(options.keys()))
    order_id = options[selected_label]

    selected = next((o for o in orders if int(o["id"]) == int(order_id)), None)
    if not selected:
        st.error("Commande introuvable.")
        return

    tracking_number = st.text_input("Tracking number", value=(selected.get("tracking_number") or ""))
    tracking_url = st.text_input("Tracking URL", value=(selected.get("tracking_url") or ""))

    payment_options = ["EN_ATTENTE", "PAYÉ", "ÉCHEC", "REMBOURSÉ"]
    order_options = ["CREÉE", "EN_COURS", "EXPÉDIÉE", "LIVRÉE", "ANNULÉE"]

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
        update_order_admin(
            int(order_id),
            tracking_number.strip(),
            tracking_url.strip(),
            payment_status,
            order_status
        )
        st.success("Mise à jour enregistrée ✅")
        st.rerun()


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