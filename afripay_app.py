# afripay_app.py
# AfriPay v1.1 - Paiement pur (Cameroun test) + Réalité terrain (Agence/Transitaire obligatoire)
# Streamlit + SQLite, un seul fichier
#
# Run:
#   pip install streamlit
#   streamlit run afripay_app.py

import os
import re
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime

import streamlit as st

# ---------------------------
# Config
# ---------------------------
DB_PATH = os.environ.get("AFRIPAY_DB_PATH", "afripay.db")
UPLOAD_DIR = os.environ.get("AFRIPAY_UPLOAD_DIR", "uploads")
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

# En prod: mets un vrai mot de passe via variable d'env AFRIPAY_ADMIN_PASSWORD
ADMIN_PASSWORD_ENV = os.environ.get("AFRIPAY_ADMIN_PASSWORD", "")

# ---------------------------
# DB helpers
# ---------------------------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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

        site_name TEXT,                 -- Amazon / Temu / Shein / AliExpress / Other
        product_url TEXT NOT NULL,
        product_title TEXT,
        product_specs TEXT NOT NULL,    -- references, size, color, variant, qty (client)
        product_image_path TEXT,        -- upload image/capture produit (client)

        product_price_eur REAL NOT NULL,
        shipping_estimate_eur REAL NOT NULL,
        commission_eur REAL NOT NULL,
        total_to_pay_eur REAL NOT NULL,

        eur_xaf_rate_used REAL NOT NULL,
        total_to_pay_xaf REAL NOT NULL,

        delivery_address TEXT NOT NULL, -- adresse de livraison saisie (agence/transitaire/contact)
        delivery_agent TEXT,            -- nom agence/transitaire/contact (obligatoire côté UI)
        client_ack INTEGER NOT NULL,    -- 1 si conditions acceptées

        payment_reference TEXT UNIQUE NOT NULL,
        payment_status TEXT NOT NULL,   -- pending / confirmed
        momo_provider TEXT,             -- MTN / Orange / Other
        momo_tx_id TEXT,                -- ref client (optionnel)
        payment_proof_path TEXT,        -- upload preuve paiement (client)

        purchase_proof_path TEXT,       -- preuve d'achat (admin)
        tracking_number TEXT,
        tracking_url TEXT,

        order_status TEXT NOT NULL,     -- created / paid / ordered / shipped / closed

        -- Observations client (data future, optionnel)
        customs_fees_xaf REAL,
        customs_notes TEXT,

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

    # Index utiles
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_payment_reference ON orders(payment_reference)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_order_status ON orders(order_status)")

    conn.commit()
    conn.close()


def ensure_column(conn, table: str, col: str, coldef: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    existing = [r[1] for r in cur.fetchall()]
    if col not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
        conn.commit()


def migrate_db():
    """Safe migrations for existing afripay.db"""
    conn = db()
    ensure_column(conn, "orders", "delivery_agent", "TEXT")
    ensure_column(conn, "orders", "customs_fees_xaf", "REAL")
    ensure_column(conn, "orders", "customs_notes", "TEXT")
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
    # Admin password: env > DB default
    if ADMIN_PASSWORD_ENV.strip():
        set_setting("admin_password", ADMIN_PASSWORD_ENV.strip())
    elif get_setting("admin_password", "") == "":
        set_setting("admin_password", "ChangeMe123!")  # change ASAP in Admin

    if get_setting("eur_xaf_rate", "") == "":
        set_setting("eur_xaf_rate", "655.957")  # EUR->XAF approx peg

    # Commission (confirmée): 10% + minimum 10€
    if get_setting("commission_percent", "") == "":
        set_setting("commission_percent", "10")
    if get_setting("commission_min_eur", "") == "":
        set_setting("commission_min_eur", "10")

    if get_setting("momo_payment_instructions", "") == "":
        set_setting(
            "momo_payment_instructions",
            "Paiement Mobile Money : envoyez le montant exact à notre numéro et mettez la référence AfriPay (AFR-XXXX) dans le message."
        )

    if get_setting("legal_disclaimer", "") == "":
        set_setting(
            "legal_disclaimer",
            "⚠️ AfriPay facilite uniquement le paiement international. "
            "Nous ne sommes pas responsables de la livraison, du transport, des délais, ni des frais de douane. "
            "La réception du colis et les éventuels frais (douane/taxes) sont à la charge du client. "
            "AfriPay ne reçoit jamais le colis."
        )


def upsert_user(phone: str, name: str = "", email: str = "") -> int:
    conn = db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("SELECT id FROM users WHERE phone = ?", (phone,))
    row = cur.fetchone()
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
    cur.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    row = cur.fetchone()
    conn.close()
    return row


def _generate_unique_payment_ref(cur) -> str:
    for _ in range(20):
        ref = f"AFR-{secrets.token_hex(4).upper()}"
        cur.execute("SELECT 1 FROM orders WHERE payment_reference=?", (ref,))
        if not cur.fetchone():
            return ref
    raise RuntimeError("Impossible de générer une référence unique.")


def create_order(
    user_id: int,
    site_name: str,
    product_url: str,
    product_title: str,
    product_specs: str,
    product_image_path: str | None,
    price_eur: float,
    shipping_eur: float,
    commission_eur: float,
    total_eur: float,
    eur_xaf_rate_used: float,
    total_xaf: float,
    delivery_address: str,
    delivery_agent: str,
    momo_provider: str,
    client_ack: int,
) -> str:
    conn = db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    ref = _generate_unique_payment_ref(cur)

    cur.execute("""
        INSERT INTO orders(
            user_id,
            site_name, product_url, product_title, product_specs, product_image_path,
            product_price_eur, shipping_estimate_eur, commission_eur, total_to_pay_eur,
            eur_xaf_rate_used, total_to_pay_xaf,
            delivery_address, delivery_agent, client_ack,
            payment_reference, payment_status, momo_provider,
            order_status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        site_name, product_url, product_title, product_specs, product_image_path,
        price_eur, shipping_eur, commission_eur, total_eur,
        eur_xaf_rate_used, total_xaf,
        delivery_address, delivery_agent, int(client_ack),
        ref, "pending", momo_provider,
        "created",
        now, now
    ))
    conn.commit()
    conn.close()
    return ref


def list_orders_for_user(user_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM orders
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def list_all_orders(limit: int = 200):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.*, u.phone as user_phone, u.name as user_name
        FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_order(order_id: int, **fields):
    if not fields:
        return
    conn = db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    fields["updated_at"] = now
    cols = ", ".join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values()) + [order_id]
    cur.execute(f"UPDATE orders SET {cols} WHERE id = ?", vals)
    conn.commit()
    conn.close()


# ---------------------------
# Utils
# ---------------------------
def valid_phone(phone: str) -> bool:
    p = phone.strip()
    return bool(re.fullmatch(r"(\+?\d{8,15})", p))


def money_fmt(x: float) -> str:
    return f"{x:,.2f}"


def eur_to_xaf(eur: float, rate: float) -> float:
    return eur * rate


def compute_commission(subtotal_eur: float, percent: float, min_eur: float) -> float:
    c = subtotal_eur * (percent / 100.0)
    return max(c, min_eur)


def save_upload(file, subfolder: str, prefix: str) -> str:
    if file is None:
        return ""
    safe_folder = re.sub(r"[^a-zA-Z0-9_\-]", "_", subfolder)
    folder = Path(UPLOAD_DIR) / safe_folder
    folder.mkdir(parents=True, exist_ok=True)

    name = Path(file.name).name
    ext = Path(name).suffix.lower()
    token = secrets.token_hex(6)
    out_name = f"{prefix}_{token}{ext}"
    out_path = folder / out_name

    with open(out_path, "wb") as f:
        f.write(file.getbuffer())

    return str(out_path)


# ---------------------------
# App init
# ---------------------------
st.set_page_config(page_title="AfriPay – Paiement International", layout="wide")
init_db()
ensure_defaults()
migrate_db()

# Session state
if "auth_phone" not in st.session_state:
    st.session_state.auth_phone = None
if "otp_code" not in st.session_state:
    st.session_state.otp_code = None
if "otp_phone" not in st.session_state:
    st.session_state.otp_phone = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Load settings
rate = float(get_setting("eur_xaf_rate", "655.957"))
commission_percent = float(get_setting("commission_percent", "10"))
commission_min_eur = float(get_setting("commission_min_eur", "10"))
pay_instructions = get_setting("momo_payment_instructions", "")
disclaimer = get_setting("legal_disclaimer", "")

# ---------------------------
# Sidebar / Navigation
# ---------------------------
st.sidebar.title("AfriPay")
st.sidebar.caption("Facilitateur de paiement international (test Cameroun)")

if st.session_state.auth_phone:
    if st.sidebar.button("Se déconnecter"):
        st.session_state.auth_phone = None
        st.session_state.otp_code = None
        st.session_state.otp_phone = None
        st.rerun()

tabs = ["Connexion", "Simuler", "Créer commande", "Mes commandes", "Admin"]
tab = st.sidebar.radio("Menu", tabs, index=0)

# Visible disclaimer (important)
st.info(disclaimer)

# Recommended sites (simple, no official partnership claim)
with st.expander("Sites recommandés (non-officiel)"):
    st.write("- Amazon")
    st.write("- Temu")
    st.write("- Shein")
    st.write("- AliExpress")
    st.caption("Note : AfriPay n’est pas un partenaire officiel de ces marques. Nous facilitons uniquement le paiement.")

# ---------------------------
# Connexion (OTP test)
# ---------------------------
if tab == "Connexion":
    st.header("Connexion")
    st.write("Connexion par téléphone (OTP de test affiché).")

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        phone = st.text_input("Téléphone (ex: +2376xxxxxxx)", placeholder="+2376...")
        name = st.text_input("Nom (optionnel)")
        email = st.text_input("Email (optionnel)")
        if st.button("Envoyer OTP"):
            if not valid_phone(phone):
                st.error("Numéro invalide. Utilisez un format type +2376xxxxxxx ou chiffres (8-15).")
            else:
                otp = str(secrets.randbelow(900000) + 100000)
                st.session_state.otp_code = otp
                st.session_state.otp_phone = phone.strip()
                upsert_user(phone.strip(), name=name.strip(), email=email.strip())
                st.success("OTP généré (mode test).")
                st.info(f"OTP (test) : **{otp}**")

    with col2:
        st.subheader("Valider l'OTP")
        otp_in = st.text_input("Entrer OTP", max_chars=6)
        if st.button("Se connecter"):
            if not st.session_state.otp_code or not st.session_state.otp_phone:
                st.error("Veuillez d'abord demander un OTP.")
            elif otp_in.strip() != st.session_state.otp_code:
                st.error("OTP incorrect.")
            else:
                st.session_state.auth_phone = st.session_state.otp_phone
                st.session_state.otp_code = None
                st.session_state.otp_phone = None
                st.success("Connecté ✅")

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
    st.caption("Transparence: EUR + XAF (taux modifiable côté Admin).")

    colA, colB = st.columns([1, 1], gap="large")
    with colA:
        price_eur = st.number_input("Prix produit (EUR)", min_value=0.0, value=50.0, step=1.0)
        shipping_eur = st.number_input("Livraison estimée (EUR)", min_value=0.0, value=15.0, step=1.0)
        subtotal = price_eur + shipping_eur
        commission_eur = compute_commission(subtotal, commission_percent, commission_min_eur)
        total_eur = subtotal + commission_eur

    with colB:
        st.subheader("Résumé")
        st.write(f"Taux EUR → XAF : **{rate:.3f}**")
        st.write(f"Commission : **{commission_percent:.2f}%** (minimum **€ {money_fmt(commission_min_eur)}**)")
        st.write(f"Produit : **€ {money_fmt(price_eur)}** (≈ {money_fmt(eur_to_xaf(price_eur, rate))} XAF)")
        st.write(f"Livraison : **€ {money_fmt(shipping_eur)}** (≈ {money_fmt(eur_to_xaf(shipping_eur, rate))} XAF)")
        st.write(f"Commission : **€ {money_fmt(commission_eur)}** (≈ {money_fmt(eur_to_xaf(commission_eur, rate))} XAF)")
        st.success(f"Total à payer : **€ {money_fmt(total_eur)}** (≈ **{money_fmt(eur_to_xaf(total_eur, rate))} XAF**)")
        st.info(pay_instructions)

# ---------------------------
# Créer commande
# ---------------------------
elif tab == "Créer commande":
    st.header("Créer une commande (Paiement pur)")
    st.caption("Nous passons l’achat uniquement après validation du paiement Mobile Money.")
    if not st.session_state.auth_phone:
        st.warning("Veuillez d'abord vous connecter (onglet Connexion).")
        st.stop()

    user = get_user_by_phone(st.session_state.auth_phone)
    user_id = int(user["id"])

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        site_name = st.selectbox("Site", ["Amazon", "Temu", "Shein", "AliExpress", "Autre"])
        product_url = st.text_input("Lien du produit", placeholder="https://...")
        product_title = st.text_input("Titre produit (optionnel)")
        product_specs = st.text_area(
            "Références produit (OBLIGATOIRE)",
            placeholder="Copie les infos exactes du site : SKU/référence, taille, couleur, variante, quantité, etc.",
            height=120
        )
        product_image = st.file_uploader(
            "Image/capture du produit (optionnel mais recommandé)",
            type=["png", "jpg", "jpeg", "webp"]
        )

        price_eur = st.number_input("Prix produit (EUR)", min_value=0.0, value=0.0, step=1.0)
        shipping_eur = st.number_input("Frais de livraison du site (EUR)", min_value=0.0, value=0.0, step=1.0)

        momo_provider = st.selectbox("Mobile Money", ["MTN", "Orange", "Autre"])

        st.subheader("Livraison (gérée par le client)")
        delivery_agent = st.text_input(
            "Agence / Transitaire / Contact utilisé (OBLIGATOIRE)",
            placeholder="Ex: Agence X (Douala), Transitaire Y, Nom du contact + téléphone..."
        )
        delivery_address = st.text_area(
            "Adresse exacte à saisir sur le site vendeur (OBLIGATOIRE)",
            placeholder="Adresse complète (celle de l’agence/transitaire/contact) : nom, quartier, ville, téléphone…",
            height=90
        )
        st.caption("⚠️ AfriPay ne reçoit jamais le colis. L’adresse saisie doit être celle de votre agence/transitaire/contact.")

    subtotal = price_eur + shipping_eur
    commission_eur = compute_commission(subtotal, commission_percent, commission_min_eur)
    total_eur = subtotal + commission_eur
    total_xaf = eur_to_xaf(total_eur, rate)

    with col2:
        st.subheader("Total & conditions (OBLIGATOIRES)")
        st.write(f"Taux EUR → XAF : **{rate:.3f}**")
        st.write(f"Commission : **{commission_percent:.2f}%** (min **€ {money_fmt(commission_min_eur)}**)")
        st.write(f"Sous-total (produit+livraison) : **€ {money_fmt(subtotal)}**")
        st.write(f"Commission : **€ {money_fmt(commission_eur)}**")
        st.success(f"Total à payer : **€ {money_fmt(total_eur)}** (≈ **{money_fmt(total_xaf)} XAF**)")

        st.divider()
        st.caption("Avant de payer, vous devez confirmer les points suivants :")
        ack1 = st.checkbox("Je confirme que le site peut livrer au Cameroun (ou que j’assume la livraison).", value=False)
        ack2 = st.checkbox("Je comprends que la livraison, les délais et les frais de douane sont sous ma responsabilité.", value=False)
        ack3 = st.checkbox("Je comprends que la commission AfriPay n’est pas remboursable.", value=False)
        ack4 = st.checkbox("Je confirme que les références saisies (taille/couleur/variante) sont exactes.", value=False)
        ack5 = st.checkbox("Je comprends que AfriPay ne reçoit jamais le colis.", value=False)
        ack6 = st.checkbox("Je confirme que l’adresse saisie appartient à mon agence/transitaire/contact et qu’elle est valide.", value=False)

        st.info(pay_instructions)

        can_create = (
            product_url.strip().startswith("http")
            and price_eur > 0
            and len(product_specs.strip()) >= 5
            and len(delivery_agent.strip()) >= 3
            and len(delivery_address.strip()) >= 10
            and ack1 and ack2 and ack3 and ack4 and ack5 and ack6
        )

        if st.button("Créer la commande", disabled=not can_create):
            product_image_path = None
            if product_image is not None:
                product_image_path = save_upload(product_image, subfolder=f"user_{user_id}", prefix="product")

            ref = create_order(
                user_id=user_id,
                site_name=site_name,
                product_url=product_url.strip(),
                product_title=product_title.strip(),
                product_specs=product_specs.strip(),
                product_image_path=product_image_path,
                price_eur=float(price_eur),
                shipping_eur=float(shipping_eur),
                commission_eur=float(commission_eur),
                total_eur=float(total_eur),
                eur_xaf_rate_used=float(rate),
                total_xaf=float(total_xaf),
                delivery_address=delivery_address.strip(),
                delivery_agent=delivery_agent.strip(),
                momo_provider=momo_provider,
                client_ack=1
            )
            st.success("Commande créée ✅")
            st.write("Référence de paiement (à mettre dans le message Mobile Money) :")
            st.code(ref)
            st.write("Après paiement, ajoutez votre **preuve de paiement** dans l’onglet **Mes commandes**.")
            st.warning("⚠️ Aucune opération d’achat ne sera déclenchée tant que le paiement n’est pas validé par l’admin.")

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
            status_line = f"{o['order_status'].upper()} / Paiement: {o['payment_status'].upper()}"
            with st.expander(f"Commande #{o['id']} — {status_line} — {o['payment_reference']}"):
                st.write(f"**Site :** {o['site_name'] or '-'}")
                st.write(f"**Lien :** {o['product_url']}")
                if o["product_title"]:
                    st.write(f"**Titre :** {o['product_title']}")
                st.write("**Références produit (client) :**")
                st.code(o["product_specs"])

                if o["product_image_path"]:
                    try:
                        st.image(o["product_image_path"], caption="Image produit (upload client)", use_container_width=True)
                    except Exception:
                        st.write(f"Image produit: {o['product_image_path']}")

                st.divider()
                st.subheader("Livraison (client)")
                st.write(f"**Agence/Transitaire/Contact :** {o['delivery_agent'] or '-'}")
                st.write(f"**Adresse de livraison :** {o['delivery_address']}")

                st.write(
                    f"**Total :** € {money_fmt(o['total_to_pay_eur'])} "
                    f"(≈ {money_fmt(o['total_to_pay_xaf'])} XAF) | "
                    f"Taux utilisé: {o['eur_xaf_rate_used']:.3f}"
                )

                st.divider()
                st.subheader("Paiement")
                st.write(f"**Référence paiement :** `{o['payment_reference']}`")
                st.write(f"**Provider :** {o['momo_provider'] or '-'}")

                momo_tx = st.text_input(
                    "Référence/Transaction MoMo (optionnel)",
                    value=o["momo_tx_id"] or "",
                    key=f"momo_tx_{o['id']}"
                )

                proof = st.file_uploader(
                    "Preuve de paiement (photo/screenshot) (optionnel mais recommandé)",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"payproof_{o['id']}"
                )

                if st.button("Enregistrer paiement / preuve", key=f"savepay_{o['id']}"):
                    fields = {}
                    if momo_tx.strip():
                        fields["momo_tx_id"] = momo_tx.strip()
                    if proof is not None:
                        p = save_upload(proof, subfolder=f"order_{o['id']}", prefix="payment_proof")
                        fields["payment_proof_path"] = p
                    if fields:
                        update_order(o["id"], **fields)
                        st.success("Enregistré ✅")
                        st.rerun()
                    else:
                        st.info("Rien à enregistrer.")

                if o["payment_proof_path"]:
                    st.write("**Preuve paiement enregistrée :**")
                    try:
                        st.image(o["payment_proof_path"], caption="Preuve de paiement", use_container_width=True)
                    except Exception:
                        st.write(o["payment_proof_path"])

                st.divider()
                st.subheader("Suivi (fourni après achat)")
                if o["purchase_proof_path"]:
                    st.write("**Preuve d'achat :**")
                    st.write(o["purchase_proof_path"])
                else:
                    st.caption("Preuve d'achat non encore fournie.")

                if o["tracking_number"]:
                    st.write(f"**Tracking :** `{o['tracking_number']}`")
                if o["tracking_url"]:
                    st.write(f"**Lien tracking :** {o['tracking_url']}")

                st.divider()
                st.subheader("Observations (optionnel)")
                st.caption("Ces infos servent à mieux comprendre les coûts/délais pour une future logistique (hub/cargo).")
                customs_fee = st.number_input(
                    "Frais de douane payés (XAF) (optionnel)",
                    min_value=0.0,
                    value=float(o["customs_fees_xaf"] or 0.0),
                    step=100.0,
                    key=f"custfee_{o['id']}"
                )
                customs_notes = st.text_area(
                    "Notes douane / réception (optionnel)",
                    value=o["customs_notes"] or "",
                    height=70,
                    key=f"custnote_{o['id']}"
                )
                if st.button("Enregistrer observations", key=f"savecust_{o['id']}"):
                    update_order(o["id"], customs_fees_xaf=float(customs_fee), customs_notes=customs_notes.strip())
                    st.success("Observations enregistrées ✅")
                    st.rerun()

                st.caption(f"Créée: {o['created_at']} | MAJ: {o['updated_at']}")

# ---------------------------
# Admin
# ---------------------------
elif tab == "Admin":
    st.header("Admin")
    admin_password = get_setting("admin_password", "ChangeMe123!")

    if not st.session_state.is_admin:
        pw = st.text_input("Mot de passe admin", type="password")
        if st.button("Se connecter (admin)"):
            if pw == admin_password:
                st.session_state.is_admin = True
                st.success("Admin connecté ✅")
            else:
                st.error("Mot de passe incorrect.")
        st.caption("Conseil: change le mot de passe admin dès maintenant si tu déploies.")
        st.stop()

    st.success("Espace Admin")
    st.write("Paramètres & gestion des commandes (paiement pur).")

    st.subheader("Paramètres")
    colP1, colP2, colP3 = st.columns([1, 1, 1], gap="large")
    with colP1:
        new_rate = st.number_input("Taux EUR → XAF", min_value=1.0, value=float(rate), step=1.0)
        if st.button("Enregistrer taux"):
            set_setting("eur_xaf_rate", str(new_rate))
            st.success("Taux mis à jour.")
            st.rerun()

    with colP2:
        new_percent = st.number_input("Commission %", min_value=0.0, value=float(commission_percent), step=0.5)
        new_min = st.number_input("Minimum commission (EUR)", min_value=0.0, value=float(commission_min_eur), step=1.0)
        if st.button("Enregistrer commission"):
            set_setting("commission_percent", str(new_percent))
            set_setting("commission_min_eur", str(new_min))
            st.success("Commission mise à jour.")
            st.rerun()

    with colP3:
        new_pw = st.text_input("Nouveau mot de passe admin", type="password", placeholder="ChangeMe...")
        if st.button("Changer mot de passe"):
            if len(new_pw.strip()) < 8:
                st.error("Mot de passe trop court (min 8).")
            else:
                set_setting("admin_password", new_pw.strip())
                st.success("Mot de passe admin modifié.")

    st.subheader("Instructions paiement (affichées aux clients)")
    instr = st.text_area("Texte instructions", value=pay_instructions, height=90)
    if st.button("Enregistrer instructions"):
        set_setting("momo_payment_instructions", instr)
        st.success("Instructions mises à jour.")
        st.rerun()

    st.subheader("Disclaimer légal (très important)")
    dis = st.text_area("Texte disclaimer", value=disclaimer, height=110)
    if st.button("Enregistrer disclaimer"):
        set_setting("legal_disclaimer", dis)
        st.success("Disclaimer mis à jour.")
        st.rerun()

    st.divider()
    st.subheader("Commandes")
    orders = list_all_orders(limit=200)
    if not orders:
        st.info("Aucune commande.")
        st.stop()

    f1, f2, f3 = st.columns([1, 1, 1], gap="large")
    with f1:
        pay_filter = st.selectbox("Filtre payment_status", ["(tous)", "pending", "confirmed"])
    with f2:
        status_filter = st.selectbox("Filtre order_status", ["(tous)", "created", "paid", "ordered", "shipped", "closed"])
    with f3:
        search_ref = st.text_input("Recherche ref paiement (AFR-...)", placeholder="AFR-....").strip().upper()

    filtered = []
    for o in orders:
        if pay_filter != "(tous)" and o["payment_status"] != pay_filter:
            continue
        if status_filter != "(tous)" and o["order_status"] != status_filter:
            continue
        if search_ref and search_ref not in o["payment_reference"]:
            continue
        filtered.append(o)

    st.caption(f"{len(filtered)} commande(s) affichée(s).")

    for o in filtered:
        title = f"#{o['id']} | {o['user_phone']} | {o['payment_status']} | {o['order_status']} | {o['payment_reference']}"
        with st.expander(title):
            st.write(f"**Client:** {o['user_name'] or ''} ({o['user_phone']})")
            st.write(f"**Site:** {o['site_name'] or '-'}")
            st.write(f"**Lien:** {o['product_url']}")
            if o["product_title"]:
                st.write(f"**Titre:** {o['product_title']}")
            st.write("**Specs client:**")
            st.code(o["product_specs"])

            st.divider()
            st.subheader("Livraison (client)")
            st.write(f"**Agence/Transitaire/Contact:** {o['delivery_agent'] or '-'}")
            st.write(f"**Adresse livraison:** {o['delivery_address']}")

            if o["product_image_path"]:
                try:
                    st.image(o["product_image_path"], caption="Image produit (client)", use_container_width=True)
                except Exception:
                    st.write(o["product_image_path"])

            st.write(
                f"**Total:** € {money_fmt(o['total_to_pay_eur'])} "
                f"(≈ {money_fmt(o['total_to_pay_xaf'])} XAF) | "
                f"Taux utilisé: {o['eur_xaf_rate_used']:.3f}"
            )

            st.divider()
            c1, c2 = st.columns([1, 1], gap="large")
            with c1:
                st.subheader("Paiement")
                new_pay_status = st.selectbox(
                    "payment_status",
                    ["pending", "confirmed"],
                    index=0 if o["payment_status"] == "pending" else 1,
                    key=f"pay_{o['id']}"
                )
                momo_tx_id = st.text_input("MoMo TX ID (client)", value=o["momo_tx_id"] or "", key=f"tx_{o['id']}")
                if o["payment_proof_path"]:
                    st.write("Preuve paiement :")
                    try:
                        st.image(o["payment_proof_path"], use_container_width=True)
                    except Exception:
                        st.write(o["payment_proof_path"])
                else:
                    st.caption("Aucune preuve paiement enregistrée.")

            with c2:
                st.subheader("Après achat (admin)")
                new_order_status = st.selectbox(
                    "order_status",
                    ["created", "paid", "ordered", "shipped", "closed"],
                    index=["created", "paid", "ordered", "shipped", "closed"].index(o["order_status"]),
                    key=f"ord_{o['id']}"
                )

                purchase_proof = st.file_uploader(
                    "Preuve d'achat (optionnel)",
                    type=["png", "jpg", "jpeg", "webp", "pdf"],
                    key=f"buyproof_{o['id']}"
                )
                tracking_number = st.text_input("Tracking number", value=o["tracking_number"] or "", key=f"trk_{o['id']}")
                tracking_url = st.text_input("Lien tracking", value=o["tracking_url"] or "", key=f"trku_{o['id']}")

            # Business rule: si paiement confirmé et status encore created -> set paid
            if new_pay_status == "confirmed" and new_order_status == "created":
                new_order_status = "paid"

            if st.button("Enregistrer MAJ", key=f"save_{o['id']}"):
                fields = {
                    "payment_status": new_pay_status,
                    "order_status": new_order_status,
                    "momo_tx_id": momo_tx_id.strip() or None,
                }
                if purchase_proof is not None:
                    p = save_upload(purchase_proof, subfolder=f"order_{o['id']}", prefix="purchase_proof")
                    fields["purchase_proof_path"] = p
                fields["tracking_number"] = tracking_number.strip() or None
                fields["tracking_url"] = tracking_url.strip() or None

                update_order(o["id"], **fields)
                st.success("Mis à jour ✅")
                st.rerun()

            st.divider()
            st.subheader("Data douane (observations)")
            st.write(f"Frais douane (XAF): {money_fmt(float(o['customs_fees_xaf'] or 0.0))}")
            if o["customs_notes"]:
                st.write(o["customs_notes"])

            st.caption(f"Créée: {o['created_at']} | MAJ: {o['updated_at']}")

    st.divider()
    if st.button("Se déconnecter (admin)"):
        st.session_state.is_admin = False
        st.rerun()