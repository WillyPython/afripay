import inspect
import os
import secrets
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta

import streamlit as st

from config.settings import APP_TITLE
from data.database import get_conn, init_db
from core.session import (
    init_session,
    login_user,
    logout_admin,
    logout_user,
    restore_user_session,
)
from services.admin_service import (
    admin_is_configured,
    verify_admin_password,
)
from services.auth_session_service import (
    create_user_session,
    deactivate_session,
    get_active_session,
    touch_session,
)
from services.order_service import (
    create_order_for_user,
    get_order_by_code,
    get_payment_status_label,
    list_orders_for_user,
    mark_payment_proof_sent,
)
from services.settings_service import ensure_defaults
from services.user_service import upsert_user
from ui.branding import render_sidebar_branding


# =========================================================
# CONFIG
# =========================================================
AFRIPAY_PUBLIC_URL = os.getenv("AFRIPAY_PUBLIC_URL", "https://afripayafrika.com")
EUR_TO_XAF_RATE = 655.957
AFRIPAY_PERCENT_FEE = 0.20
OTP_VALIDITY_MINUTES = 15

WHATSAPP_DEFAULT = os.getenv("WHATSAPP_DEFAULT", "").strip()
WHATSAPP_CM = os.getenv("WHATSAPP_CM", "").strip()
MTN_MOMO_NUMBER = os.getenv("MTN_MOMO_NUMBER", "").strip()
ORANGE_MONEY_NUMBER = os.getenv("ORANGE_MONEY_NUMBER", "").strip()


# =========================================================
# STREAMLIT PAGE
# =========================================================
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💸",
    layout="wide",
)


# =========================================================
# GENERIC HELPERS
# =========================================================
def now_utc() -> datetime:
    return datetime.utcnow()


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    cleaned = str(phone).strip()
    for char in [" ", "-", ".", "(", ")", "/"]:
        cleaned = cleaned.replace(char, "")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    return cleaned


def clean_email(email: str) -> str:
    return (email or "").strip().lower()


def safe_float(value, default=0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def round_xaf(value) -> int:
    amount = safe_float(value, 0)
    return int(round(amount / 10.0) * 10)


def format_eur(value) -> str:
    return f"{safe_float(value, 0):,.2f} €".replace(",", " ").replace(".", ",")


def format_xaf(value) -> str:
    return f"{int(round_xaf(value)):,.0f} XAF".replace(",", " ")


def compute_financials(base_eur) -> dict:
    base_eur = safe_float(base_eur, 0)
    fee_eur = base_eur * AFRIPAY_PERCENT_FEE
    total_eur = base_eur + fee_eur
    total_xaf = round_xaf(total_eur * EUR_TO_XAF_RATE)
    return {
        "merchant_total_eur": round(base_eur, 2),
        "service_fee_eur": round(fee_eur, 2),
        "total_to_pay_eur": round(total_eur, 2),
        "total_to_pay_xaf": total_xaf,
    }


def build_whatsapp_payment_url(order_code: str, amount_xaf: int) -> str:
    whatsapp_number = WHATSAPP_DEFAULT or WHATSAPP_CM
    if not whatsapp_number:
        return ""

    number = whatsapp_number.replace("+", "").replace(" ", "")
    message = f"""Bonjour AfriPay,

Je confirme le paiement de ma commande.

Référence : {order_code}
Montant payé : {amount_xaf} XAF
Opérateur : MTN MoMo / Orange Money

Vous trouverez ci-joint la capture d’écran du paiement.
Merci.
"""
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{number}?text={encoded_message}"


def build_support_whatsapp_url(order_code: str) -> str:
    whatsapp_number = WHATSAPP_DEFAULT or WHATSAPP_CM
    if not whatsapp_number:
        return ""

    number = whatsapp_number.replace("+", "").replace(" ", "")
    message = f"""Bonjour AfriPay,

Je souhaite un suivi pour la commande {order_code}.
Merci.
"""
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{number}?text={encoded_message}"


def get_value(obj, *keys, default=None):
    if obj is None:
        return default

    for key in keys:
        if isinstance(obj, dict) and key in obj:
            return obj.get(key)
        if hasattr(obj, key):
            return getattr(obj, key)

    if isinstance(obj, (list, tuple)):
        tuple_map = {
            "id": 0,
            "user_id": 0,
            "phone": 1,
            "name": 2,
            "email": 3,
            "created_at": 4,
        }
        for key in keys:
            idx = tuple_map.get(key)
            if idx is not None and len(obj) > idx:
                return obj[idx]

    return default


def invoke_service(func, alias_mapping: dict):
    signature = inspect.signature(func)
    parameters = signature.parameters
    accepts_var_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()
    )

    if accepts_var_kwargs:
        kwargs = {}
        for _, candidates in alias_mapping.items():
            for candidate_name, candidate_value in candidates:
                kwargs[candidate_name] = candidate_value
        return func(**kwargs)

    filtered_kwargs = {}
    for param_name in parameters.keys():
        for canonical_name, candidates in alias_mapping.items():
            if param_name == canonical_name:
                for _, candidate_value in candidates:
                    filtered_kwargs[param_name] = candidate_value
                    break
                break
            for candidate_name, candidate_value in candidates:
                if param_name == candidate_name:
                    filtered_kwargs[param_name] = candidate_value
                    break

    return func(**filtered_kwargs)


# =========================================================
# DATABASE HELPERS
# =========================================================
def fetch_rows(query: str, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params or ())
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description] if cur.description else []
    cur.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


def fetch_one(query: str, params=None):
    rows = fetch_rows(query, params=params)
    return rows[0] if rows else None


def get_table_columns(table_name: str) -> set:
    try:
        rows = fetch_rows(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            """,
            (table_name,),
        )
        return {row["column_name"] for row in rows}
    except Exception:
        return set()


def get_user_by_phone_db(phone: str):
    phone = normalize_phone(phone)
    try:
        return fetch_one(
            """
            SELECT *
            FROM users
            WHERE phone = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (phone,),
        )
    except Exception:
        return None


def get_user_by_id_db(user_id):
    try:
        return fetch_one(
            """
            SELECT *
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,),
        )
    except Exception:
        return None


def list_orders_for_user_db(user_id):
    try:
        return fetch_rows(
            """
            SELECT *
            FROM orders
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        )
    except Exception:
        return []


def get_order_by_code_db(order_code: str):
    try:
        return fetch_one(
            """
            SELECT *
            FROM orders
            WHERE code = %s OR order_code = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (order_code, order_code),
        )
    except Exception:
        return None


def list_all_orders_db(limit=300):
    try:
        return fetch_rows(
            f"""
            SELECT *
            FROM orders
            ORDER BY created_at DESC, id DESC
            LIMIT {int(limit)}
            """
        )
    except Exception:
        return []


def update_order_db(order_id, updates: dict):
    if not updates:
        return False

    allowed_columns = get_table_columns("orders")
    valid_updates = {k: v for k, v in updates.items() if k in allowed_columns}
    if not valid_updates:
        return False

    set_clause = ", ".join([f"{key} = %s" for key in valid_updates.keys()])
    params = list(valid_updates.values()) + [order_id]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE orders
        SET {set_clause}
        WHERE id = %s
        """,
        params,
    )
    conn.commit()
    cur.close()
    conn.close()
    return True


# =========================================================
# APP STATE
# =========================================================
def init_app_state():
    defaults = {
        "otp_nonce": 0,
        "identity_nonce": 0,
        "phone_nonce": 0,
        "pending_login_phone": "",
        "generated_otp_code": "",
        "otp_requested_at": None,
        "current_user": None,
        "user_session_token": "",
        "admin_authenticated": False,
        "last_created_order_code": "",
        "last_created_order_amount_xaf": 0,
        "last_created_order_amount_eur": 0.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_login_widgets(full_phone_reset=False):
    st.session_state["otp_nonce"] += 1
    st.session_state["identity_nonce"] += 1
    st.session_state["generated_otp_code"] = ""
    st.session_state["otp_requested_at"] = None
    st.session_state["pending_login_phone"] = ""
    if full_phone_reset:
        st.session_state["phone_nonce"] += 1


def current_user():
    user = st.session_state.get("current_user")
    if user:
        return user

    for key in ["user", "authenticated_user"]:
        if st.session_state.get(key):
            return st.session_state.get(key)

    return None


def set_current_user(user):
    st.session_state["current_user"] = user


def user_is_logged_in() -> bool:
    return current_user() is not None


# =========================================================
# BOOTSTRAP
# =========================================================
def bootstrap_core():
    init_db()
    ensure_defaults()
    init_session()

    try:
        restore_user_session()
    except Exception:
        pass

    token = st.session_state.get("user_session_token", "")
    if token and not current_user():
        try:
            session_data = get_active_session(token)
            if session_data:
                phone = get_value(session_data, "phone")
                user_id = get_value(session_data, "user_id", "id")
                user = None
                if user_id:
                    user = get_user_by_id_db(user_id)
                if not user and phone:
                    user = get_user_by_phone_db(phone)
                if user:
                    set_current_user(user)
                    try:
                        touch_session(token)
                    except Exception:
                        pass
        except Exception:
            pass


# =========================================================
# AUTH / OTP
# =========================================================
def generate_otp() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def request_otp(phone: str):
    phone = normalize_phone(phone)
    if not phone:
        st.error("Veuillez saisir un numéro de téléphone.")
        return

    otp = generate_otp()
    st.session_state["pending_login_phone"] = phone
    st.session_state["generated_otp_code"] = otp
    st.session_state["otp_requested_at"] = now_utc()
    st.session_state["otp_nonce"] += 1
    st.success(f"OTP généré pour {phone}.")
    st.info(f"Code OTP de test : {otp}")


def otp_is_valid(submitted_otp: str) -> bool:
    generated = st.session_state.get("generated_otp_code", "")
    requested_at = st.session_state.get("otp_requested_at")
    if not generated or not requested_at:
        return False
    if now_utc() > requested_at + timedelta(minutes=OTP_VALIDITY_MINUTES):
        return False
    return submitted_otp.strip() == generated.strip()


def upsert_user_safely(phone: str, name: str, email: str):
    phone = normalize_phone(phone)
    email = clean_email(email)

    try:
        user = invoke_service(
            upsert_user,
            {
                "phone": [("phone", phone), ("user_phone", phone)],
                "name": [("name", name), ("full_name", name)],
                "email": [("email", email)],
            },
        )
        if user:
            return user
    except Exception:
        pass

    user = get_user_by_phone_db(phone)
    if user:
        return user

    raise RuntimeError("Impossible d’enregistrer ou récupérer l’utilisateur.")


def login_after_otp(phone: str, otp: str, name: str, email: str):
    if not otp_is_valid(otp):
        st.error("OTP invalide ou expiré.")
        return

    try:
        user = upsert_user_safely(phone, name, email)
        set_current_user(user)

        try:
            login_user(user)
        except Exception:
            pass

        try:
            session_token = invoke_service(
                create_user_session,
                {
                    "user_id": [
                        ("user_id", get_value(user, "id", "user_id")),
                        ("id", get_value(user, "id", "user_id")),
                    ],
                    "phone": [("phone", normalize_phone(phone))],
                },
            )
            if session_token:
                st.session_state["user_session_token"] = session_token
        except Exception:
            pass

        reset_login_widgets(full_phone_reset=True)
        st.success("Connexion réussie.")
        st.rerun()

    except Exception as exc:
        st.error(f"Connexion impossible : {exc}")


def logout_current_user():
    token = st.session_state.get("user_session_token", "")
    if token:
        try:
            deactivate_session(token)
        except Exception:
            pass

    try:
        logout_user()
    except Exception:
        pass

    st.session_state["user_session_token"] = ""
    st.session_state["current_user"] = None
    reset_login_widgets(full_phone_reset=True)
    st.success("Déconnexion effectuée.")
    st.rerun()


# =========================================================
# ORDERS
# =========================================================
def create_order_safely(payload: dict):
    alias_mapping = {
        "user_id": [("user_id", payload.get("user_id"))],
        "phone": [("phone", payload.get("phone"))],
        "name": [("name", payload.get("name"))],
        "email": [("email", payload.get("email"))],
        "product_url": [
            ("product_url", payload.get("product_url")),
            ("product_link", payload.get("product_url")),
            ("link", payload.get("product_url")),
            ("merchant_link", payload.get("product_url")),
        ],
        "merchant_name": [
            ("merchant_name", payload.get("merchant_name")),
            ("site_name", payload.get("merchant_name")),
            ("merchant", payload.get("merchant_name")),
        ],
        "merchant_total_eur": [
            ("merchant_total_eur", payload.get("merchant_total_eur")),
            ("amount_eur", payload.get("merchant_total_eur")),
            ("total_eur", payload.get("merchant_total_eur")),
            ("base_amount_eur", payload.get("merchant_total_eur")),
        ],
        "service_fee_eur": [
            ("service_fee_eur", payload.get("service_fee_eur")),
            ("fee_eur", payload.get("service_fee_eur")),
        ],
        "total_to_pay_eur": [
            ("total_to_pay_eur", payload.get("total_to_pay_eur")),
            ("grand_total_eur", payload.get("total_to_pay_eur")),
        ],
        "total_to_pay_xaf": [
            ("total_to_pay_xaf", payload.get("total_to_pay_xaf")),
            ("amount_xaf", payload.get("total_to_pay_xaf")),
            ("xaf_amount", payload.get("total_to_pay_xaf")),
        ],
        "clearance_agent_name": [
            ("clearance_agent_name", payload.get("clearance_agent_name")),
            ("forwarder_name", payload.get("clearance_agent_name")),
            ("agent_name", payload.get("clearance_agent_name")),
        ],
        "clearance_agent_address": [
            ("clearance_agent_address", payload.get("clearance_agent_address")),
            ("forwarder_address", payload.get("clearance_agent_address")),
            ("agent_address", payload.get("clearance_agent_address")),
        ],
        "notes": [
            ("notes", payload.get("notes")),
            ("customer_note", payload.get("notes")),
            ("note", payload.get("notes")),
        ],
    }

    return invoke_service(create_order_for_user, alias_mapping)


def fetch_user_orders(user_id):
    try:
        orders = invoke_service(
            list_orders_for_user,
            {"user_id": [("user_id", user_id), ("id", user_id)]},
        )
        if orders is not None:
            return orders
    except Exception:
        pass
    return list_orders_for_user_db(user_id)


def fetch_order_by_code(order_code: str):
    order_code = (order_code or "").strip()
    if not order_code:
        return None

    try:
        order = invoke_service(
            get_order_by_code,
            {
                "order_code": [("order_code", order_code), ("code", order_code)],
                "code": [("code", order_code)],
            },
        )
        if order:
            return order
    except Exception:
        pass

    return get_order_by_code_db(order_code)


def get_order_code(order):
    return get_value(order, "code", "order_code", default="")


def get_order_created_at(order):
    return get_value(order, "created_at", "date_created", default=None)


def get_order_base_eur(order):
    for key in [
        "merchant_total_eur",
        "base_amount_eur",
        "amount_eur",
        "total_eur",
        "merchant_amount_eur",
    ]:
        value = get_value(order, key)
        if value not in [None, ""]:
            return safe_float(value, 0)
    return 0.0


def get_order_fee_eur(order):
    for key in ["service_fee_eur", "fee_eur"]:
        value = get_value(order, key)
        if value not in [None, ""]:
            return safe_float(value, 0)
    return round(get_order_base_eur(order) * AFRIPAY_PERCENT_FEE, 2)


def get_order_total_eur(order):
    for key in ["total_to_pay_eur", "grand_total_eur", "payable_eur"]:
        value = get_value(order, key)
        if value not in [None, ""]:
            return safe_float(value, 0)
    return round(get_order_base_eur(order) + get_order_fee_eur(order), 2)


def get_order_total_xaf(order):
    for key in ["total_to_pay_xaf", "amount_xaf", "xaf_amount"]:
        value = get_value(order, key)
        if value not in [None, ""]:
            return round_xaf(value)
    return round_xaf(get_order_total_eur(order) * EUR_TO_XAF_RATE)


def get_order_payment_status(order):
    raw_status = get_value(order, "payment_status", default="PENDING")
    try:
        return get_payment_status_label(raw_status)
    except Exception:
        return raw_status or "PENDING"


def get_order_tracking_status(order):
    return get_value(
        order,
        "tracking_status",
        "order_status",
        "status",
        default="PENDING",
    )


def mark_payment_proof_sent_safely(order):
    order_id = get_value(order, "id")
    order_code = get_order_code(order)

    try:
        invoke_service(
            mark_payment_proof_sent,
            {
                "order_id": [("order_id", order_id), ("id", order_id)],
                "order_code": [("order_code", order_code), ("code", order_code)],
            },
        )
        return True
    except Exception:
        pass

    columns = get_table_columns("orders")
    updates = {}
    if "payment_status" in columns:
        updates["payment_status"] = "PROOF_RECEIVED"
    if "proof_sent_at" in columns:
        updates["proof_sent_at"] = now_utc()
    if updates and order_id:
        try:
            return update_order_db(order_id, updates)
        except Exception:
            return False
    return False


# =========================================================
# UI HELPERS
# =========================================================
def render_metric_card(title: str, value: str):
    st.markdown(
        f"""
        <div style="padding:16px;border:1px solid rgba(255,255,255,0.1);border-radius:14px;">
            <div style="font-size:0.9rem;opacity:0.8;">{title}</div>
            <div style="font-size:1.4rem;font-weight:700;margin-top:6px;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_order_card(order, show_actions=True):
    code = get_order_code(order)
    created_at = get_order_created_at(order)
    merchant_name = get_value(order, "merchant_name", "site_name", "merchant", default="-")
    product_url = get_value(order, "product_url", "product_link", "link", default="")
    base_eur = get_order_base_eur(order)
    fee_eur = get_order_fee_eur(order)
    total_eur = get_order_total_eur(order)
    total_xaf = get_order_total_xaf(order)
    payment_status = get_order_payment_status(order)
    tracking_status = get_order_tracking_status(order)
    agent_name = get_value(order, "clearance_agent_name", "forwarder_name", "agent_name", default="-")
    agent_address = get_value(order, "clearance_agent_address", "forwarder_address", "agent_address", default="-")
    notes = get_value(order, "notes", "customer_note", "note", default="")

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader(f"Commande {code or '-'}")
        st.write(f"**Marchand / site :** {merchant_name}")
        if product_url:
            st.write(f"**Lien produit / service :** {product_url}")
        st.write(f"**Transitaire / agent :** {agent_name}")
        st.write(f"**Adresse transitaire :** {agent_address}")
        if notes:
            st.write(f"**Note :** {notes}")
        if created_at:
            st.caption(f"Créée le : {created_at}")

    with col2:
        st.write(f"**Montant marchand :** {format_eur(base_eur)}")
        st.write(f"**Frais AfriPay (20%) :** {format_eur(fee_eur)}")
        st.write(f"**Total à payer :** {format_eur(total_eur)}")
        st.write(f"**Total à payer en XAF :** {format_xaf(total_xaf)}")
        st.write(f"**Paiement :** {payment_status}")
        st.write(f"**Tracking :** {tracking_status}")

        if show_actions:
            whatsapp_url = build_whatsapp_payment_url(code, total_xaf)
            if whatsapp_url:
                st.link_button(
                    "📲 Envoyer preuve de paiement WhatsApp",
                    whatsapp_url,
                    use_container_width=True,
                )


# =========================================================
# TERMS OF USE
# =========================================================
def render_terms_of_use_block():
    st.markdown("### Conditions d’utilisation AfriPay")

    with st.expander("Lire les Conditions d’Utilisation AfriPay", expanded=False):
        st.markdown(
            """
**1. Objet**  
Les présentes Conditions d’Utilisation définissent les règles applicables à l’utilisation de la plateforme **AfriPay Afrika**.

AfriPay Afrika est un service de **facilitation de paiement international**, permettant aux utilisateurs de demander l’exécution d’un paiement auprès d’un marchand en leur nom.

**2. Nature du service**  
AfriPay Afrika agit exclusivement comme **mandataire du client pour l’exécution d’un paiement auprès d’un marchand tiers**.

AfriPay :
- n’est pas une banque
- n’est pas un établissement de paiement
- ne fournit pas de portefeuille électronique
- ne propose pas de stockage de fonds
- n’exécute pas de transfert d’argent entre utilisateurs

**3. Mandat donné par le client**  
En utilisant AfriPay, le client :
- mandate expressément AfriPay pour effectuer un paiement en son nom
- confirme que les informations fournies sont exactes
- accepte que le paiement soit réalisé selon les conditions indiquées

Le client reste seul responsable :
- du choix du marchand
- de la validité de la commande
- du contenu du produit ou service acheté

**4. Processus de paiement**  
1. Le client crée une commande via la plateforme  
2. Le client effectue un paiement via Mobile Money  
3. Le client transmet une preuve de paiement  
4. AfriPay vérifie la conformité du paiement  
5. AfriPay procède au paiement auprès du marchand

**5. Absence de détention de fonds**  
AfriPay ne conserve pas de fonds pour le compte du client.

**6. Frais de service**  
AfriPay applique des frais de service affichés avant validation de la commande.

**7. Responsabilité**  
AfriPay ne peut être tenu responsable :
- des défaillances du marchand
- de la qualité des produits ou services achetés
- des retards de livraison
- des problèmes liés au transport ou au dédouanement

Le client est responsable de la coordination avec son transitaire ou agent.

**8. Données fournies par le client**  
Le client s’engage à fournir des informations exactes. Toute fausse déclaration peut entraîner la suspension du service.

**9. Suspension / refus de service**  
AfriPay se réserve le droit de refuser une commande ou de suspendre un utilisateur en cas de fraude, incohérence ou usage abusif.

**10. Acceptation**  
En validant sa commande, le client reconnaît avoir lu, compris et accepté les présentes conditions sans réserve.
            """
        )


# =========================================================
# AUTH PANELS
# =========================================================
def render_login_area():
    st.markdown("## Connexion AfriPay")
    st.write("Connectez-vous avec votre numéro de téléphone et un OTP.")

    phone_key = f"login_phone_input_{st.session_state['phone_nonce']}"
    otp_key = f"login_otp_input_{st.session_state['otp_nonce']}"
    name_key = f"login_name_input_{st.session_state['identity_nonce']}"
    email_key = f"login_email_input_{st.session_state['identity_nonce']}"

    with st.form("request_otp_form", clear_on_submit=False):
        phone_value = st.text_input(
            "Téléphone",
            key=phone_key,
            placeholder="+237XXXXXXXXX ou +31XXXXXXXXX",
        )
        otp_requested = st.form_submit_button("Générer OTP", use_container_width=True)

    if otp_requested:
        request_otp(phone_value)
        st.rerun()

    pending_phone = st.session_state.get("pending_login_phone", "")
    if pending_phone:
        st.info(f"OTP en attente pour : {pending_phone}")

        with st.form("validate_otp_form", clear_on_submit=False):
            otp_value = st.text_input(
                "Code OTP",
                key=otp_key,
                placeholder="6 chiffres",
            )
            name_value = st.text_input(
                "Nom",
                key=name_key,
                placeholder="Votre nom",
            )
            email_value = st.text_input(
                "Email",
                key=email_key,
                placeholder="vous@email.com",
            )

            col1, col2 = st.columns(2)
            with col1:
                connect_clicked = st.form_submit_button("Se connecter", use_container_width=True)
            with col2:
                regenerate_clicked = st.form_submit_button("Régénérer OTP", use_container_width=True)

        if regenerate_clicked:
            request_otp(pending_phone)
            st.rerun()

        if connect_clicked:
            login_after_otp(
                phone=pending_phone,
                otp=otp_value,
                name=name_value.strip(),
                email=email_value.strip(),
            )


def render_logged_user_box():
    user = current_user()
    name = get_value(user, "name", "full_name", default="Utilisateur")
    phone = get_value(user, "phone", default="-")
    email = get_value(user, "email", default="-")

    st.success("Vous êtes connecté.")
    st.write(f"**Nom :** {name}")
    st.write(f"**Téléphone :** {phone}")
    st.write(f"**Email :** {email}")

    if st.button("Déconnexion", use_container_width=True):
        logout_current_user()


# =========================================================
# USER DASHBOARD
# =========================================================
def render_user_summary(orders):
    total_orders = len(orders)
    total_eur = sum(get_order_total_eur(order) for order in orders)
    total_xaf = sum(get_order_total_xaf(order) for order in orders)

    payment_counter = Counter(str(get_value(order, "payment_status", default="PENDING")) for order in orders)
    tracking_counter = Counter(str(get_order_tracking_status(order)) for order in orders)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Commandes", str(total_orders))
    with col2:
        render_metric_card("Volume EUR", format_eur(total_eur))
    with col3:
        render_metric_card("Volume XAF", format_xaf(total_xaf))
    with col4:
        render_metric_card("En attente paiement", str(payment_counter.get("PENDING", 0)))

    with st.expander("Voir les statistiques détaillées", expanded=False):
        st.write("**Paiement**")
        st.json(dict(payment_counter))
        st.write("**Tracking**")
        st.json(dict(tracking_counter))


def render_create_order_tab(user):
    st.markdown("### Créer une commande")

    user_id = get_value(user, "id", "user_id")
    phone = get_value(user, "phone", default="")
    name = get_value(user, "name", "full_name", default="")
    email = get_value(user, "email", default="")

    render_terms_of_use_block()

    with st.form("create_order_form", clear_on_submit=True):
        product_url = st.text_input(
            "Lien du produit / service",
            placeholder="Collez ici le lien exact du produit ou du paiement marchand",
        )
        merchant_name = st.text_input(
            "Nom du marchand / site",
            placeholder="Amazon, Temu, Zara, etc.",
        )
        merchant_total_eur = st.number_input(
            "Total livré affiché par le marchand (EUR)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
        )
        clearance_agent_name = st.text_input(
            "Nom du transitaire / agent de dédouanement",
            placeholder="Nom du transitaire",
        )
        clearance_agent_address = st.text_area(
            "Adresse du transitaire / agent",
            placeholder="Adresse complète à fournir également chez le marchand",
        )
        notes = st.text_area(
            "Note complémentaire",
            placeholder="Informations utiles sur la commande",
        )

        st.markdown("---")
        st.caption(
            "En validant, vous mandatez AfriPay pour effectuer le paiement en votre nom auprès du marchand sélectionné."
        )

        accepted_terms = st.checkbox(
            "J’ai lu et j’accepte les Conditions d’Utilisation AfriPay",
            key="accepted_terms_create_order",
        )

        submitted = st.form_submit_button("Créer la commande", use_container_width=True)

    if submitted:
        if not product_url.strip():
            st.error("Le lien du produit / service est obligatoire.")
            return
        if not merchant_name.strip():
            st.error("Le nom du marchand / site est obligatoire.")
            return
        if safe_float(merchant_total_eur, 0) <= 0:
            st.error("Le montant marchand doit être supérieur à 0.")
            return
        if not clearance_agent_name.strip():
            st.error("Le nom du transitaire / agent est obligatoire.")
            return
        if not clearance_agent_address.strip():
            st.error("L’adresse du transitaire / agent est obligatoire.")
            return
        if not accepted_terms:
            st.error("Vous devez accepter les Conditions d’Utilisation AfriPay pour continuer.")
            return

        financials = compute_financials(merchant_total_eur)

        payload = {
            "user_id": user_id,
            "phone": phone,
            "name": name,
            "email": email,
            "product_url": product_url.strip(),
            "merchant_name": merchant_name.strip(),
            "merchant_total_eur": financials["merchant_total_eur"],
            "service_fee_eur": financials["service_fee_eur"],
            "total_to_pay_eur": financials["total_to_pay_eur"],
            "total_to_pay_xaf": financials["total_to_pay_xaf"],
            "clearance_agent_name": clearance_agent_name.strip(),
            "clearance_agent_address": clearance_agent_address.strip(),
            "notes": notes.strip(),
        }

        try:
            created_order = create_order_safely(payload)
            order_code = get_order_code(created_order)
            if not order_code:
                latest_orders = fetch_user_orders(user_id)
                if latest_orders:
                    order_code = get_order_code(latest_orders[0])

            st.session_state["last_created_order_code"] = order_code or ""
            st.session_state["last_created_order_amount_xaf"] = financials["total_to_pay_xaf"]
            st.session_state["last_created_order_amount_eur"] = financials["total_to_pay_eur"]

            st.success("Commande créée avec succès.")
            st.write(f"**Référence :** {order_code or '-'}")
            st.write(f"**Montant marchand :** {format_eur(financials['merchant_total_eur'])}")
            st.write(f"**Frais AfriPay :** {format_eur(financials['service_fee_eur'])}")
            st.write(f"**Total à payer :** {format_eur(financials['total_to_pay_eur'])}")
            st.write(f"**Total à payer en XAF :** {format_xaf(financials['total_to_pay_xaf'])}")

            whatsapp_url = build_whatsapp_payment_url(
                order_code=order_code or "N/A",
                amount_xaf=financials["total_to_pay_xaf"],
            )
            if whatsapp_url:
                st.link_button(
                    "📲 Envoyer preuve de paiement WhatsApp",
                    whatsapp_url,
                    use_container_width=True,
                )

        except Exception as exc:
            st.error(f"Création de commande impossible : {exc}")


def render_my_orders_tab(user):
    st.markdown("### Mes commandes")
    user_id = get_value(user, "id", "user_id")
    orders = fetch_user_orders(user_id)

    if not orders:
        st.info("Aucune commande enregistrée pour le moment.")
        return

    for order in orders:
        render_order_card(order, show_actions=True)


def render_tracking_tab(user):
    st.markdown("### Tracking / Paiement")
    default_code = st.session_state.get("last_created_order_code", "")

    with st.form("tracking_form", clear_on_submit=False):
        order_code = st.text_input(
            "Référence commande",
            value=default_code,
            placeholder="Ex: AFRI-2026-0001",
        )
        search_clicked = st.form_submit_button("Rechercher", use_container_width=True)

    if search_clicked:
        order = fetch_order_by_code(order_code.strip())
        if not order:
            st.error("Commande introuvable.")
            return

        render_order_card(order, show_actions=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Marquer preuve envoyée",
                key=f"proof_sent_{get_order_code(order)}",
                use_container_width=True,
            ):
                ok = mark_payment_proof_sent_safely(order)
                if ok:
                    st.success("Preuve marquée comme envoyée.")
                    st.rerun()
                else:
                    st.warning("Impossible de mettre à jour le statut automatiquement.")

        with col2:
            support_url = build_support_whatsapp_url(get_order_code(order))
            if support_url:
                st.link_button(
                    "💬 Ouvrir WhatsApp support",
                    support_url,
                    use_container_width=True,
                )


def render_user_dashboard():
    user = current_user()
    if not user:
        return

    st.markdown("# Tableau de bord client")

    user_id = get_value(user, "id", "user_id")
    orders = fetch_user_orders(user_id)
    render_user_summary(orders)

    tab1, tab2, tab3 = st.tabs(
        ["Créer commande", "Mes commandes", "Tracking / Paiement"]
    )

    with tab1:
        render_create_order_tab(user)

    with tab2:
        render_my_orders_tab(user)

    with tab3:
        render_tracking_tab(user)


# =========================================================
# PUBLIC TRACKING
# =========================================================
def render_public_tracking():
    st.markdown("## Suivre une commande")
    with st.form("public_tracking_form", clear_on_submit=False):
        code = st.text_input("Référence commande", placeholder="Ex: AFRI-2026-0001")
        submitted = st.form_submit_button("Consulter", use_container_width=True)

    if submitted:
        order = fetch_order_by_code(code.strip())
        if order:
            render_order_card(order, show_actions=False)
        else:
            st.error("Commande introuvable.")


# =========================================================
# ADMIN
# =========================================================
def render_admin_sidebar():
    st.markdown("---")
    st.markdown("## Admin")

    if st.session_state.get("admin_authenticated"):
        st.success("Admin connecté")
        if st.button("Déconnexion admin", use_container_width=True):
            try:
                logout_admin()
            except Exception:
                pass
            st.session_state["admin_authenticated"] = False
            st.rerun()
        return

    configured = False
    try:
        configured = admin_is_configured()
    except Exception:
        configured = True

    if not configured:
        st.warning("Admin non configuré.")
        return

    with st.form("admin_login_form", clear_on_submit=True):
        admin_password = st.text_input("Mot de passe admin", type="password")
        admin_submit = st.form_submit_button("Connexion admin", use_container_width=True)

    if admin_submit:
        try:
            if verify_admin_password(admin_password):
                st.session_state["admin_authenticated"] = True
                st.success("Connexion admin réussie.")
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        except Exception as exc:
            st.error(f"Connexion admin impossible : {exc}")


def render_admin_dashboard():
    if not st.session_state.get("admin_authenticated"):
        return

    st.markdown("# Dashboard Admin")

    orders = list_all_orders_db(limit=500)
    if not orders:
        st.info("Aucune commande disponible.")
        return

    total_orders = len(orders)
    total_eur = sum(get_order_total_eur(order) for order in orders)
    total_xaf = sum(get_order_total_xaf(order) for order in orders)

    payment_counter = Counter(str(get_value(order, "payment_status", default="PENDING")) for order in orders)
    tracking_counter = Counter(str(get_order_tracking_status(order)) for order in orders)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Total commandes", str(total_orders))
    with col2:
        render_metric_card("TPV / GMV EUR", format_eur(total_eur))
    with col3:
        render_metric_card("TPV / GMV XAF", format_xaf(total_xaf))
    with col4:
        render_metric_card("Proof reçues", str(payment_counter.get("PROOF_RECEIVED", 0)))

    tab1, tab2 = st.tabs(["Vue globale", "Gestion commandes"])

    with tab1:
        st.write("**Statut paiement**")
        st.json(dict(payment_counter))
        st.write("**Statut tracking**")
        st.json(dict(tracking_counter))

    with tab2:
        columns = get_table_columns("orders")
        for order in orders:
            order_id = get_value(order, "id")
            code = get_order_code(order)
            merchant_name = get_value(order, "merchant_name", "site_name", default="-")
            payment_status = str(get_value(order, "payment_status", default="PENDING"))
            tracking_status = str(get_order_tracking_status(order))
            admin_note_value = str(get_value(order, "admin_note", default=""))

            with st.expander(
                f"{code or '-'} • {merchant_name} • {format_xaf(get_order_total_xaf(order))}",
                expanded=False,
            ):
                render_order_card(order, show_actions=False)

                with st.form(f"admin_order_update_{order_id}", clear_on_submit=False):
                    payment_options = ["PENDING", "PROOF_RECEIVED", "CONFIRMED", "REJECTED"]
                    tracking_options = [
                        "PENDING",
                        "PAID",
                        "ORDERED",
                        "IN_TRANSIT",
                        "ARRIVED_HUB",
                        "READY_FOR_PICKUP",
                        "DELIVERED",
                        "CANCELLED",
                    ]

                    payment_index = payment_options.index(payment_status) if payment_status in payment_options else 0
                    tracking_index = tracking_options.index(tracking_status) if tracking_status in tracking_options else 0

                    new_payment_status = payment_status
                    new_tracking_status = tracking_status
                    new_admin_note = admin_note_value

                    if "payment_status" in columns:
                        new_payment_status = st.selectbox(
                            "Statut paiement",
                            payment_options,
                            index=payment_index,
                            key=f"payment_status_select_{order_id}",
                        )

                    tracking_column_present = next(
                        (col for col in ["tracking_status", "order_status", "status"] if col in columns),
                        None,
                    )
                    if tracking_column_present:
                        new_tracking_status = st.selectbox(
                            "Statut tracking",
                            tracking_options,
                            index=tracking_index,
                            key=f"tracking_status_select_{order_id}",
                        )

                    if "admin_note" in columns:
                        new_admin_note = st.text_area(
                            "Note admin",
                            value=admin_note_value,
                            key=f"admin_note_input_{order_id}",
                        )

                    save_clicked = st.form_submit_button("Enregistrer", use_container_width=True)

                if save_clicked:
                    updates = {}
                    if "payment_status" in columns:
                        updates["payment_status"] = new_payment_status
                    if tracking_column_present:
                        updates[tracking_column_present] = new_tracking_status
                    if "admin_note" in columns:
                        updates["admin_note"] = new_admin_note
                    if "updated_at" in columns:
                        updates["updated_at"] = now_utc()

                    try:
                        updated = update_order_db(order_id, updates)
                        if updated:
                            st.success("Commande mise à jour.")
                            st.rerun()
                        else:
                            st.warning("Aucune mise à jour effectuée.")
                    except Exception as exc:
                        st.error(f"Mise à jour impossible : {exc}")


# =========================================================
# SIDEBAR
# =========================================================
def render_sidebar():
    with st.sidebar:
        try:
            render_sidebar_branding()
        except Exception:
            st.title(APP_TITLE)

        st.markdown("---")
        st.write(f"**Taux EUR → XAF :** {EUR_TO_XAF_RATE}")
        st.write(f"**Frais AfriPay :** {int(AFRIPAY_PERCENT_FEE * 100)}%")

        if MTN_MOMO_NUMBER:
            st.write(f"**MTN MoMo :** {MTN_MOMO_NUMBER}")
        if ORANGE_MONEY_NUMBER:
            st.write(f"**Orange Money :** {ORANGE_MONEY_NUMBER}")

        st.markdown("---")

        if user_is_logged_in():
            render_logged_user_box()
        else:
            render_login_area()

        render_admin_sidebar()


# =========================================================
# MAIN
# =========================================================
def main():
    bootstrap_core()
    init_app_state()

    st.title(APP_TITLE)
    st.caption("AfriPay Afrika — Paiement international, suivi commande, WhatsApp preuve de paiement")

    render_sidebar()

    if user_is_logged_in():
        render_user_dashboard()
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            render_public_tracking()
        with col2:
            st.markdown("## Résumé AfriPay")
            st.write("**Fonctionnalités disponibles :**")
            st.write("- Connexion OTP")
            st.write("- Création de commande")
            st.write("- Résumé financier EUR / XAF")
            st.write("- Preuve de paiement WhatsApp")
            st.write("- Tracking commande")
            st.write("- Dashboard client")

    if st.session_state.get("admin_authenticated"):
        st.markdown("---")
        render_admin_dashboard()


if __name__ == "__main__":
    main()