# afripay_app.py
# AfriPay Afrika — MVP Streamlit (paiement international uniquement)
# IMPORTANT: AfriPay ne gère PAS la livraison ni le dédouanement. Le client fournit l'adresse agence/transitaire.

from __future__ import annotations

import os
import re
import hmac
import time
import uuid
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

import streamlit as st

# bcrypt (admin password hashing)
import bcrypt


# ----------------------------
# Config UI
# ----------------------------
APP_NAME = "AfriPay Afrika"
TAGLINE = "Pilot Cameroun • Paiement international"
DISCLAIMER = (
    "AfriPay facilite uniquement le **paiement international**. "
    "Nous ne sommes pas responsables de la livraison, du transport, des délais, ni des frais de douane. "
    "Le client fournit l’adresse de son **agence/transitaire** et gère réception + dédouanement."
)

LOGO_PATH = os.path.join("assets", "logo.png")

DB_PATH = "afripay.db"

DEFAULT_EUR_XAF = 655.957  # BCE approx (fixe pour MVP)
DEFAULT_FEE_MODE = "percent"  # "percent" or "fixed"
DEFAULT_FEE_VALUE = 10.0      # 10%


# ----------------------------
# Helpers: DB
# ----------------------------
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        phone TEXT UNIQUE NOT NULL,
        name TEXT,
        email TEXT,
        agency_name TEXT NOT NULL,
        agency_address TEXT NOT NULL,
        agency_ack INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS otps (
        phone TEXT PRIMARY KEY,
        otp TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,

        merchant_site TEXT,
        product_name TEXT,
        product_url TEXT,

        product_price_eur REAL NOT NULL,
        seller_shipping_eur REAL NOT NULL DEFAULT 0,

        eur_xaf REAL NOT NULL,
        fee_mode TEXT NOT NULL,
        fee_value REAL NOT NULL,
        afripay_fee_eur REAL NOT NULL,
        total_eur REAL NOT NULL,
        total_xaf REAL NOT NULL,

        agency_name TEXT NOT NULL,
        agency_address TEXT NOT NULL,
        agency_ack INTEGER NOT NULL DEFAULT 0,

        tracking_code TEXT,
        notes TEXT,

        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # seed settings if missing
    set_if_missing(cur, "eur_xaf", str(DEFAULT_EUR_XAF))
    set_if_missing(cur, "fee_mode", DEFAULT_FEE_MODE)
    set_if_missing(cur, "fee_value", str(DEFAULT_FEE_VALUE))

    conn.commit()
    conn.close()


def set_if_missing(cur: sqlite3.Cursor, key: str, value: str) -> None:
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO settings(key, value) VALUES(?, ?)", (key, value))


def get_setting(key: str, default: str) -> str:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()


# ----------------------------
# Helpers: security / secrets
# ----------------------------
def secret_get(path: str, default: Optional[str] = None) -> Optional[str]:
    """
    Reads st.secrets in Streamlit Cloud or local .streamlit/secrets.toml.
    path: "admin.password_hash" or "admin.password_plain"
    """
    try:
        parts = path.split(".")
        node: Any = st.secrets
        for p in parts:
            node = node[p]
        return str(node)
    except Exception:
        return default


def verify_admin_password(plain: str) -> bool:
    """
    Supports either:
      - admin.password_hash (bcrypt hash)  [RECOMMENDED]
      - admin.password_plain (plain)       [only for quick local tests]
    """
    stored_hash = secret_get("admin.password_hash")
    stored_plain = secret_get("admin.password_plain")

    if stored_hash:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), stored_hash.encode("utf-8"))
        except Exception:
            return False

    if stored_plain:
        # constant-time compare
        return hmac.compare_digest(plain, stored_plain)

    # If nothing set, block admin by default
    return False


# ----------------------------
# OTP (test)
# ----------------------------
def generate_otp() -> str:
    # 6 digits
    return f"{uuid.uuid4().int % 1_000_000:06d}"


def save_otp(phone: str, otp: str, ttl_seconds: int = 180) -> None:
    expires_at = int(time.time()) + ttl_seconds
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO otps(phone, otp, expires_at) VALUES(?, ?, ?) "
                "ON CONFLICT(phone) DO UPDATE SET otp=excluded.otp, expires_at=excluded.expires_at",
                (phone, otp, expires_at))
    conn.commit()
    conn.close()


def check_otp(phone: str, otp: str) -> Tuple[bool, str]:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT otp, expires_at FROM otps WHERE phone = ?", (phone,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False, "OTP introuvable. Clique sur “Envoyer OTP”."
    if int(time.time()) > int(row["expires_at"]):
        return False, "OTP expiré. Renvoie un nouvel OTP."
    if not hmac.compare_digest(str(row["otp"]), str(otp).strip()):
        return False, "OTP incorrect."
    return True, "OK"


# ----------------------------
# Users
# ----------------------------
PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def upsert_user(
    phone: str,
    name: str,
    email: str,
    agency_name: str,
    agency_address: str,
    agency_ack: bool
) -> str:
    uid = get_user_id_by_phone(phone)
    now = datetime.utcnow().isoformat()

    conn = db()
    cur = conn.cursor()

    if uid is None:
        uid = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO users(id, phone, name, email, agency_name, agency_address, agency_ack, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, phone, name or None, email or None, agency_name, agency_address, int(bool(agency_ack)), now))
    else:
        cur.execute("""
            UPDATE users
            SET name=?, email=?, agency_name=?, agency_address=?, agency_ack=?
            WHERE id=?
        """, (name or None, email or None, agency_name, agency_address, int(bool(agency_ack)), uid))

    conn.commit()
    conn.close()
    return uid


def get_user_id_by_phone(phone: str) -> Optional[str]:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE phone = ?", (phone,))
    row = cur.fetchone()
    conn.close()
    return row["id"] if row else None


def get_user(uid: str) -> Optional[sqlite3.Row]:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    conn.close()
    return row


# ----------------------------
# Orders
# ----------------------------
def compute_fees(product_eur: float, seller_ship_eur: float, fee_mode: str, fee_value: float) -> Tuple[float, float]:
    base = max(product_eur, 0.0) + max(seller_ship_eur, 0.0)
    if fee_mode == "fixed":
        afripay_fee = max(fee_value, 0.0)
    else:
        afripay_fee = base * max(fee_value, 0.0) / 100.0
    total = base + afripay_fee
    return afripay_fee, total


def create_order(payload: Dict[str, Any]) -> str:
    oid = str(uuid.uuid4())
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders(
            id, user_id, created_at, status,
            merchant_site, product_name, product_url,
            product_price_eur, seller_shipping_eur,
            eur_xaf, fee_mode, fee_value, afripay_fee_eur, total_eur, total_xaf,
            agency_name, agency_address, agency_ack,
            tracking_code, notes
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        oid,
        payload["user_id"],
        datetime.utcnow().isoformat(),
        "CREATED",
        payload.get("merchant_site"),
        payload.get("product_name"),
        payload.get("product_url"),
        float(payload["product_price_eur"]),
        float(payload.get("seller_shipping_eur", 0.0)),
        float(payload["eur_xaf"]),
        payload["fee_mode"],
        float(payload["fee_value"]),
        float(payload["afripay_fee_eur"]),
        float(payload["total_eur"]),
        float(payload["total_xaf"]),
        payload["agency_name"],
        payload["agency_address"],
        int(bool(payload["agency_ack"])),
        payload.get("tracking_code"),
        payload.get("notes")
    ))

    conn.commit()
    conn.close()
    return oid


def list_orders_for_user(uid: str) -> list[sqlite3.Row]:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (uid,))
    rows = cur.fetchall()
    conn.close()
    return list(rows)


# ----------------------------
# UI Helpers
# ----------------------------
def money_eur(x: float) -> str:
    return f"€ {x:,.2f}".replace(",", " ").replace(".", ",")


def money_xaf(x: float) -> str:
    return f"{x:,.0f} XAF".replace(",", " ").replace(".", ",")


def ensure_session_defaults() -> None:
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("user_phone", None)
    st.session_state.setdefault("user_logged", False)

    st.session_state.setdefault("admin_logged", False)


def sidebar_header() -> None:
    st.sidebar.markdown(f"## {APP_NAME}")
    st.sidebar.caption(TAGLINE)
    st.sidebar.markdown("---")


def show_logo_header() -> None:
    c1, c2 = st.columns([1, 2], vertical_alignment="center")
    with c1:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        else:
            st.write("🟦")
    with c2:
        st.markdown(f"# {APP_NAME}")
        st.caption("Facilitateur de paiement international — Phase pilote (Cameroun)")


# ----------------------------
# Pages
# ----------------------------
def page_connexion() -> None:
    show_logo_header()
    st.info(DISCLAIMER)

    st.markdown("## Connexion")
    st.caption("Connexion par téléphone (OTP de test affiché).")

    left, right = st.columns([1.2, 1], vertical_alignment="top")

    with left:
        phone = st.text_input("Téléphone (ex: +2376xxxxxxx)", value=st.session_state.get("user_phone") or "", placeholder="+2376...")
        name = st.text_input("Nom (optionnel)")
        email = st.text_input("Email (optionnel)")

        st.markdown("### Adresse agence / transitaire (obligatoire)")
        agency_name = st.text_input("Nom de l’agence / transitaire", placeholder="Ex: DHL Express Douala / Transitaire XYZ")
        agency_address = st.text_area(
            "Adresse exacte de livraison (celle fournie par l’agence/transitaire)",
            placeholder="Ex: Rue…, Quartier…, Ville…, Téléphone…, Référence…",
            height=90
        )

        agency_ack = st.checkbox(
            "Je confirme que cette adresse est valide et que je gère la livraison et le dédouanement. "
            "AfriPay ne reçoit jamais le colis.",
            value=False
        )

        col_a, col_b = st.columns([1, 1])
        with col_a:
            send = st.button("Envoyer OTP", use_container_width=True)
        with col_b:
            st.write("")

        otp_display = None

        if send:
            phone_clean = phone.strip()
            if not PHONE_RE.match(phone_clean):
                st.error("Numéro invalide. Format recommandé: +2376xxxxxxx")
            elif not agency_name.strip() or not agency_address.strip():
                st.error("L’agence/transitaire + l’adresse exacte sont obligatoires.")
            elif not agency_ack:
                st.error("La confirmation livraison + dédouanement est obligatoire.")
            else:
                otp = generate_otp()
                save_otp(phone_clean, otp, ttl_seconds=180)
                st.session_state["user_phone"] = phone_clean
                otp_display = otp
                st.success("OTP envoyé (test).")

        if otp_display:
            st.warning(f"OTP de test: **{otp_display}** (expire en 3 min)")

    with right:
        st.markdown("### Valider l'OTP")
        otp_in = st.text_input("Entrer OTP", placeholder="123456")
        login = st.button("Se connecter", use_container_width=True)

        if login:
            phone_clean = (phone or "").strip()
            if not PHONE_RE.match(phone_clean):
                st.error("Numéro invalide.")
            elif not otp_in.strip():
                st.error("Entre l’OTP.")
            else:
                ok, msg = check_otp(phone_clean, otp_in.strip())
                if not ok:
                    st.error(msg)
                else:
                    # enforce address fields again
                    if not agency_name.strip() or not agency_address.strip():
                        st.error("L’agence/transitaire + l’adresse exacte sont obligatoires.")
                        return
                    if not agency_ack:
                        st.error("La confirmation livraison + dédouanement est obligatoire.")
                        return

                    uid = upsert_user(
                        phone=phone_clean,
                        name=name.strip(),
                        email=email.strip(),
                        agency_name=agency_name.strip(),
                        agency_address=agency_address.strip(),
                        agency_ack=agency_ack
                    )
                    st.session_state["user_id"] = uid
                    st.session_state["user_logged"] = True
                    st.success("Connecté ✅")

                    # refresh app state
                    st.rerun()


def page_simuler() -> None:
    show_logo_header()
    st.info(DISCLAIMER)

    st.markdown("## Simulation du coût total")
    st.caption("Le client paie : prix produit + frais vendeur (si applicable) + frais de service AfriPay.")

    eur_xaf = float(get_setting("eur_xaf", str(DEFAULT_EUR_XAF)))
    fee_mode = get_setting("fee_mode", DEFAULT_FEE_MODE)
    fee_value = float(get_setting("fee_value", str(DEFAULT_FEE_VALUE)))

    left, right = st.columns([1.2, 1], vertical_alignment="top")

    with left:
        product = st.number_input("Prix du produit (EUR)", min_value=0.0, value=50.0, step=1.0, format="%.2f")
        seller_ship = st.number_input(
            "Frais du vendeur (livraison du site) — optionnel (EUR)",
            min_value=0.0, value=15.0, step=1.0, format="%.2f",
            help="Ex: frais de livraison facturés par Amazon/Shein/Alibaba. Ce n’est PAS une livraison AfriPay."
        )

    afripay_fee, total_eur = compute_fees(product, seller_ship, fee_mode, fee_value)
    total_xaf = total_eur * eur_xaf

    with right:
        st.markdown("### Résumé")
        st.write(f"Taux EUR → XAF : **{eur_xaf:,.3f}**".replace(",", " ").replace(".", ","))
        st.write(f"Produit : **{money_eur(product)}** (≈ {money_xaf(product*eur_xaf)})")
        st.write(f"Frais vendeur (livraison du site) : **{money_eur(seller_ship)}** (≈ {money_xaf(seller_ship*eur_xaf)})")

        if fee_mode == "fixed":
            st.write(f"Frais de service AfriPay (fixe) : **{money_eur(afripay_fee)}** (≈ {money_xaf(afripay_fee*eur_xaf)})")
        else:
            st.write(f"Frais de service AfriPay ({fee_value:.2f}%) : **{money_eur(afripay_fee)}** (≈ {money_xaf(afripay_fee*eur_xaf)})")

        st.success(f"Total à payer : {money_eur(total_eur)} (≈ {money_xaf(total_xaf)})")


def page_creer_commande() -> None:
    show_logo_header()
    st.info(DISCLAIMER)

    st.markdown("## Créer une commande")

    if not st.session_state.get("user_logged"):
        st.warning("Veuillez d'abord vous connecter (onglet Connexion).")
        return

    user = get_user(st.session_state["user_id"])
    if not user:
        st.error("Utilisateur introuvable. Reconnecte-toi.")
        return

    eur_xaf = float(get_setting("eur_xaf", str(DEFAULT_EUR_XAF)))
    fee_mode = get_setting("fee_mode", DEFAULT_FEE_MODE)
    fee_value = float(get_setting("fee_value", str(DEFAULT_FEE_VALUE)))

    st.markdown("### Détails produit")
    c1, c2 = st.columns([1, 1], vertical_alignment="top")

    with c1:
        merchant_site = st.text_input("Site marchand (optionnel)", placeholder="Amazon / Shein / AliExpress / …")
        product_name = st.text_input("Nom du produit (optionnel)", placeholder="Ex: Smartphone, chaussures, …")
        product_url = st.text_input("Lien produit (optionnel)", placeholder="https://...")

    with c2:
        product_price = st.number_input("Prix produit (EUR)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        seller_ship = st.number_input(
            "Frais vendeur (livraison du site) — optionnel (EUR)",
            min_value=0.0, value=0.0, step=1.0, format="%.2f",
            help="Ex: frais de livraison facturés par le site. Ce n’est PAS une livraison AfriPay."
        )

    st.markdown("### Adresse agence / transitaire (obligatoire)")
    st.caption("Cette adresse est celle que le client met aussi sur Amazon/Shein/Alibaba pour la livraison.")

    agency_name = st.text_input("Nom de l’agence / transitaire", value=str(user["agency_name"] or ""))
    agency_address = st.text_area("Adresse exacte de livraison", value=str(user["agency_address"] or ""), height=100)

    agency_ack = st.checkbox(
        "Je confirme que cette adresse est valide et que je gère la livraison et le dédouanement. AfriPay ne reçoit jamais le colis.",
        value=bool(user["agency_ack"])
    )

    st.markdown("### Tracking (optionnel)")
    tracking_code = st.text_input("Code de tracking (si déjà disponible)", placeholder="Ex: 1Z..., LP..., ...")
    notes = st.text_area("Notes (optionnel)", placeholder="Tout détail utile pour le suivi…", height=80)

    afripay_fee, total_eur = compute_fees(product_price, seller_ship, fee_mode, fee_value)
    total_xaf = total_eur * eur_xaf

    st.markdown("### Résumé paiement")
    st.write(f"Frais de service AfriPay : **{money_eur(afripay_fee)}**")
    st.success(f"Total à payer : {money_eur(total_eur)} (≈ {money_xaf(total_xaf)})")

    st.markdown("---")
    confirm = st.checkbox("Je confirme que je paie uniquement un service de paiement AfriPay (pas la livraison).", value=False)

    if st.button("Créer la commande", use_container_width=True):
        if not agency_name.strip() or not agency_address.strip():
            st.error("L’agence/transitaire + l’adresse exacte sont obligatoires.")
            return
        if not agency_ack:
            st.error("La confirmation livraison + dédouanement est obligatoire.")
            return
        if not confirm:
            st.error("La confirmation du service AfriPay est obligatoire.")
            return
        if product_price <= 0:
            st.error("Le prix produit doit être > 0.")
            return

        # update user profile with latest address/ack
        upsert_user(
            phone=str(user["phone"]),
            name=str(user["name"] or ""),
            email=str(user["email"] or ""),
            agency_name=agency_name.strip(),
            agency_address=agency_address.strip(),
            agency_ack=agency_ack
        )

        oid = create_order({
            "user_id": st.session_state["user_id"],
            "merchant_site": merchant_site.strip() or None,
            "product_name": product_name.strip() or None,
            "product_url": product_url.strip() or None,
            "product_price_eur": float(product_price),
            "seller_shipping_eur": float(seller_ship),
            "eur_xaf": float(eur_xaf),
            "fee_mode": fee_mode,
            "fee_value": float(fee_value),
            "afripay_fee_eur": float(afripay_fee),
            "total_eur": float(total_eur),
            "total_xaf": float(total_xaf),
            "agency_name": agency_name.strip(),
            "agency_address": agency_address.strip(),
            "agency_ack": bool(agency_ack),
            "tracking_code": tracking_code.strip() or None,
            "notes": notes.strip() or None
        })

        st.success(f"Commande créée ✅ ID: {oid}")
        st.balloons()


def page_mes_commandes() -> None:
    show_logo_header()
    st.info(DISCLAIMER)

    st.markdown("## Mes commandes")

    if not st.session_state.get("user_logged"):
        st.warning("Veuillez d'abord vous connecter.")
        return

    orders = list_orders_for_user(st.session_state["user_id"])
    if not orders:
        st.info("Aucune commande pour le moment.")
        return

    for o in orders:
        with st.expander(f"Commande {o['id']} • {o['status']} • {o['created_at']}", expanded=False):
            st.write(f"Site: {o['merchant_site'] or '-'}")
            st.write(f"Produit: {o['product_name'] or '-'}")
            if o["product_url"]:
                st.write(f"Lien: {o['product_url']}")
            st.write(f"Prix produit: **{money_eur(o['product_price_eur'])}**")
            st.write(f"Frais vendeur (site): **{money_eur(o['seller_shipping_eur'])}**")
            st.write(f"Frais de service AfriPay: **{money_eur(o['afripay_fee_eur'])}**")
            st.success(f"Total: {money_eur(o['total_eur'])} (≈ {money_xaf(o['total_xaf'])})")

            st.markdown("**Adresse agence/transitaire**")
            st.write(o["agency_name"])
            st.write(o["agency_address"])

            if o["tracking_code"]:
                st.write(f"Tracking: {o['tracking_code']}")
            if o["notes"]:
                st.write(f"Notes: {o['notes']}")


def page_admin() -> None:
    show_logo_header()
    st.info(DISCLAIMER)

    st.markdown("## Admin")

    if not st.session_state.get("admin_logged"):
        pwd = st.text_input("Mot de passe admin", type="password")
        if st.button("Se connecter (admin)"):
            if verify_admin_password(pwd):
                st.session_state["admin_logged"] = True
                st.success("Admin connecté ✅")
                st.rerun()
            else:
                st.error("Mot de passe incorrect (ou secret non configuré).")
        st.caption("Conseil: configure le mot de passe admin dans `.streamlit/secrets.toml`.")
        return

    st.success("Espace Admin")
    st.caption("Paramètres & gestion des commandes.")

    eur_xaf = float(get_setting("eur_xaf", str(DEFAULT_EUR_XAF)))
    fee_mode = get_setting("fee_mode", DEFAULT_FEE_MODE)
    fee_value = float(get_setting("fee_value", str(DEFAULT_FEE_VALUE)))

    c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="top")

    with c1:
        st.markdown("### Taux EUR → XAF")
        new_rate = st.number_input("Taux EUR → XAF", min_value=1.0, value=float(eur_xaf), step=0.1, format="%.3f")
        if st.button("Enregistrer taux"):
            set_setting("eur_xaf", str(new_rate))
            st.success("Taux enregistré.")
            st.rerun()

    with c2:
        st.markdown("### Frais de service AfriPay")
        new_mode = st.selectbox("Mode", options=["percent", "fixed"], index=0 if fee_mode == "percent" else 1)
        new_val = st.number_input(
            "Valeur (%, ou EUR si fixed)",
            min_value=0.0,
            value=float(fee_value),
            step=0.5,
            format="%.2f"
        )
        if st.button("Enregistrer frais"):
            set_setting("fee_mode", new_mode)
            set_setting("fee_value", str(new_val))
            st.success("Frais enregistrés.")
            st.rerun()

    with c3:
        st.markdown("### Déconnexion admin")
        if st.button("Se déconnecter"):
            st.session_state["admin_logged"] = False
            st.rerun()


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="💳", layout="wide")

    init_db()
    ensure_session_defaults()

    sidebar_header()

    tab = st.sidebar.radio(
        "Menu",
        ["Connexion", "Simuler", "Créer commande", "Mes commandes", "Admin"],
        index=0
    )

    if tab == "Connexion":
        page_connexion()
    elif tab == "Simuler":
        page_simuler()
    elif tab == "Créer commande":
        page_creer_commande()
    elif tab == "Mes commandes":
        page_mes_commandes()
    elif tab == "Admin":
        page_admin()


if __name__ == "__main__":
    main()