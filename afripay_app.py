# afripay_app.py
# AfriPay Afrika v1.2 — Facilitateur de paiement (Pilot Cameroun)
# Streamlit + SQLite
#
# Run:
#   pip install -r requirements.txt
#   streamlit run afripay_app.py

import os
import re
import sqlite3
import secrets
from datetime import datetime

import streamlit as st

DB_PATH = os.getenv("AFRIPAY_DB_PATH", "afripay.db")
LOGO_PATH = os.getenv("AFRIPAY_LOGO_PATH", "assets/logo.png")

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

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        name TEXT,
        email TEXT,
        created_at TEXT NOT NULL
    )
    """
    )

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,

        product_url TEXT NOT NULL,
        product_title TEXT,

        product_price_eur REAL NOT NULL,
        vendor_shipping_eur REAL NOT NULL,          -- frais du vendeur (livraison du site)
        afripay_fee_eur REAL NOT NULL,              -- frais de service AfriPay (commission)
        total_to_pay_eur REAL NOT NULL,

        payment_reference TEXT UNIQUE NOT NULL,
        payment_status TEXT NOT NULL,               -- pending / confirmed
        order_status TEXT NOT NULL,                 -- created / paid / ordered / shipped / closed

        momo_provider TEXT,                         -- MTN / Orange / Autre
        momo_tx_id TEXT,                            -- référence/ID transaction client

        delivery_city TEXT,
        agency_name TEXT,                           -- agence / transitaire
        agency_delivery_address TEXT,               -- adresse exacte fournie par l’agence
        customer_ack_delivery INTEGER NOT NULL DEFAULT 0,  -- case à cocher obligatoire

        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,

        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """
    )

    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """
    )

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
    cur.execute(
        """
        INSERT INTO settings(key, value, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """,
        (key, value, now),
    )
    conn.commit()
    conn.close()


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
            (phone, name, email, now),
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


def create_order(
    user_id: int,
    product_url: str,
    product_title: str,
    price_eur: float,
    vendor_shipping_eur: float,
    afripay_fee_eur: float,
    total_eur: float,
    momo_provider: str,
    delivery_city: str,
    agency_name: str,
    agency_delivery_address: str,
    customer_ack_delivery: bool,
    notes: str,
) -> str:
    conn = db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    ref = f"AFR-{secrets.token_hex(4).upper()}"

    cur.execute(
        """
        INSERT INTO orders(
            user_id,
            product_url, product_title,
            product_price_eur, vendor_shipping_eur, afripay_fee_eur, total_to_pay_eur,
            payment_reference, payment_status, order_status,
            momo_provider, momo_tx_id,
            delivery_city, agency_name, agency_delivery_address, customer_ack_delivery,
            notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            user_id,
            product_url,
            product_title,
            price_eur,
            vendor_shipping_eur,
            afripay_fee_eur,
            total_eur,
            ref,
            "pending",
            "created",
            momo_provider,
            None,
            delivery_city,
            agency_name,
            agency_delivery_address,
            1 if customer_ack_delivery else 0,
            notes,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return ref


def list_orders_for_user(user_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
    """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_all_orders(limit: int = 200):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT o.*, u.phone as user_phone, u.name as user_name
        FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.id DESC
        LIMIT ?
    """,
        (limit,),
    )
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


def eur_to_xaf(eur: float, rate: float) -> float:
    return eur * rate


def money_fmt(x: float) -> str:
    return f"{x:,.2f}"


# ---------------------------
# Defaults / settings
# ---------------------------
def ensure_defaults():
    # IMPORTANT: change admin password in Admin panel ASAP (or set AFRIPAY_ADMIN_PASSWORD env var)
    if get_setting("admin_password", "") == "":
        set_setting("admin_password", "ChangeMe123!")  # first boot only

    if get_setting("eur_xaf_rate", "") == "":
        set_setting("eur_xaf_rate", "655.957")

    if get_setting("commission_mode", "") == "":
        set_setting("commission_mode", "percent")  # percent or fixed

    if get_setting("commission_value", "") == "":
        set_setting("commission_value", "10")  # default 10%

    if get_setting("momo_payment_instructions", "") == "":
        set_setting(
            "momo_payment_instructions",
            "Paiement Mobile Money : envoyez le montant exact et indiquez la référence de paiement dans le message.",
        )

    if get_setting("brand_name", "") == "":
        set_setting("brand_name", "AfriPay Afrika")

    if get_setting("pilot_label", "") == "":
        set_setting("pilot_label", "Pilot Cameroun • Paiement international")

    if get_setting("legal_banner", "") == "":
        set_setting(
            "legal_banner",
            "AfriPay facilite uniquement le paiement international. Nous ne sommes pas responsables de la livraison, du transport, des délais, ni des frais de douane. "
            "Le client fournit l’adresse de son agence/transitaire et gère réception + dédouanement.",
        )


def compute_afripay_fee(subtotal_eur: float, mode: str, value: float) -> float:
    if mode == "percent":
        return subtotal_eur * (value / 100.0)
    return float(value)


# ---------------------------
# App
# ---------------------------
st.set_page_config(page_title="AfriPay Afrika", layout="wide")
init_db()
ensure_defaults()

# Session
if "auth_phone" not in st.session_state:
    st.session_state.auth_phone = None
if "otp_code" not in st.session_state:
    st.session_state.otp_code = None
if "otp_phone" not in st.session_state:
    st.session_state.otp_phone = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Load settings
brand_name = get_setting("brand_name", "AfriPay Afrika")
pilot_label = get_setting("pilot_label", "Pilot Cameroun • Paiement international")
legal_banner = get_setting("legal_banner", "")

rate = float(get_setting("eur_xaf_rate", "655.957"))
commission_mode = get_setting("commission_mode", "percent")
commission_value = float(get_setting("commission_value", "10"))
pay_instructions = get_setting("momo_payment_instructions", "")

# Sidebar
st.sidebar.title(brand_name)
st.sidebar.caption(pilot_label)

tabs = ["Connexion", "Simuler", "Créer commande", "Mes commandes", "Admin"]
tab = st.sidebar.radio("Menu", tabs, index=0)

# Header block with logo + banner
col_logo, col_title = st.columns([1, 3], gap="large")
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=220)
with col_title:
    st.markdown(f"# {brand_name}")
    st.caption("Facilitateur de paiement international — Phase pilote (Cameroun)")

if legal_banner:
    st.info(legal_banner)

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
                otp = str(secrets.randbelow(900000) + 100000)  # 6 digits
                st.session_state.otp_code = otp
                st.session_state.otp_phone = phone.strip()

                # Upsert user
                upsert_user(phone.strip(), name=name.strip(), email=email.strip())

                st.success("OTP généré. (Mode test)")
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
    st.caption("Le client paie : prix produit + frais vendeur (si applicable) + frais de service AfriPay.")

    colA, colB = st.columns([1, 1], gap="large")
    with colA:
        price_eur = st.number_input("Prix du produit (EUR)", min_value=0.0, value=50.0, step=1.0)

        # IMPORTANT: on renomme clairement pour éviter la confusion
        vendor_shipping_eur = st.number_input(
            "Frais du vendeur (livraison du site) — optionnel (EUR)",
            min_value=0.0,
            value=15.0,
            step=1.0,
            help="Ce montant correspond aux frais facturés par le site marchand (Amazon/Temu/...). AfriPay ne livre pas.",
        )

        subtotal = price_eur + vendor_shipping_eur
        afripay_fee_eur = compute_afripay_fee(subtotal, commission_mode, commission_value)

        total_eur = subtotal + afripay_fee_eur

    with colB:
        st.subheader("Résumé")
        st.write(f"Taux EUR → XAF : **{rate:.3f}**")

        st.write(f"Produit : **€ {money_fmt(price_eur)}** (≈ {money_fmt(eur_to_xaf(price_eur, rate))} XAF)")
        st.write(
            f"Frais vendeur (livraison du site) : **€ {money_fmt(vendor_shipping_eur)}** "
            f"(≈ {money_fmt(eur_to_xaf(vendor_shipping_eur, rate))} XAF)"
        )

        if commission_mode == "percent":
            fee_label = f"Frais de service AfriPay ({commission_value:.2f}%)"
        else:
            fee_label = "Frais de service AfriPay (fixe)"

        st.write(
            f"{fee_label} : **€ {money_fmt(afripay_fee_eur)}** "
            f"(≈ {money_fmt(eur_to_xaf(afripay_fee_eur, rate))} XAF)"
        )

        st.success(
            f"Total à payer : **€ {money_fmt(total_eur)}** "
            f"(≈ **{money_fmt(eur_to_xaf(total_eur, rate))} XAF**)"
        )

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
        product_url = st.text_input("Lien du produit (Amazon/Temu/AliExpress)", placeholder="https://...")
        product_title = st.text_input("Titre du produit (optionnel)")

        price_eur = st.number_input("Prix du produit (EUR)", min_value=0.0, value=0.0, step=1.0)
        vendor_shipping_eur = st.number_input(
            "Frais du vendeur (livraison du site) — optionnel (EUR)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Frais facturés par le site marchand. AfriPay ne fait pas la livraison.",
        )

        st.subheader("Adresse (agence / transitaire)")
        delivery_city = st.text_input("Ville (Cameroun)", placeholder="Douala, Yaoundé...")
        agency_name = st.text_input("Nom de l’agence / transitaire", placeholder="Ex: DHL Bonanjo / Agence X...")
        agency_delivery_address = st.text_area(
            "Adresse exacte fournie par l’agence / transitaire (obligatoire)",
            placeholder="Adresse complète (quartier, rue, repères, téléphone agence...)",
            height=110,
        )

        customer_ack = st.checkbox(
            "Je confirme que cette adresse est valide et que je gère la livraison et le dédouanement (AfriPay ne reçoit jamais le colis).",
            value=False,
        )

        momo_provider = st.selectbox("Mobile Money", ["MTN", "Orange", "Autre"])
        notes = st.text_area("Notes (optionnel)", placeholder="Couleur, taille, détails...", height=110)

    subtotal = price_eur + vendor_shipping_eur
    afripay_fee_eur = compute_afripay_fee(subtotal, commission_mode, commission_value)
    total_eur = subtotal + afripay_fee_eur

    with col2:
        st.subheader("Total & instructions")
        st.write(f"Taux EUR → XAF : **{rate:.3f}**")
        st.write(f"Produit : € {money_fmt(price_eur)}  |  ≈ {money_fmt(eur_to_xaf(price_eur, rate))} XAF")
        st.write(
            f"Frais vendeur (livraison du site) : € {money_fmt(vendor_shipping_eur)}  |  "
            f"≈ {money_fmt(eur_to_xaf(vendor_shipping_eur, rate))} XAF"
        )

        if commission_mode == "percent":
            fee_label = f"Frais de service AfriPay ({commission_value:.2f}%)"
        else:
            fee_label = "Frais de service AfriPay (fixe)"

        st.write(
            f"{fee_label} : € {money_fmt(afripay_fee_eur)}  |  "
            f"≈ {money_fmt(eur_to_xaf(afripay_fee_eur, rate))} XAF"
        )

        st.success(
            f"Total à payer : **€ {money_fmt(total_eur)}** "
            f"(≈ **{money_fmt(eur_to_xaf(total_eur, rate))} XAF**)"
        )

        st.info(pay_instructions)

        if st.button("Créer la commande"):
            if not product_url.strip().startswith("http"):
                st.error("Veuillez saisir un lien valide (http/https).")
            elif price_eur <= 0:
                st.error("Veuillez saisir un prix produit > 0.")
            elif not agency_delivery_address.strip():
                st.error("Adresse agence/transitaire obligatoire.")
            elif not customer_ack:
                st.error("Veuillez cocher la confirmation (livraison + dédouanement).")
            else:
                ref = create_order(
                    user_id=user_id,
                    product_url=product_url.strip(),
                    product_title=product_title.strip(),
                    price_eur=float(price_eur),
                    vendor_shipping_eur=float(vendor_shipping_eur),
                    afripay_fee_eur=float(afripay_fee_eur),
                    total_eur=float(total_eur),
                    momo_provider=momo_provider,
                    delivery_city=delivery_city.strip(),
                    agency_name=agency_name.strip(),
                    agency_delivery_address=agency_delivery_address.strip(),
                    customer_ack_delivery=customer_ack,
                    notes=notes.strip(),
                )
                st.success("Commande créée ✅")
                st.write("Référence de paiement (à mettre dans le message Mobile Money) :")
                st.code(ref)
                st.write("Après paiement, envoyez votre référence Mobile Money à l’admin pour validation.")

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
            st.write(f"**Lien :** {o['product_url']}")
            if o["product_title"]:
                st.write(f"**Produit :** {o['product_title']}")

            st.write(
                f"**Total :** € {money_fmt(o['total_to_pay_eur'])} "
                f"(≈ {money_fmt(eur_to_xaf(o['total_to_pay_eur'], rate))} XAF)"
            )

            st.caption(
                f"Ville: {o['delivery_city'] or '-'} | Agence: {o['agency_name'] or '-'}"
            )
            st.caption(f"Adresse agence/transitaire: {o['agency_delivery_address'] or '-'}")
            st.caption(f"Créée: {o['created_at']} | MAJ: {o['updated_at']}")
            st.divider()

# ---------------------------
# Admin
# ---------------------------
elif tab == "Admin":
    st.header("Admin")

    # Allow override by env in production
    env_admin_pw = os.getenv("AFRIPAY_ADMIN_PASSWORD")
    admin_password = env_admin_pw if env_admin_pw else get_setting("admin_password", "ChangeMe123!")

    if not st.session_state.is_admin:
        pw = st.text_input("Mot de passe admin", type="password")
        if st.button("Se connecter (admin)"):
            if pw == admin_password:
                st.session_state.is_admin = True
                st.success("Admin connecté ✅")
            else:
                st.error("Mot de passe incorrect.")
        st.caption("Conseil: change le mot de passe admin dans cette page une fois connecté.")
        st.stop()

    st.success("Espace Admin")
    st.write("Paramètres & gestion des commandes.")

    st.subheader("Paramètres")
    colP1, colP2, colP3 = st.columns([1, 1, 1], gap="large")

    with colP1:
        new_rate = st.number_input("Taux EUR → XAF", min_value=1.0, value=float(rate), step=1.0)
        if st.button("Enregistrer taux"):
            set_setting("eur_xaf_rate", str(new_rate))
            st.success("Taux mis à jour.")
            st.rerun()

    with colP2:
        mode = st.selectbox("Mode frais AfriPay", ["percent", "fixed"], index=0 if commission_mode == "percent" else 1)
        val = st.number_input(
            "Valeur (% si percent, ou EUR si fixed)",
            min_value=0.0,
            value=float(commission_value),
            step=0.5,
        )
        if st.button("Enregistrer frais"):
            set_setting("commission_mode", mode)
            set_setting("commission_value", str(val))
            st.success("Frais AfriPay mis à jour.")
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
    instr = st.text_area("Texte instructions", value=pay_instructions, height=120)
    if st.button("Enregistrer instructions"):
        set_setting("momo_payment_instructions", instr)
        st.success("Instructions mises à jour.")
        st.rerun()

    st.subheader("Bannière légale (affichée en haut)")
    banner = st.text_area("Texte bannière", value=legal_banner, height=120)
    if st.button("Enregistrer bannière"):
        set_setting("legal_banner", banner)
        st.success("Bannière mise à jour.")
        st.rerun()

    st.divider()
    st.subheader("Commandes (admin)")

    orders = list_all_orders(limit=200)
    if not orders:
        st.info("Aucune commande.")
        st.stop()

    fcol1, fcol2, fcol3 = st.columns([1, 1, 1], gap="large")
    with fcol1:
        status_filter = st.selectbox("Filtre order_status", ["(tous)", "created", "paid", "ordered", "shipped", "closed"])
    with fcol2:
        pay_filter = st.selectbox("Filtre payment_status", ["(tous)", "pending", "confirmed"])
    with fcol3:
        search_ref = st.text_input("Recherche ref paiement (AFR-...)", placeholder="AFR-....").strip().upper()

    filtered = []
    for o in orders:
        if status_filter != "(tous)" and o["order_status"] != status_filter:
            continue
        if pay_filter != "(tous)" and o["payment_status"] != pay_filter:
            continue
        if search_ref and search_ref not in o["payment_reference"]:
            continue
        filtered.append(o)

    st.caption(f"{len(filtered)} commande(s) affichée(s).")

    for o in filtered:
        with st.expander(
            f"#{o['id']} | {o['user_phone']} | {o['order_status']} / {o['payment_status']} | {o['payment_reference']}"
        ):
            st.write(f"**Client:** {o['user_name'] or ''} ({o['user_phone']})")
            st.write(f"**Lien:** {o['product_url']}")
            if o["product_title"]:
                st.write(f"**Produit:** {o['product_title']}")

            st.write(
                f"**Total:** € {money_fmt(o['total_to_pay_eur'])} "
                f"(≈ {money_fmt(eur_to_xaf(o['total_to_pay_eur'], float(get_setting('eur_xaf_rate','655.957'))))} XAF)"
            )

            st.write(
                f"**Ville:** {o['delivery_city'] or '-'} | **Agence:** {o['agency_name'] or '-'}"
            )
            st.write(f"**Adresse agence/transitaire:** {o['agency_delivery_address'] or '-'}")
            st.write(f"**Confirmation livraison/douane:** {'✅' if o['customer_ack_delivery'] else '❌'}")

            if o["notes"]:
                st.write(f"**Notes:** {o['notes']}")

            c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="large")
            with c1:
                new_pay_status = st.selectbox(
                    "payment_status",
                    ["pending", "confirmed"],
                    index=0 if o["payment_status"] == "pending" else 1,
                    key=f"pay_{o['id']}",
                )
                momo_tx_id = st.text_input(
                    "Mobile Money TX ID (client)",
                    value=o["momo_tx_id"] or "",
                    key=f"tx_{o['id']}",
                )
            with c2:
                new_order_status = st.selectbox(
                    "order_status",
                    ["created", "paid", "ordered", "shipped", "closed"],
                    index=["created", "paid", "ordered", "shipped", "closed"].index(o["order_status"]),
                    key=f"ord_{o['id']}",
                )
                momo_provider = st.selectbox(
                    "Provider",
                    ["MTN", "Orange", "Autre"],
                    index=["MTN", "Orange", "Autre"].index(o["momo_provider"] or "Autre"),
                    key=f"prov_{o['id']}",
                )
            with c3:
                admin_note = st.text_area("Admin note (optionnel)", value="", key=f"an_{o['id']}", height=80)
            with c4:
                if st.button("Enregistrer MAJ", key=f"save_{o['id']}"):
                    update_order(
                        o["id"],
                        payment_status=new_pay_status,
                        order_status=new_order_status,
                        momo_tx_id=momo_tx_id.strip() or None,
                        momo_provider=momo_provider,
                        notes=(o["notes"] or "")
                        + (f"\n[ADMIN] {admin_note.strip()}" if admin_note.strip() else ""),
                    )
                    st.success("Mis à jour.")
                    st.rerun()

    st.divider()
    if st.button("Se déconnecter (admin)"):
        st.session_state.is_admin = False
        st.rerun()