# afripay_app.py
# AfriPay Afrika — MVP Paiement (Streamlit + SQLite)
# v1.2 (propre): Connecté + Déconnexion + Admin dashboard + tracking + labels clarifiés
# DB schema compatible with your current afripay.db tables.

import os
import re
import uuid
import time
import sqlite3
from datetime import datetime

import streamlit as st
import bcrypt

DB_PATH = "afripay.db"
UPLOAD_DIR = "uploads"

# ---------------------------
# DB helpers
# ---------------------------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if missing (safe with existing DB)."""
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        name TEXT,
        email TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        site_name TEXT,
        product_url TEXT NOT NULL,
        product_title TEXT,
        product_specs TEXT NOT NULL,
        product_image_path TEXT,
        product_price_eur REAL NOT NULL,
        shipping_estimate_eur REAL NOT NULL,
        commission_eur REAL NOT NULL,
        total_to_pay_eur REAL NOT NULL,
        eur_xaf_rate_used REAL NOT NULL,
        total_to_pay_xaf REAL NOT NULL,
        delivery_address TEXT NOT NULL,
        client_ack INTEGER NOT NULL,
        payment_reference TEXT UNIQUE NOT NULL,
        payment_status TEXT NOT NULL,
        momo_provider TEXT,
        momo_tx_id TEXT,
        payment_proof_path TEXT,
        purchase_proof_path TEXT,
        tracking_number TEXT,
        tracking_url TEXT,
        order_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_auth (
        id INTEGER PRIMARY KEY,
        password_hash TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def get_setting(key: str, default: str) -> str:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO settings(key, value, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """, (key, value, now))
    conn.commit()
    conn.close()

def ensure_defaults():
    # Baselines
    if get_setting("eur_xaf_rate", "") == "":
        set_setting("eur_xaf_rate", "655.957")
    if get_setting("commission_mode", "") == "":
        set_setting("commission_mode", "percent")  # percent / fixed
    if get_setting("commission_value", "") == "":
        set_setting("commission_value", "10")  # 10% default
    if get_setting("momo_payment_instructions", "") == "":
        set_setting(
            "momo_payment_instructions",
            "Paiement Mobile Money : envoyez le montant exact et indiquez la référence de paiement dans le message."
        )

def bcrypt_hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def bcrypt_check(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def ensure_admin():
    """
    Ensure admin_auth row exists.
    Priority:
      - Streamlit secrets ADMIN_PASSWORD (plain) if provided
      - Else DEV fallback "ChangeMe123!" (you already changed admin in DB, so this will not overwrite)
    """
    conn = db()
    cur = conn.cursor()
    row = cur.execute("SELECT password_hash FROM admin_auth WHERE id=1").fetchone()
    if not row:
        initial = st.secrets.get("ADMIN_PASSWORD", "ChangeMe123!")
        cur.execute(
            "INSERT INTO admin_auth(id, password_hash, updated_at) VALUES(1, ?, ?)",
            (bcrypt_hash(initial), datetime.utcnow().isoformat())
        )
        conn.commit()
    conn.close()

def admin_verify(pw: str) -> bool:
    conn = db()
    cur = conn.cursor()
    row = cur.execute("SELECT password_hash FROM admin_auth WHERE id=1").fetchone()
    conn.close()
    if not row:
        return False
    return bcrypt_check(pw, row["password_hash"])

def admin_set_password(new_pw: str):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE admin_auth SET password_hash=?, updated_at=? WHERE id=1",
        (bcrypt_hash(new_pw), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def upsert_user(phone: str, name: str = "", email: str = "") -> int:
    conn = db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    row = cur.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
    if row:
        user_id = row["id"]
        cur.execute("UPDATE users SET name=?, email=? WHERE id=?", (name, email, user_id))
    else:
        cur.execute(
            "INSERT INTO users(phone, name, email, created_at) VALUES(?, ?, ?, ?)",
            (phone, name, email, now)
        )
        user_id = cur.lastrowid

    conn.commit()
    conn.close()
    return int(user_id)

def get_user_by_phone(phone: str):
    conn = db()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return row

def create_order(
    user_id: int,
    site_name: str,
    product_url: str,
    product_title: str,
    product_specs: str,
    product_price_eur: float,
    vendor_fee_eur: float,              # stored in shipping_estimate_eur
    commission_eur: float,
    total_eur: float,
    eur_xaf_rate_used: float,
    total_xaf: float,
    delivery_address: str,              # agency / transitaire address
    client_ack: int,
    momo_provider: str,
    momo_tx_id: str | None,
    payment_proof_path: str | None,
    purchase_proof_path: str | None,
) -> str:
    conn = db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    ref = f"AFR-{uuid.uuid4().hex[:8].upper()}"

    cur.execute("""
        INSERT INTO orders(
            user_id, site_name, product_url, product_title, product_specs, product_image_path,
            product_price_eur, shipping_estimate_eur, commission_eur, total_to_pay_eur,
            eur_xaf_rate_used, total_to_pay_xaf,
            delivery_address, client_ack,
            payment_reference, payment_status,
            momo_provider, momo_tx_id,
            payment_proof_path, purchase_proof_path,
            tracking_number, tracking_url,
            order_status, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,
                  ?,?,?,?,
                  ?,?,
                  ?,?,
                  ?,?,
                  ?,?,
                  ?,?,
                  ?,?,
                  ?,?,?)
    """, (
        user_id, site_name, product_url, product_title, product_specs, None,
        product_price_eur, vendor_fee_eur, commission_eur, total_eur,
        eur_xaf_rate_used, total_xaf,
        delivery_address, client_ack,
        ref, "pending",
        momo_provider, momo_tx_id,
        payment_proof_path, purchase_proof_path,
        None, None,
        "created", now, now
    ))

    conn.commit()
    conn.close()
    return ref

def list_orders_for_user(user_id: int):
    conn = db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT * FROM orders
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows

def list_all_orders(limit: int = 300):
    conn = db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT o.*, u.phone AS user_phone, u.name AS user_name
        FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows

def update_order(order_id: int, **fields):
    if not fields:
        return
    conn = db()
    cur = conn.cursor()
    fields["updated_at"] = datetime.utcnow().isoformat()
    cols = ", ".join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values()) + [order_id]
    cur.execute(f"UPDATE orders SET {cols} WHERE id=?", vals)
    conn.commit()
    conn.close()

# ---------------------------
# Utils
# ---------------------------
def valid_phone(phone: str) -> bool:
    p = phone.strip().replace(" ", "")
    return bool(re.fullmatch(r"(\+?\d{8,15})", p))

def money_fmt(x: float) -> str:
    return f"{x:,.2f}"

def eur_to_xaf(eur: float, rate: float) -> float:
    return eur * rate

def compute_commission(subtotal_eur: float, mode: str, value: float) -> float:
    if mode == "fixed":
        return float(max(value, 0.0))
    return float(max(subtotal_eur * (value / 100.0), 0.0))

def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_upload(file, prefix: str) -> str | None:
    if not file:
        return None
    ensure_upload_dir()
    ext = os.path.splitext(file.name)[1].lower()
    safe_name = f"{prefix}_{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(file.getbuffer())
    return path

# ---------------------------
# Session init
# ---------------------------
def init_session():
    if "auth_phone" not in st.session_state:
        st.session_state.auth_phone = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "otp_code" not in st.session_state:
        st.session_state.otp_code = None
    if "otp_expires_at" not in st.session_state:
        st.session_state.otp_expires_at = None
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

def logout_user():
    st.session_state.auth_phone = None
    st.session_state.user_id = None
    st.session_state.otp_code = None
    st.session_state.otp_expires_at = None

# ---------------------------
# App
# ---------------------------
st.set_page_config(page_title="AfriPay Afrika", layout="wide")
init_db()
ensure_defaults()
ensure_admin()
init_session()

# Settings
rate = float(get_setting("eur_xaf_rate", "655.957"))
commission_mode = get_setting("commission_mode", "percent")
commission_value = float(get_setting("commission_value", "10"))
pay_instructions = get_setting("momo_payment_instructions", "")

# Sidebar branding + status
st.sidebar.title("AfriPay Afrika")
st.sidebar.caption("MVP — Facilitateur de paiement international (Phase pilote)")

if st.session_state.auth_phone:
    st.sidebar.success(f"Connecté ✅\n\n{st.session_state.auth_phone}")
    if st.sidebar.button("Se déconnecter"):
        logout_user()
        st.rerun()
else:
    st.sidebar.info("Non connecté")

tabs = ["Connexion", "Simuler", "Créer commande", "Mes commandes", "Admin"]
tab = st.sidebar.radio("Menu", tabs, index=0)

# Logo (optional)
logo_path = os.path.join("assets", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=160)

st.info(
    "📌 **Transparence** : AfriPay facilite uniquement le **paiement**. "
    "Le client fournit l’adresse de son **agence/transitaire** et gère livraison + dédouanement. "
    "**AfriPay ne reçoit jamais le colis.**"
)

# ---------------------------
# Connexion
# ---------------------------
if tab == "Connexion":
    st.header("Connexion")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("1) Demander OTP (mode test)")
        phone = st.text_input("Téléphone (ex: +2376xxxxxxx)", placeholder="+2376...")
        name = st.text_input("Nom (optionnel)")
        email = st.text_input("Email (optionnel)")

        if st.button("Envoyer OTP"):
            if not valid_phone(phone):
                st.error("Numéro invalide. Format: +2376xxxxxxx ou chiffres (8–15).")
            else:
                otp = str(100000 + int(uuid.uuid4().int % 900000))  # 6 digits
                st.session_state.otp_code = otp
                st.session_state.otp_expires_at = time.time() + 180  # 3 minutes
                # Upsert user now
                user_id = upsert_user(phone.strip(), name.strip(), email.strip())
                st.session_state.user_id = user_id

                st.success("OTP généré (mode test). Expire dans 3 minutes.")
                st.info(f"OTP (test) : **{otp}**")

    with col2:
        st.subheader("2) Valider OTP")
        otp_in = st.text_input("Entrer OTP", max_chars=6)
        if st.button("Se connecter"):
            if not st.session_state.otp_code:
                st.error("Veuillez d'abord demander un OTP.")
            elif time.time() > float(st.session_state.otp_expires_at or 0):
                st.error("OTP expiré. Veuillez renvoyer un OTP.")
                st.session_state.otp_code = None
                st.session_state.otp_expires_at = None
            elif otp_in.strip() != st.session_state.otp_code:
                st.error("OTP incorrect.")
            else:
                st.session_state.auth_phone = phone.strip()
                # Ensure user exists and get ID
                u = get_user_by_phone(st.session_state.auth_phone)
                st.session_state.user_id = int(u["id"])
                st.session_state.otp_code = None
                st.session_state.otp_expires_at = None
                st.success("Connecté ✅")
                st.rerun()

    st.divider()
    st.subheader("Statut session")
    if st.session_state.auth_phone:
        u = get_user_by_phone(st.session_state.auth_phone)
        st.write(f"Connecté en tant que : **{u['phone']}**  ({u['name'] or 'sans nom'})")
    else:
        st.write("Non connecté.")

# ---------------------------
# Simuler
# ---------------------------
elif tab == "Simuler":
    st.header("Simulation du coût total")
    st.caption("Prix produit + **frais vendeur (site)** + **frais de service AfriPay**.")

    colA, colB = st.columns([1, 1], gap="large")

    with colA:
        price_eur = st.number_input("Prix du produit (EUR)", min_value=0.0, value=50.0, step=1.0)
        vendor_fee_eur = st.number_input(
            "Frais vendeur (site) (EUR)",
            min_value=0.0, value=15.0, step=1.0,
            help="Ex : frais appliqués par Amazon/Shein/Temu (livraison du site, taxes du site, etc.)."
        )

        subtotal = price_eur + vendor_fee_eur
        afripay_fee = compute_commission(subtotal, commission_mode, commission_value)
        total_eur = subtotal + afripay_fee

    with colB:
        st.subheader("Résumé")
        st.write(f"Taux EUR → XAF : **{rate:.3f}**")
        st.write(f"Produit : **€ {money_fmt(price_eur)}** (≈ {money_fmt(eur_to_xaf(price_eur, rate))} XAF)")
        st.write(f"Frais vendeur (site) : **€ {money_fmt(vendor_fee_eur)}** (≈ {money_fmt(eur_to_xaf(vendor_fee_eur, rate))} XAF)")

        if commission_mode == "percent":
            st.write(f"Frais de service AfriPay ({commission_value:.2f}%) : **€ {money_fmt(afripay_fee)}** (≈ {money_fmt(eur_to_xaf(afripay_fee, rate))} XAF)")
        else:
            st.write(f"Frais de service AfriPay (fixe) : **€ {money_fmt(afripay_fee)}** (≈ {money_fmt(eur_to_xaf(afripay_fee, rate))} XAF)")

        st.success(f"Total à payer : **€ {money_fmt(total_eur)}** (≈ **{money_fmt(eur_to_xaf(total_eur, rate))} XAF**)")
        st.info(pay_instructions)

# ---------------------------
# Créer commande
# ---------------------------
elif tab == "Créer commande":
    st.header("Créer une commande")

    if not st.session_state.auth_phone:
        st.warning("Veuillez d'abord vous connecter (onglet Connexion).")
        st.stop()

    user = get_user_by_phone(st.session_state.auth_phone)
    user_id = int(user["id"])

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        site_name = st.selectbox("Site marchand", ["Amazon", "Shein", "Temu", "AliExpress", "Autre"])
        product_url = st.text_input("Lien du produit", placeholder="https://...")
        product_title = st.text_input("Titre du produit (optionnel)")
        product_specs = st.text_area("Référence / Détails (obligatoire)", placeholder="Couleur, taille, modèle, SKU, etc.")
        price_eur = st.number_input("Prix du produit (EUR)", min_value=0.0, value=0.0, step=1.0)
        vendor_fee_eur = st.number_input("Frais vendeur (site) (EUR)", min_value=0.0, value=0.0, step=1.0)

        st.subheader("Adresse agence / transitaire (obligatoire)")
        delivery_address = st.text_area(
            "Adresse complète (celle que le client mettra sur Amazon/Shein/Temu)",
            placeholder="Nom agence/transitaire, ville, quartier, rue, repères, téléphone..."
        )

        client_ack = st.checkbox("Je confirme que cette adresse est valide et que je gère livraison + dédouanement.")

        momo_provider = st.selectbox("Mobile Money", ["MTN", "Orange", "Autre"])
        momo_tx_id = st.text_input("Référence / TX ID Mobile Money (optionnel)", placeholder="Si le client a déjà payé")

        st.subheader("Preuves (optionnel)")
        payment_proof = st.file_uploader("Preuve de paiement (image/pdf)", type=["png", "jpg", "jpeg", "pdf"])
        purchase_proof = st.file_uploader("Preuve d'achat / facture (image/pdf)", type=["png", "jpg", "jpeg", "pdf"])

    subtotal = price_eur + vendor_fee_eur
    afripay_fee = compute_commission(subtotal, commission_mode, commission_value)
    total_eur = subtotal + afripay_fee
    total_xaf = eur_to_xaf(total_eur, rate)

    with col2:
        st.subheader("Total & instructions")
        st.write(f"Taux EUR → XAF : **{rate:.3f}**")
        st.write(f"Produit : € {money_fmt(price_eur)}  |  ≈ {money_fmt(eur_to_xaf(price_eur, rate))} XAF")
        st.write(f"Frais vendeur (site) : € {money_fmt(vendor_fee_eur)}  |  ≈ {money_fmt(eur_to_xaf(vendor_fee_eur, rate))} XAF")
        st.write(f"Frais de service AfriPay : € {money_fmt(afripay_fee)}  |  ≈ {money_fmt(eur_to_xaf(afripay_fee, rate))} XAF")
        st.success(f"Total à payer : **€ {money_fmt(total_eur)}** (≈ **{money_fmt(total_xaf)} XAF**)")
        st.info(pay_instructions)

        if st.button("Créer la commande"):
            if not product_url.strip().startswith("http"):
                st.error("Veuillez saisir un lien valide (http/https).")
            elif price_eur <= 0:
                st.error("Veuillez saisir un prix produit > 0.")
            elif not product_specs.strip():
                st.error("Veuillez renseigner les références / détails du produit (obligatoire).")
            elif not delivery_address.strip():
                st.error("Adresse agence/transitaire obligatoire.")
            elif not client_ack:
                st.error("Veuillez confirmer que vous gérez livraison + dédouanement.")
            else:
                payment_proof_path = save_upload(payment_proof, "payment") if payment_proof else None
                purchase_proof_path = save_upload(purchase_proof, "purchase") if purchase_proof else None

                ref = create_order(
                    user_id=user_id,
                    site_name=site_name,
                    product_url=product_url.strip(),
                    product_title=product_title.strip(),
                    product_specs=product_specs.strip(),
                    product_price_eur=float(price_eur),
                    vendor_fee_eur=float(vendor_fee_eur),
                    commission_eur=float(afripay_fee),
                    total_eur=float(total_eur),
                    eur_xaf_rate_used=float(rate),
                    total_xaf=float(total_xaf),
                    delivery_address=delivery_address.strip(),
                    client_ack=1,
                    momo_provider=momo_provider,
                    momo_tx_id=momo_tx_id.strip() or None,
                    payment_proof_path=payment_proof_path,
                    purchase_proof_path=purchase_proof_path,
                )

                st.success("Commande créée ✅")
                st.write("Référence de paiement (à mettre dans le message Mobile Money) :")
                st.code(ref)
                st.info("Tracking : il sera ajouté par l’Admin quand disponible (site marchand / transitaire).")

# ---------------------------
# Mes commandes
# ---------------------------
elif tab == "Mes commandes":
    st.header("Mes commandes")

    if not st.session_state.auth_phone:
        st.warning("Veuillez d'abord vous connecter.")
        st.stop()

    user = get_user_by_phone(st.session_state.auth_phone)
    user_id = int(user["id"])
    orders = list_orders_for_user(user_id)

    if not orders:
        st.info("Aucune commande pour le moment.")
    else:
        for o in orders:
            st.subheader(f"Commande #{o['id']} — {o['order_status'].upper()} / Paiement: {o['payment_status'].upper()}")
            st.write(f"**Référence paiement :** `{o['payment_reference']}`")
            st.write(f"**Site :** {o['site_name'] or '-'}")
            st.write(f"**Lien :** {o['product_url']}")
            if o["product_title"]:
                st.write(f"**Produit :** {o['product_title']}")
            st.write(f"**Références / détails :** {o['product_specs']}")
            st.write(f"**Adresse agence/transitaire :** {o['delivery_address']}")

            st.write(
                f"**Total :** € {money_fmt(o['total_to_pay_eur'])} "
                f"(≈ {money_fmt(o['total_to_pay_xaf'])} XAF)"
            )

            # Tracking block
            if o["tracking_number"] or o["tracking_url"]:
                st.markdown("**Tracking :**")
                if o["tracking_number"]:
                    st.code(o["tracking_number"])
                if o["tracking_url"]:
                    st.write(o["tracking_url"])
            else:
                st.caption("Tracking non renseigné (sera ajouté par l’Admin).")

            st.caption(f"Créée: {o['created_at']} | MAJ: {o['updated_at']}")
            st.divider()

# ---------------------------
# Admin
# ---------------------------
elif tab == "Admin":
    st.header("Admin")

    if not st.session_state.is_admin:
        pw = st.text_input("Mot de passe admin", type="password")
        if st.button("Se connecter (admin)"):
            if admin_verify(pw):
                st.session_state.is_admin = True
                st.success("Admin connecté ✅")
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.caption("Conseil : change le mot de passe admin une fois connecté.")
        st.stop()

    st.success("Dashboard Admin")

    # Metrics
    all_orders = list_all_orders(limit=2000)
    nb_orders = len(all_orders)
    total_ca = sum(float(o["total_to_pay_eur"]) for o in all_orders) if all_orders else 0.0
    total_comm = sum(float(o["commission_eur"]) for o in all_orders) if all_orders else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Commandes", nb_orders)
    c2.metric("CA total (EUR)", money_fmt(total_ca))
    c3.metric("Frais AfriPay (EUR)", money_fmt(total_comm))

    st.divider()

    st.subheader("Paramètres")
    colP1, colP2, colP3 = st.columns([1, 1, 1], gap="large")

    with colP1:
        new_rate = st.number_input("Taux EUR → XAF", min_value=1.0, value=float(rate), step=1.0)
        if st.button("Enregistrer taux"):
            set_setting("eur_xaf_rate", str(new_rate))
            st.success("Taux mis à jour.")
            st.rerun()

    with colP2:
        mode = st.selectbox("Mode commission", ["percent", "fixed"], index=0 if commission_mode == "percent" else 1)
        val = st.number_input("Valeur commission (%, ou EUR si fixed)", min_value=0.0, value=float(commission_value), step=0.5)
        if st.button("Enregistrer commission"):
            set_setting("commission_mode", mode)
            set_setting("commission_value", str(val))
            st.success("Commission mise à jour.")
            st.rerun()

    with colP3:
        new_pw = st.text_input("Nouveau mot de passe admin", type="password", placeholder="Min 8 caractères")
        new_pw2 = st.text_input("Confirmer", type="password")
        if st.button("Changer mot de passe"):
            if len(new_pw.strip()) < 8:
                st.error("Mot de passe trop court (min 8).")
            elif new_pw.strip() != new_pw2.strip():
                st.error("Confirmation différente.")
            else:
                admin_set_password(new_pw.strip())
                st.success("Mot de passe admin modifié ✅")

    st.subheader("Instructions paiement (affichées aux clients)")
    instr = st.text_area("Texte instructions", value=pay_instructions, height=120)
    if st.button("Enregistrer instructions"):
        set_setting("momo_payment_instructions", instr)
        st.success("Instructions mises à jour.")
        st.rerun()

    st.divider()
    st.subheader("Commandes (admin)")

    if not all_orders:
        st.info("Aucune commande.")
        st.stop()

    # Filters
    fcol1, fcol2, fcol3 = st.columns([1, 1, 1], gap="large")
    with fcol1:
        status_filter = st.selectbox("Filtre order_status", ["(tous)", "created", "paid", "ordered", "shipped", "closed"])
    with fcol2:
        pay_filter = st.selectbox("Filtre payment_status", ["(tous)", "pending", "confirmed"])
    with fcol3:
        search_ref = st.text_input("Recherche ref paiement (AFR-...)", placeholder="AFR-....").strip().upper()

    filtered = []
    for o in all_orders:
        if status_filter != "(tous)" and o["order_status"] != status_filter:
            continue
        if pay_filter != "(tous)" and o["payment_status"] != pay_filter:
            continue
        if search_ref and search_ref not in o["payment_reference"]:
            continue
        filtered.append(o)

    st.caption(f"{len(filtered)} commande(s) affichée(s).")

    for o in filtered:
        with st.expander(f"#{o['id']} | {o['user_phone']} | {o['order_status']} / {o['payment_status']} | {o['payment_reference']}"):
            st.write(f"**Client:** {o['user_name'] or ''} ({o['user_phone']})")
            st.write(f"**Site:** {o['site_name'] or '-'}")
            st.write(f"**Lien:** {o['product_url']}")
            if o["product_title"]:
                st.write(f"**Produit:** {o['product_title']}")
            st.write(f"**Références / détails:** {o['product_specs']}")
            st.write(f"**Adresse agence/transitaire:** {o['delivery_address']}")

            st.write(
                f"**Total:** € {money_fmt(o['total_to_pay_eur'])} "
                f"(≈ {money_fmt(o['total_to_pay_xaf'])} XAF)"
            )

            st.markdown("### Mise à jour (Admin)")
            c1, c2, c3 = st.columns([1, 1, 1], gap="large")

            with c1:
                new_pay_status = st.selectbox(
                    "payment_status",
                    ["pending", "confirmed"],
                    index=0 if o["payment_status"] == "pending" else 1,
                    key=f"pay_{o['id']}"
                )
                momo_tx_id = st.text_input("Mobile Money TX ID", value=o["momo_tx_id"] or "", key=f"tx_{o['id']}")

            with c2:
                new_order_status = st.selectbox(
                    "order_status",
                    ["created", "paid", "ordered", "shipped", "closed"],
                    index=["created", "paid", "ordered", "shipped", "closed"].index(o["order_status"]),
                    key=f"ord_{o['id']}"
                )
                momo_provider = st.selectbox(
                    "Provider",
                    ["MTN", "Orange", "Autre"],
                    index=["MTN", "Orange", "Autre"].index(o["momo_provider"] or "Autre"),
                    key=f"prov_{o['id']}"
                )

            with c3:
                tracking_number = st.text_input("Tracking number", value=o["tracking_number"] or "", key=f"trk_{o['id']}")
                tracking_url = st.text_input("Tracking URL", value=o["tracking_url"] or "", key=f"trku_{o['id']}")

            if st.button("Enregistrer MAJ", key=f"save_{o['id']}"):
                update_order(
                    o["id"],
                    payment_status=new_pay_status,
                    order_status=new_order_status,
                    momo_tx_id=momo_tx_id.strip() or None,
                    momo_provider=momo_provider,
                    tracking_number=tracking_number.strip() or None,
                    tracking_url=tracking_url.strip() or None,
                )
                st.success("Mis à jour ✅")
                st.rerun()

    st.divider()
    if st.button("Se déconnecter (admin)"):
        st.session_state.is_admin = False
        st.rerun()