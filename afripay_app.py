# ===============================
# IMPORTS
# ===============================
import secrets
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import streamlit as st

from config.settings import APP_TITLE
from data.database import init_db
from core.session import (
    init_session,
    logout_user,
    logout_admin,
    login_user,
    restore_user_session,
)
from services.user_service import upsert_user
from services.auth_session_service import (
    create_user_session,
    get_active_session,
    touch_session,
    deactivate_session,
)
from services.order_service import (
    create_order_for_user,
    list_orders_for_user,
    get_order_by_code,
)
from services.admin_service import (
    admin_is_configured,
    verify_admin_password,
)
from services.settings_service import ensure_defaults
from ui.branding import render_sidebar_branding


# ===============================
# CONSTANTES
# ===============================
AFRIPAY_PUBLIC_URL = "https://afripayafrika.com"
EUR_TO_XAF_RATE = 655.957
AFRIPAY_PERCENT_FEE = 0.20

AFRIPAY_WHATSAPP_NUMBER = "316XXXXXXXX"

# ===============================
# HELPERS
# ===============================
def to_float(value, default=0.0):
    try:
        return float(value or 0)
    except:
        return default


def format_xaf(value):
    value = to_float(value, 0.0)
    rounded = int(value) if float(value).is_integer() else int(value) + 1
    return f"{rounded:,}".replace(",", ".")


def format_eur(value):
    value = to_float(value, 0.0)
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def eur_to_xaf(value_eur):
    return to_float(value_eur) * EUR_TO_XAF_RATE


def xaf_to_eur(value_xaf):
    return to_float(value_xaf) / EUR_TO_XAF_RATE if EUR_TO_XAF_RATE else 0


# ===============================
# CALCULS
# ===============================
def compute_dual_amounts(amount, currency):
    currency = str(currency).upper()

    if currency == "XAF":
        return amount, xaf_to_eur(amount)
    elif currency == "EUR":
        return eur_to_xaf(amount), amount

    return 0, 0


def calculate_afripay_fee(merchant_eur):
    fee_eur = merchant_eur * AFRIPAY_PERCENT_FEE
    fee_xaf = eur_to_xaf(fee_eur)
    return fee_xaf, fee_eur


def compute_payment_preview(amount, currency):
    merchant_xaf, merchant_eur = compute_dual_amounts(amount, currency)

    fee_xaf, fee_eur = calculate_afripay_fee(merchant_eur)

    return {
        "merchant_xaf": merchant_xaf,
        "merchant_eur": merchant_eur,
        "afripay_fee_xaf": fee_xaf,
        "afripay_fee_eur": fee_eur,
        "total_to_pay_xaf": merchant_xaf + fee_xaf,
        "total_to_pay_eur": merchant_eur + fee_eur,
    }


# ===============================
# WHATSAPP
# ===============================
def build_whatsapp_direct_url(phone, message):
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded}"


# ===============================
# PAGE CRÉATION COMMANDE (CORRIGÉE)
# ===============================
def page_creer_commande():

    st.title("Créer commande")

    merchant_total_amount = st.number_input("Montant marchand", min_value=0.0)
    merchant_currency = st.selectbox("Devise", ["XAF", "EUR"])

    preview = compute_payment_preview(merchant_total_amount, merchant_currency)

    st.metric("Total XAF", f"{format_xaf(preview['total_to_pay_xaf'])} XAF")

    with st.form("form"):
        product_url = st.text_input("Lien produit")
        product_title = st.text_input("Nom produit")
        site_name = st.text_input("Marchand")
        product_specs = st.text_area("Détails")
        delivery_address = st.text_area("Adresse")
        momo_provider = st.selectbox("Mobile Money", ["MTN", "Orange"])

        submitted = st.form_submit_button("Créer")

    if submitted:

        final_preview = compute_payment_preview(
            merchant_total_amount,
            merchant_currency,
        )

        if merchant_currency == "EUR":
            product_price_eur = merchant_total_amount
        else:
            product_price_eur = final_preview["merchant_eur"]

        # ===============================
        # 🔥 CORRECTION PRINCIPALE ICI
        # ===============================
        order_code = create_order_for_user(
            user_id=int(st.session_state["user_id"]),
            site_name=site_name,
            product_url=product_url,
            product_title=product_title,
            product_specs=product_specs,
            product_price_eur=product_price_eur,
            shipping_estimate_eur=0.0,
            delivery_address=delivery_address,
            momo_provider=momo_provider,

            # 🔥 DONNÉES FINANCIÈRES CORRECTES
            merchant_total_amount=merchant_total_amount,
            merchant_currency=merchant_currency,
            seller_fee_xaf=0,
            afripay_fee_xaf=final_preview["afripay_fee_xaf"],
            total_xaf=final_preview["total_to_pay_xaf"],
            total_to_pay_eur=final_preview["total_to_pay_eur"],
        )

        st.success(f"Commande créée : {order_code}")

        # ===============================
        # WHATSAPP PREUVE PAIEMENT
        # ===============================
        message = f"""
Bonjour AfriPay,

Je confirme le paiement.

Référence : {order_code}
Montant : {format_xaf(final_preview['total_to_pay_xaf'])} XAF

Merci.
"""

        url = build_whatsapp_direct_url(AFRIPAY_WHATSAPP_NUMBER, message)

        st.link_button("📲 Envoyer preuve de paiement WhatsApp", url)


# ===============================
# MAIN
# ===============================
def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    init_db()
    ensure_defaults()
    init_session()

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = True
        st.session_state["user_id"] = 1

    page_creer_commande()


if __name__ == "__main__":
    main()