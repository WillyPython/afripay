import os
import secrets
from collections import Counter, defaultdict
from datetime import datetime

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

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
    pbkdf2_verify_password,
    get_admin_hash,
)
from services.settings_service import ensure_defaults


# =========================================================
# COOKIE MANAGER
# =========================================================
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD", "afripay-cookie-secret-dev")

cookies = EncryptedCookieManager(
    prefix="afripay_",
    password=COOKIE_PASSWORD,
)


# =========================================================
# HELPERS
# =========================================================
def format_xaf(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0

    rounded = int(value) if float(value).is_integer() else int(value) + 1
    return f"{rounded:,}".replace(",", ".")


def format_eur(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0

    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def safe_get(row, key, default=""):
    try:
        value = row[key]
        return value if value not in (None, "") else default
    except Exception:
        return default


def parse_date(value):
    if not value:
        return None

    text = str(value).strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def normalize_status(status):
    mapping = {
        "CREEE": "Créée",
        "PAYEE": "Payée",
        "EN_COURS": "En cours",
        "LIVREE": "Livrée",
        "ANNULEE": "Annulée",
    }
    return mapping.get(str(status or "").strip().upper(), str(status or "—"))


def month_label(dt):
    months = [
        "Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
        "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc",
    ]
    return f"{months[dt.month - 1]} {dt.year}"


def merchant_status_to_step(merchant_status):
    status = str(merchant_status or "").strip().lower()

    mapping = {
        "commande passée": 3,
        "paiement effectué": 3,
        "confirmée par le marchand": 3,
        "en préparation": 3,
        "expédiée": 4,
        "en transit": 4,
        "livrée au transitaire": 5,
    }
    return mapping.get(status, 0)


def build_timeline_steps(order):
    order_status = str(safe_get(order, "order_status", "")).strip().upper()
    payment_status = str(safe_get(order, "payment_status", "")).strip().upper()
    merchant_status = safe_get(order, "merchant_status", "")

    merchant_step = merchant_status_to_step(merchant_status)

    return [
        {
            "title": "Commande créée",
            "done": order_status in {"CREEE", "PAYEE", "EN_COURS", "LIVREE"},
            "detail": f"Référence : {safe_get(order, 'order_code', '—')}",
        },
        {
            "title": "Paiement AfriPay confirmé",
            "done": payment_status in {"PAYE", "PAYÉ", "PAYEE", "PAYÉE"},
            "detail": f"Statut paiement : {safe_get(order, 'payment_status', '—')}",
        },
        {
            "title": "Commande passée chez marchand",
            "done": merchant_step >= 3,
            "detail": f"Statut marchand : {merchant_status or 'En attente'}",
        },
        {
            "title": "Expédiée",
            "done": merchant_step >= 4,
            "detail": f"Lien suivi : {safe_get(order, 'merchant_tracking_url', 'Non disponible')}",
        },
        {
            "title": "Livrée au transitaire",
            "done": merchant_step >= 5,
            "detail": f"Adresse transitaire : {safe_get(order, 'delivery_address', '—')}",
        },
    ]


def render_logistics_timeline(order, title="Timeline logistique"):
    st.markdown(f"### {title}")

    for index, step in enumerate(build_timeline_steps(order), start=1):
        icon = "🟢" if step["done"] else "⚪"
        st.markdown(f"**{icon} Étape {index} — {step['title']}**")
        st.caption(step["detail"])


# =========================================================
# COOKIE SESSION MANAGEMENT
# =========================================================
def save_session_token_in_cookie(token: str | None) -> None:
    """
    Sauvegarde ou supprime le token de session dans un cookie navigateur.
    """
    if token:
        cookies["session_token"] = token
    else:
        if "session_token" in cookies:
            del cookies["session_token"]

    cookies.save()


def restore_session_from_cookie() -> None:
    """
    Restaure automatiquement la session utilisateur si un token valide
    est présent dans le cookie navigateur.
    """
    if st.session_state.get("logged_in"):
        token = st.session_state.get("session_token")
        if token:
            touch_session(token)
        return

    token = cookies.get("session_token")

    if not token:
        return

    row = get_active_session(token)

    if not row:
        save_session_token_in_cookie(None)
        return

    restore_user_session(
        user_id=row["user_id"],
        phone=row.get("phone", ""),
        name=row.get("name", ""),
        session_token=row["session_token"],
    )

    touch_session(token)


# =========================================================
# SIDEBAR
# =========================================================
def render_sidebar() -> str:
    st.sidebar.image("assets/logo.png", width=190)
    st.sidebar.markdown("---")

    st.sidebar.markdown(
        """
        <h3 style="
            text-align:center;
            margin-bottom:6px;
            color:white;
            font-weight:700;
        ">
            AfriPay Afrika
        </h3>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        """
        <p style="
            text-align:center;
            font-size:13px;
            font-weight:700;
            margin-top:0;
            margin-bottom:0;
            color:#ff9900;
            text-shadow:0 0 10px rgba(255,153,0,0.9);
        ">
            ✨ Facilitateur des paiements internationaux
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")

    if st.session_state.get("logged_in"):
        st.sidebar.success("Connecté ✅")
        if st.sidebar.button("Déconnexion"):
            token = st.session_state.get("session_token")

            if token:
                deactivate_session(token)

            save_session_token_in_cookie(None)
            logout_user()
            st.rerun()
    else:
        st.sidebar.info("Non connecté")

    st.sidebar.markdown("---")

    return st.sidebar.radio(
        "Menu",
        [
            "Connexion",
            "Dashboard Client",
            "Suivre commande",
            "Simuler",
            "Créer commande",
            "Mes commandes",
            "Admin",
        ],
        index=0,
    )


# =========================================================
# PAGES
# =========================================================
def page_connexion() -> None:
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

    otp_input = st.text_input("Entrer OTP", type="password")
    name = st.text_input("Nom", placeholder="Optionnel")
    email = st.text_input("Email", placeholder="Optionnel")

    if st.button("Se connecter"):
        if not st.session_state.get("otp_code"):
            st.error("Demande d'abord un OTP.")
            return

        if phone.strip() != st.session_state.get("otp_phone"):
            st.error("Téléphone différent de celui utilisé pour l’OTP.")
            return

        if otp_input.strip() != st.session_state.get("otp_code"):
            st.error("OTP incorrect.")
            return

        clean_phone = phone.strip()
        clean_name = name.strip()
        clean_email = email.strip()

        user_id = upsert_user(
            phone=clean_phone,
            name=clean_name,
            email=clean_email,
        )

        session_token = create_user_session(
            user_id=user_id,
            phone=clean_phone,
        )

        login_user(
            user_id=user_id,
            phone=clean_phone,
            name=clean_name,
            session_token=session_token,
        )

        save_session_token_in_cookie(session_token)

        st.success("Connexion réussie ✅")
        st.rerun()


def page_dashboard_client() -> None:
    st.title("Dashboard Client")

    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté pour accéder à ton tableau de bord.")
        return

    rows = list_orders_for_user(int(st.session_state["user_id"]))

    total_orders = len(rows)
    paid_orders = 0
    in_progress_orders = 0
    delivered_orders = 0
    cancelled_orders = 0

    total_xaf_sum = 0.0
    total_eur_sum = 0.0

    status_counter = Counter()
    monthly_orders = defaultdict(int)
    monthly_volume = defaultdict(float)

    for row in rows:
        raw_status = str(safe_get(row, "order_status", "")).upper()
        total_xaf = float(safe_get(row, "total_xaf", 0) or 0)
        total_eur = float(safe_get(row, "total_to_pay_eur", 0) or 0)

        total_xaf_sum += total_xaf
        total_eur_sum += total_eur

        if raw_status == "PAYEE":
            paid_orders += 1
        elif raw_status == "EN_COURS":
            in_progress_orders += 1
        elif raw_status == "LIVREE":
            delivered_orders += 1
        elif raw_status == "ANNULEE":
            cancelled_orders += 1

        status_counter[normalize_status(raw_status)] += 1

        created_at = parse_date(safe_get(row, "created_at", ""))
        if created_at:
            key = created_at.strftime("%Y-%m")
            monthly_orders[key] += 1
            monthly_volume[key] += total_xaf

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mes commandes", total_orders)
    c2.metric("Payées", paid_orders)
    c3.metric("En cours", in_progress_orders)
    c4.metric("Livrées", delivered_orders)

    c5, c6, c7 = st.columns(3)
    c5.metric("Annulées", cancelled_orders)
    c6.metric("Montant cumulé XAF", f"{format_xaf(total_xaf_sum)} XAF")
    c7.metric("Montant cumulé EUR", f"{format_eur(total_eur_sum)} €")

    st.markdown("---")
    st.subheader("Résumé client")
    st.info(
        "AfriPay facilite vos paiements internationaux. "
        "Le dédouanement et la livraison finale restent sous votre responsabilité via votre transitaire / agent."
    )

    if not rows:
        st.info("Aucune commande pour le moment.")
        return

    col_chart_1, col_chart_2 = st.columns(2)

    with col_chart_1:
        st.markdown("### 📊 Répartition des commandes par statut")
        if status_counter:
            status_data = {
                "Statut": list(status_counter.keys()),
                "Commandes": list(status_counter.values()),
            }
            st.bar_chart(status_data, x="Statut", y="Commandes", use_container_width=True)
        else:
            st.info("Pas assez de données pour afficher le graphique des statuts.")

    with col_chart_2:
        st.markdown("### 📈 Évolution mensuelle des commandes")
        if monthly_orders:
            sorted_keys = sorted(monthly_orders.keys())
            evolution_data = {
                "Mois": [month_label(datetime.strptime(k, "%Y-%m")) for k in sorted_keys],
                "Commandes": [monthly_orders[k] for k in sorted_keys],
            }
            st.line_chart(evolution_data, x="Mois", y="Commandes", use_container_width=True)
        else:
            st.info("Pas assez de données pour afficher l’évolution mensuelle.")

    st.markdown("### 💰 Volume financier mensuel XAF")
    if monthly_volume:
        sorted_keys = sorted(monthly_volume.keys())
        volume_data = {
            "Mois": [month_label(datetime.strptime(k, "%Y-%m")) for k in sorted_keys],
            "Montant_XAF": [monthly_volume[k] for k in sorted_keys],
        }
        st.area_chart(volume_data, x="Mois", y="Montant_XAF", use_container_width=True)
    else:
        st.info("Pas assez de données pour afficher le volume financier.")

    st.markdown("---")

    latest = rows[0]

    st.subheader("Dernière commande")
    info1, info2 = st.columns(2)

    with info1:
        st.write(f"**Référence :** {safe_get(latest, 'order_code', '—')}")
        st.write(f"**Produit :** {safe_get(latest, 'product_name', '—')}")
        st.write(f"**Marchand :** {safe_get(latest, 'site_name', '—')}")
        st.write(f"**Montant XAF :** {format_xaf(safe_get(latest, 'total_xaf', 0))} XAF")
        st.write(f"**Montant EUR :** {format_eur(safe_get(latest, 'total_to_pay_eur', 0))} €")

    with info2:
        st.write(f"**Statut commande :** {normalize_status(safe_get(latest, 'order_status', '—'))}")
        st.write(f"**Statut paiement :** {safe_get(latest, 'payment_status', '—')}")
        st.write(f"**Adresse transitaire :** {safe_get(latest, 'delivery_address', '—')}")

    render_logistics_timeline(latest)

    merchant_order_number = safe_get(latest, "merchant_order_number", "")
    merchant_confirmation_url = safe_get(latest, "merchant_confirmation_url", "")
    merchant_tracking_url = safe_get(latest, "merchant_tracking_url", "")
    merchant_purchase_date = safe_get(latest, "merchant_purchase_date", "")
    merchant_status = safe_get(latest, "merchant_status", "")

    if any([
        merchant_order_number,
        merchant_confirmation_url,
        merchant_tracking_url,
        merchant_purchase_date,
        merchant_status,
    ]):
        st.markdown("### Informations marchand")
        if merchant_order_number:
            st.write(f"**Numéro commande marchand :** {merchant_order_number}")
        if merchant_purchase_date:
            st.write(f"**Date d'achat :** {merchant_purchase_date}")
        if merchant_status:
            st.write(f"**Statut marchand :** {merchant_status}")
        if merchant_confirmation_url:
            st.write(f"**Lien confirmation :** {merchant_confirmation_url}")
        if merchant_tracking_url:
            st.write(f"**Lien suivi :** {merchant_tracking_url}")


def page_tracking() -> None:
    st.title("Suivre une commande")
    st.caption("Entre ton numéro de commande. Exemple : CMD-2026-001")

    order_code = st.text_input("Numéro de commande", placeholder="CMD-2026-001")

    if st.button("Rechercher"):
        if not order_code.strip():
            st.error("Entre un numéro de commande.")
            return

        row = get_order_by_code(order_code.strip())

        if not row:
            st.error("Commande introuvable.")
            return

        st.success(f"Commande : **{safe_get(row, 'order_code', '')}**")
        st.write("**Produit :**", safe_get(row, "product_title", "—"))
        st.write("**Marchand :**", safe_get(row, "site_name", "—"))
        st.write("**Montant XAF :**", f"{format_xaf(safe_get(row, 'total_xaf', 0))} XAF")
        st.write("**Montant EUR :**", f"{format_eur(safe_get(row, 'total_to_pay_eur', 0))} €")
        st.write("**Statut commande :**", normalize_status(safe_get(row, "order_status", "—")))
        st.write("**Statut paiement :**", safe_get(row, "payment_status", "—"))
        st.write("**Adresse transitaire :**", safe_get(row, "delivery_address", "—"))

        render_logistics_timeline(row)

        merchant_status = safe_get(row, "merchant_status", "")
        merchant_order_number = safe_get(row, "merchant_order_number", "")
        merchant_confirmation_url = safe_get(row, "merchant_confirmation_url", "")
        merchant_tracking_url = safe_get(row, "merchant_tracking_url", "")
        merchant_purchase_date = safe_get(row, "merchant_purchase_date", "")

        if any([
            merchant_status,
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
        ]):
            st.subheader("Informations marchand")
            if merchant_order_number:
                st.write("**Numéro commande marchand :**", merchant_order_number)
            if merchant_purchase_date:
                st.write("**Date d'achat :**", merchant_purchase_date)
            if merchant_status:
                st.write("**Statut marchand :**", merchant_status)
            if merchant_confirmation_url:
                st.write("**Lien confirmation :**", merchant_confirmation_url)
            if merchant_tracking_url:
                st.write("**Lien suivi :**", merchant_tracking_url)
        else:
            st.info("Les informations marchand ne sont pas encore disponibles.")


def page_simuler() -> None:
    st.title("Simuler paiement")

    amount_xaf = st.number_input("Montant marchand (XAF)", min_value=0.0, value=0.0, step=1000.0)
    seller_fee = st.number_input("Frais vendeur / site (XAF)", min_value=0.0, value=0.0, step=500.0)
    afripay_fee = st.number_input("Frais de service AfriPay (XAF)", min_value=0.0, value=0.0, step=500.0)

    total = amount_xaf + seller_fee + afripay_fee
    st.metric("Total à payer (XAF)", f"{format_xaf(total)} XAF")


def page_creer_commande() -> None:
    st.title("Créer commande")

    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté.")
        return

    st.info(
        "📌 AfriPay facilite le paiement international. "
        "Le client reste responsable du dédouanement et de la livraison finale via son transitaire / agent."
    )

    st.markdown("### Informations importantes à valider")

    st.warning(
        "Message juridique : AfriPay agit comme facilitateur de paiement international. "
        "AfriPay n'assure pas le dédouanement ni la livraison finale. "
        "Le client demeure responsable de son transitaire, de l'adresse de réception finale "
        "et des formalités éventuelles liées à l'importation."
    )

    st.info(
        "Message opérationnel : pour éviter toute erreur, le client doit saisir le montant total affiché par le marchand "
        "et renseigner l'adresse de son transitaire / agence, qui pourra aussi servir d'adresse de livraison sur le site marchand."
    )

    with st.form("create_order_form"):
        site_name = st.text_input("Site marchand", placeholder="Amazon, Temu, Zara...")
        product_url = st.text_input("Lien produit")
        product_title = st.text_input("Nom du produit / commande")
        product_specs = st.text_area(
            "Caractéristiques / variantes",
            placeholder="Taille, couleur, quantité...",
        )

        col1, col2 = st.columns(2)

        with col1:
            product_price_eur = st.number_input("Montant produit (EUR)", min_value=0.0, value=0.0, step=1.0)

        with col2:
            shipping_estimate_eur = st.number_input("Transport / livraison (EUR)", min_value=0.0, value=0.0, step=1.0)

        delivery_address = st.text_area("Adresse agence / transitaire (obligatoire)")
        momo_provider = st.selectbox("Opérateur Mobile Money", ["", "MTN", "Orange"], index=0)

        client_ack = st.checkbox(
            "Je confirme avoir lu et accepté les informations juridiques et opérationnelles ci-dessus."
        )

        total_eur = product_price_eur + shipping_estimate_eur
        st.caption(f"Total estimé : {format_eur(total_eur)} EUR")

        submitted = st.form_submit_button("Créer la commande")

    if submitted:
        if not site_name.strip():
            st.error("Le site marchand est obligatoire.")
            return
        if not product_title.strip():
            st.error("Le nom du produit est obligatoire.")
            return
        if total_eur <= 0:
            st.error("Le montant total doit être supérieur à 0.")
            return
        if not delivery_address.strip():
            st.error("Adresse agence / transitaire obligatoire.")
            return
        if not client_ack:
            st.error("Tu dois valider les informations juridiques et opérationnelles avant de créer la commande.")
            return

        order_code = create_order_for_user(
            user_id=int(st.session_state["user_id"]),
            site_name=site_name.strip(),
            product_url=product_url.strip(),
            product_title=product_title.strip(),
            product_specs=product_specs.strip(),
            product_price_eur=float(product_price_eur),
            shipping_estimate_eur=float(shipping_estimate_eur),
            delivery_address=delivery_address.strip(),
            momo_provider=momo_provider.strip() or None,
        )

        st.success(f"Commande créée ✅ Numéro : **{order_code}**")


def page_mes_commandes() -> None:
    st.title("Mes commandes")

    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté.")
        return

    rows = list_orders_for_user(int(st.session_state["user_id"]))

    if not rows:
        st.info("Aucune commande.")
        return

    for row in rows:
        code = safe_get(row, "order_code", f"#{safe_get(row, 'id', '')}")
        total = safe_get(row, "total_xaf", 0)
        total_eur = safe_get(row, "total_to_pay_eur", 0)
        status = safe_get(row, "order_status", "—")

        expander_title = f"{code} — {normalize_status(status)} — {format_xaf(total)} XAF"

        with st.expander(expander_title):
            st.write(f"**Créée le :** {safe_get(row, 'created_at', '—')}")
            st.write(f"**Produit :** {safe_get(row, 'product_name', '—')}")
            st.write(f"**Marchand :** {safe_get(row, 'site_name', '—')}")
            st.write(f"**Montant XAF :** {format_xaf(total)} XAF")
            st.write(f"**Montant EUR :** {format_eur(total_eur)} €")
            st.write(f"**Frais vendeur :** {format_xaf(safe_get(row, 'seller_fee_xaf', 0))} XAF")
            st.write(f"**Frais AfriPay :** {format_xaf(safe_get(row, 'afripay_fee_xaf', 0))} XAF")
            st.write(f"**Adresse agence / transitaire :** {safe_get(row, 'delivery_address', '—')}")
            st.write(f"**Paiement :** {safe_get(row, 'payment_status', '—')}")
            st.write(f"**Statut :** {normalize_status(status)}")

            render_logistics_timeline(row, title="Timeline logistique de la commande")

            merchant_order_number = safe_get(row, "merchant_order_number", "")
            merchant_confirmation_url = safe_get(row, "merchant_confirmation_url", "")
            merchant_tracking_url = safe_get(row, "merchant_tracking_url", "")
            merchant_purchase_date = safe_get(row, "merchant_purchase_date", "")
            merchant_status = safe_get(row, "merchant_status", "")

            if any([
                merchant_order_number,
                merchant_confirmation_url,
                merchant_tracking_url,
                merchant_purchase_date,
                merchant_status,
            ]):
                st.markdown("### Informations marchand")
                if merchant_order_number:
                    st.write(f"**Numéro commande marchand :** {merchant_order_number}")
                if merchant_purchase_date:
                    st.write(f"**Date d'achat :** {merchant_purchase_date}")
                if merchant_status:
                    st.write(f"**Statut marchand :** {merchant_status}")
                if merchant_confirmation_url:
                    st.write(f"**Lien confirmation :** {merchant_confirmation_url}")
                if merchant_tracking_url:
                    st.write(f"**Lien suivi :** {merchant_tracking_url}")


def page_admin() -> None:
    st.title("Administration AfriPay")

    if not st.session_state.get("admin_logged_in"):
        st.subheader("Connexion Admin")
        password = st.text_input("Mot de passe admin", type="password")

        if st.button("Se connecter (Admin)"):
            stored_hash = get_admin_hash()

            if not stored_hash:
                st.error("Admin non configuré.")
                return

            if pbkdf2_verify_password(password, stored_hash):
                st.session_state["admin_logged_in"] = True
                st.success("Admin connecté ✅")
                st.switch_page("pages/admin_dashboard.py")
            else:
                st.error("Mot de passe incorrect.")

        st.caption("Conseil : définis ADMIN_PASSWORD dans les variables d’environnement.")
        return

    st.success("Bienvenue dans l'espace administration")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Ouvrir le Dashboard Admin", use_container_width=True):
            st.switch_page("pages/admin_dashboard.py")

    with col2:
        if st.button("Déconnexion Admin", use_container_width=True):
            logout_admin()
            st.rerun()

    st.info(
        "Clique sur « Ouvrir le Dashboard Admin » pour accéder directement à la page sécurisée admin_dashboard."
    )


# =========================================================
# MAIN
# =========================================================
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    if not cookies.ready():
        st.stop()

    init_db()
    ensure_defaults()
    init_session()
    restore_session_from_cookie()

    menu = render_sidebar()

    if menu == "Connexion":
        page_connexion()
    elif menu == "Dashboard Client":
        page_dashboard_client()
    elif menu == "Suivre commande":
        page_tracking()
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