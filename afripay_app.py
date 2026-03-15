import secrets
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime

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


AFRIPAY_PUBLIC_URL = "https://afripayafrika.com"
EUR_TO_XAF_RATE = 655.957

MENU_OPTIONS = [
    "Connexion",
    "Dashboard Client",
    "Suivre commande",
    "Simuler",
    "Créer commande",
    "Mes commandes",
    "Admin",
]

ORDER_TYPE_PHYSICAL = "Produit physique"
ORDER_TYPE_SERVICE = "Service / paiement digital"


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


def eur_to_xaf(value_eur):
    try:
        value_eur = float(value_eur or 0)
    except (TypeError, ValueError):
        value_eur = 0.0
    return value_eur * EUR_TO_XAF_RATE


def xaf_to_eur(value_xaf):
    try:
        value_xaf = float(value_xaf or 0)
    except (TypeError, ValueError):
        value_xaf = 0.0
    return value_xaf / EUR_TO_XAF_RATE if EUR_TO_XAF_RATE else 0.0


def safe_get(row, key, default=""):
    try:
        value = row[key]
        return value if value not in (None, "") else default
    except Exception:
        return default


def get_product_label(row, default="—"):
    value = safe_get(row, "product_title", "")
    if value:
        return value

    value = safe_get(row, "product_name", "")
    if value:
        return value

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

    steps = [
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
            "title": "Commande passée chez le marchand",
            "done": merchant_step >= 3,
            "detail": f"Statut marchand : {merchant_status or 'En attente'}",
        },
        {
            "title": "Commande expédiée",
            "done": merchant_step >= 4,
            "detail": f"Lien suivi : {safe_get(order, 'merchant_tracking_url', 'Non disponible')}",
        },
        {
            "title": "Livrée au transitaire",
            "done": merchant_step >= 5,
            "detail": f"Adresse transitaire : {safe_get(order, 'delivery_address', '—')}",
        },
    ]

    current_index = None
    for i, step in enumerate(steps):
        if step["done"]:
            current_index = i

    if current_index is None:
        current_index = 0

    return steps, current_index


def render_logistics_timeline(order, title="Timeline logistique"):
    st.markdown(f"### {title}")

    steps, current_index = build_timeline_steps(order)

    for index, step in enumerate(steps, start=1):
        step_position = index - 1

        if step_position < current_index:
            icon = "🟢"
        elif step_position == current_index:
            icon = "🟡"
        else:
            icon = "⚪"

        st.markdown(f"**{icon} Étape {index} — {step['title']}**")
        st.caption(step["detail"])


def save_session_token_in_query_params(token: str | None) -> None:
    if token:
        st.query_params["session_token"] = token
    else:
        try:
            del st.query_params["session_token"]
        except Exception:
            pass


def restore_session_from_query_params() -> None:
    if st.session_state.get("logged_in"):
        token = st.session_state.get("session_token")
        if token:
            touch_session(token)
        return

    token = st.query_params.get("session_token")

    if not token:
        return

    row = get_active_session(token)

    if not row:
        save_session_token_in_query_params(None)
        return

    restore_user_session(
        user_id=row["user_id"],
        phone=row["phone"] if "phone" in row.keys() else "",
        name=row["name"] if "name" in row.keys() else "",
        session_token=row["session_token"],
    )

    touch_session(token)


def compute_dual_amounts(merchant_total_amount, merchant_currency):
    currency = str(merchant_currency or "").strip().upper()

    try:
        amount = float(merchant_total_amount or 0)
    except (TypeError, ValueError):
        amount = 0.0

    if currency == "XAF":
        total_xaf = amount
        total_eur = xaf_to_eur(amount)
    else:
        total_eur = amount
        total_xaf = eur_to_xaf(amount)

    return total_xaf, total_eur


def build_whatsapp_order_message(
    order_code,
    product_title,
    merchant_total_amount,
    merchant_currency,
    product_url,
):
    clean_product_title = str(product_title or "").strip() or "Produit ou service non précisé"
    clean_product_url = str(product_url or "").strip()
    currency = str(merchant_currency or "").strip().upper() or "EUR"

    total_xaf, total_eur = compute_dual_amounts(merchant_total_amount, currency)

    lines = [
        "Bonjour 👋",
        "",
        "Votre commande AfriPay a bien été créée ✅",
        "",
        f"Référence : {order_code}",
        f"Produit / Service : {clean_product_title}",
        "Montant marchand estimé :",
        f"{format_xaf(total_xaf)} XAF ({format_eur(total_eur)} EUR)",
        f"Devise d'origine du marchand : {currency}",
    ]

    if clean_product_url:
        lines.extend(
            [
                "",
                "Lien du produit / service :",
                clean_product_url,
            ]
        )

    lines.extend(
        [
            "",
            "Vous pouvez suivre votre commande directement dans AfriPay.",
            "",
            "🚀 AfriPay permet de payer vos achats et services internationaux depuis l’Afrique avec Mobile Money.",
            "",
            "Exemples : Amazon, Temu, certifications, universités, logiciels, abonnements, services en ligne.",
            "",
            "💡 Essayez AfriPay pour vos prochains paiements internationaux :",
            AFRIPAY_PUBLIC_URL,
            "",
            "AfriPay Afrika",
            "Facilitateur des paiements internationaux",
        ]
    )

    return "\n".join(lines)


def build_whatsapp_share_url(message: str) -> str:
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/?text={encoded_message}"


def refresh_captcha(prefix: str) -> None:
    a = secrets.randbelow(8) + 2
    b = secrets.randbelow(8) + 1
    st.session_state[f"{prefix}_captcha_a"] = a
    st.session_state[f"{prefix}_captcha_b"] = b
    st.session_state[f"{prefix}_captcha_expected"] = str(a + b)


def ensure_captcha(prefix: str) -> None:
    expected_key = f"{prefix}_captcha_expected"
    if expected_key not in st.session_state:
        refresh_captcha(prefix)


def get_captcha_error(prefix: str) -> str:
    return str(st.session_state.get(f"{prefix}_captcha_error", "")).strip()


def set_captcha_error(prefix: str, message: str) -> None:
    st.session_state[f"{prefix}_captcha_error"] = str(message or "").strip()


def clear_captcha_error(prefix: str) -> None:
    st.session_state[f"{prefix}_captcha_error"] = ""


def get_captcha_status(prefix: str, user_input: str) -> str:
    expected = str(st.session_state.get(f"{prefix}_captcha_expected", "")).strip()
    provided = str(user_input or "").strip()

    if not provided:
        return "empty"

    if not expected:
        return "missing"

    if provided != expected:
        return "invalid"

    return "ok"


def render_captcha_block(prefix: str, title: str = "Vérification humaine") -> str:
    ensure_captcha(prefix)

    a = st.session_state.get(f"{prefix}_captcha_a", 0)
    b = st.session_state.get(f"{prefix}_captcha_b", 0)

    st.markdown(f"### {title}")
    st.warning("Captcha obligatoire : vous devez saisir le résultat exact pour continuer.")
    st.info(
        f"Protection anti-bot AfriPay : veuillez résoudre l'opération suivante avant de continuer : **{a} + {b} = ?**"
    )

    existing_error = get_captcha_error(prefix)
    if existing_error:
        st.error(existing_error)

    col1, col2 = st.columns([3, 1])

    with col1:
        captcha_input = st.text_input(
            "Résultat de l'opération *",
            key=f"{prefix}_captcha_input",
            placeholder="Captcha obligatoire : entrez le résultat exact",
            help="Ce captcha est obligatoire. Sans le bon résultat, vous ne pourrez pas continuer.",
        )

        status = get_captcha_status(prefix, captcha_input)
        if captcha_input.strip():
            if status == "ok":
                st.success("Captcha correct ✅")
            elif status in {"invalid", "missing"}:
                st.error("Captcha incorrect ❌")

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Nouveau calcul", key=f"{prefix}_captcha_refresh"):
            refresh_captcha(prefix)
            clear_captcha_error(prefix)
            st.rerun()

    st.caption("Saisissez le résultat exact du captcha, puis cliquez sur le bouton de validation de cette page.")

    return captcha_input


def init_navigation_state() -> None:
    if "main_menu" not in st.session_state:
        st.session_state["main_menu"] = "Connexion"


def schedule_menu_redirect(menu_name: str) -> None:
    if menu_name in MENU_OPTIONS:
        st.session_state["pending_main_menu"] = menu_name


def apply_pending_menu_redirect() -> None:
    pending_menu = st.session_state.pop("pending_main_menu", None)
    if pending_menu in MENU_OPTIONS:
        st.session_state["main_menu"] = pending_menu


def consume_flash_message() -> None:
    flash_message = st.session_state.pop("flash_message", "")
    if flash_message:
        st.success(flash_message)


def render_test_otp_panel(current_phone: str = "") -> None:
    current_phone = str(current_phone or "").strip()
    otp_code = str(st.session_state.get("otp_code", "") or "").strip()
    otp_phone = str(st.session_state.get("otp_phone", "") or "").strip()

    if not otp_code:
        st.info(
            "Aucun OTP de test généré pour le moment. "
            "Clique sur « Envoyer OTP » pour générer un code visible à l’écran."
        )
        return

    if current_phone and otp_phone and current_phone != otp_phone:
        st.warning(
            "Un OTP de test existe déjà pour un autre numéro. "
            "Utilise le même numéro ou demande un nouvel OTP."
        )

    st.markdown("## 🔐 MODE TEST AFRIPAY")
    st.warning(
        "Ce code OTP est visible à l’écran uniquement pour le test privé. "
        "Il n’est pas encore envoyé par SMS ni par WhatsApp."
    )

    st.markdown(
        f"""
<div style="
    border: 3px solid #16a34a;
    border-radius: 16px;
    padding: 22px;
    margin: 12px 0 18px 0;
    background-color: rgba(22, 163, 74, 0.10);
    text-align: center;
">
    <div style="font-size: 18px; font-weight: 800; margin-bottom: 12px;">
        NUMÉRO DE TÉLÉPHONE LIÉ
    </div>
    <div style="font-size: 28px; font-weight: 900; margin-bottom: 18px;">
        {otp_phone or "—"}
    </div>
    <div style="font-size: 18px; font-weight: 800; margin-bottom: 10px;">
        CODE OTP DE TEST
    </div>
    <div style="font-size: 46px; font-weight: 900; letter-spacing: 10px; line-height: 1.2;">
        {otp_code}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.info(
        "Conserve ce code et ce numéro tels qu’affichés ci-dessus. "
        "Ils resteront visibles tant qu’un nouvel OTP n’est pas demandé ou que la connexion n’est pas validée."
    )


def clear_login_test_otp() -> None:
    st.session_state.pop("otp_code", None)
    st.session_state.pop("otp_phone", None)


def render_sidebar() -> str:
    render_sidebar_branding()

    if st.session_state.get("logged_in"):
        st.sidebar.success("Connecté ✅")
        connected_phone = st.session_state.get("phone", "")
        if connected_phone:
            st.sidebar.caption(f"Téléphone : {connected_phone}")

        if st.sidebar.button("Déconnexion"):
            token = st.session_state.get("session_token")

            if token:
                deactivate_session(token)

            save_session_token_in_query_params(None)
            clear_login_test_otp()
            logout_user()
            schedule_menu_redirect("Connexion")
            st.rerun()
    else:
        st.sidebar.info("Non connecté")

    st.sidebar.markdown("---")

    st.sidebar.radio(
        "Menu",
        MENU_OPTIONS,
        key="main_menu",
    )

    return st.session_state["main_menu"]


def page_connexion() -> None:
    st.title("Connexion")
    consume_flash_message()

    st.markdown(
        """
### 🌍 Que pouvez-vous payer avec AfriPay ?

AfriPay permet de payer vos **achats et services internationaux** avec Mobile Money depuis l’Afrique.

**Exemples :**

• 🛒 Produits : Amazon, Temu, AliExpress  
• 🎓 Études : certifications de diplômes, universités, examens  
• 💻 Digital : logiciels, hébergement, abonnements  
• 📦 Commerce : achats pour revente locale
"""
    )

    st.markdown(
        """
### 🔒 Pourquoi faire confiance à AfriPay ?

✅ Connexion sécurisée par OTP  
✅ Vérification humaine anti-bot  
✅ Suivi des commandes directement dans AfriPay  
✅ Paiements internationaux facilités
"""
    )

    st.info(
        "Connexion privée de test AfriPay. "
        "Après connexion, vous serez redirigé vers « Créer commande » pour commencer votre opération."
    )

    default_phone = str(st.session_state.get("otp_phone", "") or "")
    phone = st.text_input("Téléphone", value=default_phone, placeholder="+2376...")

    render_test_otp_panel(current_phone=phone)

    captcha_input = render_captcha_block("login", title="Captcha sécurité connexion")

    if st.button("Envoyer OTP", use_container_width=True):
        clean_phone = str(phone or "").strip()

        if not clean_phone:
            st.error("Entre ton numéro.")
            return

        captcha_status = get_captcha_status("login", captcha_input)

        if captcha_status == "empty":
            set_captcha_error(
                "login",
                "Captcha obligatoire : veuillez entrer le résultat de l'opération avant d'envoyer l'OTP.",
            )
            st.rerun()
            return

        if captcha_status in {"invalid", "missing"}:
            set_captcha_error(
                "login",
                "Captcha incorrect : veuillez entrer le résultat exact de l'opération pour envoyer l'OTP.",
            )
            refresh_captcha("login")
            st.rerun()
            return

        clear_captcha_error("login")

        otp = f"{secrets.randbelow(900000) + 100000}"
        st.session_state["otp_code"] = otp
        st.session_state["otp_phone"] = clean_phone
        st.success("OTP de test généré avec succès ✅")
        st.rerun()

    otp_input = st.text_input(
        "Entrer OTP",
        key="login_otp_input",
        placeholder="Entrez ici le code OTP affiché ci-dessus",
    )
    name = st.text_input("Nom", placeholder="Optionnel")
    email = st.text_input("Email", placeholder="Optionnel")

    if st.button("Se connecter", use_container_width=True):
        stored_otp = str(st.session_state.get("otp_code", "") or "").strip()
        stored_phone = str(st.session_state.get("otp_phone", "") or "").strip()
        clean_phone = str(phone or "").strip()

        if not stored_otp:
            st.error("Demande d'abord un OTP.")
            return

        if not clean_phone:
            st.error("Entre le numéro de téléphone utilisé pour demander l’OTP.")
            return

        if clean_phone != stored_phone:
            st.error("Téléphone différent de celui utilisé pour l’OTP.")
            return

        if str(otp_input or "").strip() != stored_otp:
            st.error("OTP incorrect.")
            return

        clean_name = str(name or "").strip()
        clean_email = str(email or "").strip()

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

        save_session_token_in_query_params(session_token)

        clear_captcha_error("login")
        refresh_captcha("login")
        clear_login_test_otp()

        st.session_state["flash_message"] = "Connexion réussie ✅"
        schedule_menu_redirect("Créer commande")
        st.rerun()


def page_dashboard_client() -> None:
    st.title("Dashboard Client")
    consume_flash_message()

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
        "Le dédouanement et la livraison finale restent sous votre responsabilité via votre transitaire / agent lorsqu’il s’agit d’un produit physique."
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
        st.write(f"**Produit / Service :** {get_product_label(latest)}")
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
        st.write("**Produit / Service :**", get_product_label(row))
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
    consume_flash_message()

    if not st.session_state.get("logged_in"):
        st.warning("Tu dois être connecté.")
        return

    st.info(
        "📌 Étape principale après connexion : crée d’abord ta commande. "
        "Tu pourras ensuite vérifier le résultat dans « Mes commandes » puis dans le Dashboard Client."
    )

    st.info(
        "📌 AfriPay facilite le paiement international. "
        "Pour un produit physique, le transitaire reste sous la responsabilité du client. "
        "Pour un service ou paiement digital, aucun transitaire n’est requis."
    )

    st.markdown("### Comment créer votre commande")
    st.markdown(
        """
1. Choisissez le **type de commande**  
2. Collez le **lien du produit ou du service**  
3. Indiquez le **nom du produit ou du service**  
4. Saisissez le **montant total affiché par le marchand**  
5. Choisissez la **devise du marchand**  
6. Si c’est un produit physique, renseignez l'**adresse du transitaire / agence**  
7. Choisissez votre **opérateur Mobile Money**
"""
    )

    st.warning(
        "Message juridique : AfriPay agit comme facilitateur de paiement international. "
        "AfriPay n'assure pas le dédouanement ni la livraison finale des produits physiques. "
        "Le client demeure responsable de son transitaire, de l'adresse de réception finale "
        "et des formalités éventuelles liées à l'importation."
    )

    st.info(
        "Conseil pratique : saisissez le montant total final affiché par le marchand. "
        "Ce montant peut être en XAF ou en EUR selon le site ou le vendeur."
    )

    with st.form("create_order_form"):
        st.markdown("### 🔗 Informations principales")

        order_type = st.selectbox(
            "Type de commande *",
            [ORDER_TYPE_PHYSICAL, ORDER_TYPE_SERVICE],
            index=0,
            help="Choisissez « Produit physique » pour un achat à livrer, ou « Service / paiement digital » pour une certification, un abonnement, un logiciel, etc.",
        )

        product_url = st.text_input(
            "🔗 Lien du produit ou du service *",
            placeholder="Collez ici le lien Amazon, Temu, WES, logiciel, hébergement, université, etc.",
            help="Lien du produit ou du service à payer.",
        )

        st.caption(
            "💡 Astuce : Collez ici le lien du produit ou du service. "
            "Si votre commande contient plusieurs éléments, saisissez simplement le montant total affiché par le marchand."
        )

        product_title = st.text_input(
            "🛍 Nom du produit ou du service *",
            placeholder="Exemple : Routeur Wi-Fi, Certification diplôme, Hébergement web annuel...",
        )

        site_name = st.text_input(
            "🏪 Site marchand / organisme *",
            placeholder="Exemple : Amazon, Temu, WES, IELTS, Hostinger, Université...",
        )

        product_specs = st.text_area(
            "📋 Caractéristiques / détails utiles",
            placeholder="Exemple : taille, couleur, quantité, numéro de dossier, type de service...",
        )

        st.markdown("### 💶 Montant du marchand")

        merchant_total_amount = st.number_input(
            "Montant total affiché par le marchand *",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

        merchant_currency = st.selectbox(
            "Devise du marchand *",
            ["XAF", "EUR"],
            index=0,
            help="Choisissez la devise réellement affichée par le site marchand ou le service.",
        )

        preview_total_xaf, preview_total_eur = compute_dual_amounts(
            merchant_total_amount,
            merchant_currency,
        )

        st.caption(
            f"Montant marchand estimé : {format_xaf(preview_total_xaf)} XAF "
            f"({format_eur(preview_total_eur)} EUR)"
        )

        st.markdown("### 🚚 Livraison et paiement")

        requires_forwarder = order_type == ORDER_TYPE_PHYSICAL

        if requires_forwarder:
            delivery_address = st.text_area(
                "📦 Adresse du transitaire / agence *",
                placeholder="Exemple : nom de l'agence, ville, quartier, contact utile...",
                help="Cette adresse doit correspondre à l'adresse utilisée pour la réception de la commande physique.",
            )
            st.caption("Saisissez le résultat exact du captcha, puis cliquez sur « Créer la commande ».")
        else:
            delivery_address = ""
            st.success("Aucun transitaire requis ✅")
            st.caption("Cette commande concerne un service / paiement digital. Saisissez le captcha puis cliquez sur « Créer la commande ».")

        momo_provider = st.selectbox(
            "📱 Opérateur Mobile Money",
            ["", "MTN", "Orange"],
            index=0,
        )

        client_ack = st.checkbox(
            "Je confirme avoir lu et accepté les informations juridiques et opérationnelles ci-dessus."
        )

        captcha_input = render_captcha_block("order", title="Captcha sécurité création commande")

        submitted = st.form_submit_button("Créer la commande", use_container_width=True)

    if submitted:
        captcha_status = get_captcha_status("order", captcha_input)

        if captcha_status == "empty":
            set_captcha_error(
                "order",
                "Captcha obligatoire : veuillez entrer le résultat de l'opération avant de créer la commande.",
            )
            st.rerun()
            return

        if captcha_status in {"invalid", "missing"}:
            set_captcha_error(
                "order",
                "Captcha incorrect : veuillez entrer le résultat exact de l'opération avant de créer la commande.",
            )
            refresh_captcha("order")
            st.rerun()
            return

        clear_captcha_error("order")

        if not product_url.strip():
            st.error("Le lien du produit ou du service est obligatoire.")
            return

        if not product_title.strip():
            st.error("Le nom du produit ou du service est obligatoire.")
            return

        if not site_name.strip():
            st.error("Le site marchand / organisme est obligatoire.")
            return

        if merchant_total_amount <= 0:
            st.error("Le montant total affiché par le marchand doit être supérieur à 0.")
            return

        if requires_forwarder and not delivery_address.strip():
            st.error("L'adresse du transitaire / agence est obligatoire pour un produit physique.")
            return

        if not client_ack:
            st.error("Tu dois valider les informations juridiques et opérationnelles avant de créer la commande.")
            return

        final_total_xaf, final_total_eur = compute_dual_amounts(
            merchant_total_amount,
            merchant_currency,
        )

        if merchant_currency == "EUR":
            product_price_eur = float(merchant_total_amount)
            shipping_estimate_eur = 0.0
        else:
            product_price_eur = float(final_total_eur)
            shipping_estimate_eur = 0.0

        order_code = create_order_for_user(
            user_id=int(st.session_state["user_id"]),
            site_name=site_name.strip(),
            product_url=product_url.strip(),
            product_title=product_title.strip(),
            product_specs=product_specs.strip(),
            product_price_eur=float(product_price_eur),
            shipping_estimate_eur=float(shipping_estimate_eur),
            delivery_address=delivery_address.strip() if requires_forwarder else "",
            momo_provider=momo_provider.strip() or None,
        )

        st.success(f"Commande créée ✅ Numéro : **{order_code}**")
        st.info(
            "Votre commande a bien été enregistrée. "
            "Vous pouvez maintenant vérifier le résultat dans « Mes commandes » puis dans le Dashboard Client."
        )

        st.success(
            f"Montant retenu : {format_xaf(final_total_xaf)} XAF ({format_eur(final_total_eur)} EUR)"
        )

        whatsapp_message = build_whatsapp_order_message(
            order_code=order_code,
            product_title=product_title.strip(),
            merchant_total_amount=merchant_total_amount,
            merchant_currency=merchant_currency,
            product_url=product_url.strip(),
        )
        whatsapp_url = build_whatsapp_share_url(whatsapp_message)

        st.markdown("### 📲 Partager votre commande")
        st.link_button(
            "Partager AfriPay sur WhatsApp",
            whatsapp_url,
            use_container_width=True,
        )

        with st.expander("Voir le message WhatsApp"):
            st.code(whatsapp_message)

        clear_captcha_error("order")
        refresh_captcha("order")


def page_mes_commandes() -> None:
    st.title("Mes commandes")
    consume_flash_message()

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
            st.write(f"**Produit / Service :** {get_product_label(row)}")
            st.write(f"**Marchand / Organisme :** {safe_get(row, 'site_name', '—')}")
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
            if not admin_is_configured():
                st.error("Admin non configuré.")
                return

            if verify_admin_password(password):
                st.session_state["admin_logged_in"] = True
                st.success("Admin connecté ✅")
                st.switch_page("pages/admin_dashboard.py")
            else:
                st.error("Mot de passe incorrect.")

        st.caption("Le mot de passe admin est chargé depuis ADMIN_PASSWORD sur Render.")
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


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    init_db()
    ensure_defaults()
    init_session()
    init_navigation_state()
    restore_session_from_query_params()
    apply_pending_menu_redirect()

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