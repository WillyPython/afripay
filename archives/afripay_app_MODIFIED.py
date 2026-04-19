import os
import secrets
import urllib.parse

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image
import streamlit as st

from core.session import init_session_state
from data.database import get_cursor
from services.order_service import _round_xaf, get_order_by_code, create_order_for_user
from services.user_service import get_user_by_id


# =========================================================
# CONFIG / CONSTANTES APP
# =========================================================
APP_BASE_COUNTRY = "CM"
DEFAULT_LANGUAGE = "fr"

PLAN_FREE = "FREE"
PLAN_PREMIUM = "PREMIUM"

FREE_MAX_ORDERS = 2
FREE_MAX_ORDER_XAF = 50000

SUPPORTED_COUNTRIES = [
    "CM",  # Cameroun
    "CI",  # Côte d’Ivoire
    "CD",  # RDC
    "GA",  # Gabon
    "NG",  # Nigeria
    "KE",  # Kenya
    "MZ",  # Mozambique
]


# =========================================================
# HELPERS GÉNÉRAUX
# =========================================================
def clean_text(value) -> str:
    """Retourne une chaîne nettoyée."""
    if value is None:
        return ""
    return str(value).strip()


def normalize_country_code(value: str, fallback: str = APP_BASE_COUNTRY) -> str:
    """Normalise un code pays sur 2 lettres."""
    value = clean_text(value).upper()
    if not value:
        return fallback
    return value[:2]


def normalize_phone(phone: str) -> str:
    """Nettoie un numéro pour stockage/usage logique."""
    if not phone:
        return ""

    phone = str(phone).strip()
    for char in [" ", "-", ".", "(", ")", "/"]:
        phone = phone.replace(char, "")

    return phone


def sanitize_whatsapp_phone(phone: str) -> str:
    """
    Prépare un numéro pour wa.me
    - conserve les chiffres
    - retire le '+' éventuel
    """
    raw = normalize_phone(phone)
    if raw.startswith("+"):
        raw = raw[1:]

    return "".join(ch for ch in raw if ch.isdigit())


# =========================================================
# SETTINGS DB
# =========================================================
def get_setting(key: str, default: str = "") -> str:
    """
    Lit un paramètre applicatif depuis la DB.
    Table attendue : settings(key TEXT PRIMARY KEY, value TEXT, ...)
    """
    key = clean_text(key)
    if not key:
        return default

    try:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT value
                FROM settings
                WHERE key = %s
                LIMIT 1
                """,
                (key,),
            )
            row = cur.fetchone()
            if not row:
                return default

            if isinstance(row, dict):
                return clean_text(row.get("value", default))

            return clean_text(row[0] if row[0] is not None else default)

    except Exception:
        return default


def get_country_whatsapp_number(country_code: str) -> str:
    """
    Retourne le numéro WhatsApp opérationnel selon le pays,
    sans aucun numéro en dur dans le code.

    Ordre de recherche :
    1. whatsapp_number_<CC>
    2. WHATSAPP_<CC>
    3. whatsapp_default
    4. WHATSAPP_DEFAULT
    """
    cc = normalize_country_code(country_code)

    candidates = [
        f"whatsapp_number_{cc.lower()}",
        f"WHATSAPP_{cc}",
        "whatsapp_default",
        "WHATSAPP_DEFAULT",
    ]

    for key in candidates:
        value = sanitize_whatsapp_phone(get_setting(key, ""))
        if value:
            return value

    return ""


def get_support_whatsapp_number() -> str:
    """
    Numéro support / fallback global.
    Toujours lu depuis la DB.
    """
    candidates = [
        "support_whatsapp_number",
        "SUPPORT_WHATSAPP_NUMBER",
        "whatsapp_default",
        "WHATSAPP_DEFAULT",
    ]

    for key in candidates:
        value = sanitize_whatsapp_phone(get_setting(key, ""))
        if value:
            return value

    return ""


def build_whatsapp_url(phone: str, message: str) -> str:
    """Construit une URL wa.me propre."""
    phone = sanitize_whatsapp_phone(phone)
    message = clean_text(message)

    if not phone:
        return ""

    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded_message}"


# =========================================================
# PROFIL / PLAN UTILISATEUR
# =========================================================
def get_user_country_code(user: dict | None) -> str:
    """
    Détermine le pays utilisateur.
    Priorité :
    - user.country_code
    - setting par défaut
    - APP_BASE_COUNTRY
    """
    if user and isinstance(user, dict):
        country = user.get("country_code") or user.get("country")
        if country:
            return normalize_country_code(country)

    default_country = get_setting("default_country_code", APP_BASE_COUNTRY)
    return normalize_country_code(default_country, APP_BASE_COUNTRY)


def get_user_plan(user: dict | None) -> str:
    """Retourne FREE par défaut si aucun plan n'est défini."""
    if not user or not isinstance(user, dict):
        return PLAN_FREE

    plan = clean_text(user.get("plan", PLAN_FREE)).upper()
    if plan not in {PLAN_FREE, PLAN_PREMIUM}:
        return PLAN_FREE

    return plan


def get_free_orders_used(user: dict | None) -> int:
    """Nombre de commandes gratuites déjà consommées."""
    if not user or not isinstance(user, dict):
        return 0

    value = user.get("free_orders_used", 0)
    try:
        return max(0, int(value or 0))
    except Exception:
        return 0


def get_free_orders_remaining(user: dict | None) -> int:
    """Nombre de commandes gratuites restantes."""
    if get_user_plan(user) == PLAN_PREMIUM:
        return FREE_MAX_ORDERS

    used = get_free_orders_used(user)
    return max(0, FREE_MAX_ORDERS - used)


def is_premium_user(user: dict | None) -> bool:
    return get_user_plan(user) == PLAN_PREMIUM


def can_user_create_order(user: dict | None, amount_xaf: int | float) -> tuple[bool, str]:
    """
    Vérifie les règles FREE / PREMIUM.
    Retourne (autorisé, raison).
    """
    if is_premium_user(user):
        return True, ""

    remaining = get_free_orders_remaining(user)
    if remaining <= 0:
        return False, "FREE_ORDER_LIMIT_REACHED"

    try:
        amount_xaf = int(round(float(amount_xaf or 0)))
    except Exception:
        amount_xaf = 0

    if amount_xaf > FREE_MAX_ORDER_XAF:
        return False, "FREE_ORDER_AMOUNT_LIMIT_REACHED"

    return True, ""


# =========================================================
# SESSION HELPERS
# =========================================================
def ensure_app_session() -> None:
    """
    Initialise la session Streamlit avec les clés minimales.
    Complète core/session.py sans le contredire.
    """
    init_session_state()

    defaults = {
        "language": DEFAULT_LANGUAGE,
        "selected_country": APP_BASE_COUNTRY,
        "premium_page_open": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_current_user() -> dict | None:
    """
    Recharge l'utilisateur courant depuis la DB à partir de user_id.
    """
    user_id = st.session_state.get("user_id")
    if not user_id:
        return None

    try:
        return get_user_by_id(user_id)
    except Exception:
        return None
# =========================================================
# PAGE CONFIG / ASSETS
# =========================================================
st.set_page_config(
    page_title="AfriPay Afrika",
    page_icon="🌍",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
HERO_BANNER_FR_PATH = ASSETS_DIR / "hero_banner_fr.png"
HERO_BANNER_EN_PATH = ASSETS_DIR / "hero_banner_en.png"


def load_image_safe(path: Path):
    """
    Charge une image localement de manière robuste.
    Retourne None si introuvable ou illisible.
    """
    try:
        if path.exists():
            return Image.open(path)
    except Exception:
        return None
    return None


def get_hero_banner_path(language: str) -> Path:
    """Retourne la bannière selon la langue."""
    return HERO_BANNER_EN_PATH if clean_text(language).lower() == "en" else HERO_BANNER_FR_PATH


# =========================================================
# TRADUCTIONS MINIMALES STABLES
# =========================================================
TRANSLATIONS = {
    "fr": {
        "premium_title": "Premium",
        "premium_subtitle": "Passez à Premium pour continuer sans blocage FREE.",
        "premium_open_button": "⭐ Découvrir Premium",
        "premium_open_small": "Passer en Premium",
        "free_box_title": "🎁 OFFRE GRATUITE",
        "free_box_remaining": "Il vous reste {count} commande(s) gratuite(s).",
        "free_box_exhausted": "🚫 Offre gratuite terminée",
        "free_box_limit_amount": "Montant maximum par commande FREE : {amount} XAF",
        "premium_box_title": "⭐ OFFRE PREMIUM",
        "premium_box_active": "Votre compte Premium est actif.",
        "premium_box_benefit": "Commandes sans blocage FREE.",
        "sidebar_country": "Pays",
        "sidebar_language": "Langue",
        "language_fr": "Français",
        "language_en": "English",
    },
    "en": {
        "premium_title": "Premium",
        "premium_subtitle": "Upgrade to Premium to continue without FREE limits.",
        "premium_open_button": "⭐ Discover Premium",
        "premium_open_small": "Upgrade to Premium",
        "free_box_title": "🎁 FREE OFFER",
        "free_box_remaining": "You have {count} free order(s) left.",
        "free_box_exhausted": "🚫 Free offer exhausted",
        "free_box_limit_amount": "Maximum amount per FREE order: {amount} XAF",
        "premium_box_title": "⭐ PREMIUM PLAN",
        "premium_box_active": "Your Premium account is active.",
        "premium_box_benefit": "Orders without FREE restrictions.",
        "sidebar_country": "Country",
        "sidebar_language": "Language",
        "language_fr": "Français",
        "language_en": "English",
    },
}


def get_language() -> str:
    lang = clean_text(st.session_state.get("language", DEFAULT_LANGUAGE)).lower()
    if lang not in {"fr", "en"}:
        return DEFAULT_LANGUAGE
    return lang


def t(key: str, **kwargs) -> str:
    """
    Traduction simple et stable.
    """
    lang = get_language()
    text = TRANSLATIONS.get(lang, {}).get(key)

    if text is None:
        text = TRANSLATIONS["fr"].get(key, key)

    try:
        return text.format(**kwargs)
    except Exception:
        return text


# =========================================================
# INITIALISATION APP
# =========================================================
ensure_app_session()


def get_selected_country() -> str:
    """Pays actuellement sélectionné dans la session."""
    current = st.session_state.get("selected_country", APP_BASE_COUNTRY)
    return normalize_country_code(current, APP_BASE_COUNTRY)


def format_xaf(value: int | float) -> str:
    """Affichage simple XAF."""
    try:
        value = int(round(float(value or 0)))
    except Exception:
        value = 0

    return f"{value:,}".replace(",", " ")


# =========================================================
# SIDEBAR CONTROL
# =========================================================
def render_sidebar_language_country() -> None:
    """
    Contrôles de base sidebar :
    - langue
    - pays
    """
    current_lang = get_language()
    lang_label = t("sidebar_language")

    selected_lang = st.sidebar.selectbox(
        lang_label,
        options=["fr", "en"],
        index=0 if current_lang == "fr" else 1,
        format_func=lambda x: t("language_fr") if x == "fr" else t("language_en"),
        key="sidebar_language_select",
    )
    st.session_state["language"] = selected_lang

    current_country = get_selected_country()
    country_label = t("sidebar_country")
    country_index = SUPPORTED_COUNTRIES.index(current_country) if current_country in SUPPORTED_COUNTRIES else 0

    selected_country = st.sidebar.selectbox(
        country_label,
        options=SUPPORTED_COUNTRIES,
        index=country_index,
        key="sidebar_country_select",
    )
    st.session_state["selected_country"] = normalize_country_code(selected_country)


def open_premium_page() -> None:
    st.session_state["premium_page_open"] = True


def close_premium_page() -> None:
    st.session_state["premium_page_open"] = False


def render_sidebar_plan_card(user: dict | None) -> None:
    """
    Carte FREE / PREMIUM dans la sidebar.
    """
    plan = get_user_plan(user)

    if plan == PLAN_PREMIUM:
        st.sidebar.markdown(f"### {t('premium_box_title')}")
        st.sidebar.success(t("premium_box_active"))
        st.sidebar.caption(t("premium_box_benefit"))
        return

    remaining = get_free_orders_remaining(user)

    st.sidebar.markdown(f"### {t('free_box_title')}")

    if remaining > 0:
        st.sidebar.info(
            t("free_box_remaining", count=remaining)
        )
        st.sidebar.caption(
            t("free_box_limit_amount", amount=format_xaf(FREE_MAX_ORDER_XAF))
        )
    else:
        st.sidebar.warning(t("free_box_exhausted"))
        st.sidebar.caption(
            t("free_box_limit_amount", amount=format_xaf(FREE_MAX_ORDER_XAF))
        )
        if st.sidebar.button(t("premium_open_small"), key="sidebar_open_premium_button", width="stretch"):
            open_premium_page()


def render_branding_header() -> None:
    """
    Logo + bannière hero.
    """
    logo = load_image_safe(LOGO_PATH)
    if logo is not None:
        st.image(logo, width=120)

    hero = load_image_safe(get_hero_banner_path(get_language()))
    if hero is not None:
        st.image(hero, width="stretch")
# =========================================================
# PREMIUM PAGE
# =========================================================
def build_premium_whatsapp_message(user: dict | None) -> str:
    """
    Message WhatsApp pour demande d’activation Premium.
    Aucun numéro n'est codé en dur : seul le message est préparé ici.
    """
    language = get_language()

    client_name = ""
    client_phone = ""
    client_country = get_selected_country()

    if user and isinstance(user, dict):
        client_name = clean_text(user.get("full_name") or user.get("name"))
        client_phone = clean_text(user.get("phone"))
        client_country = get_user_country_code(user)

    if language == "en":
        lines = [
            "Hello AfriPay Afrika,",
            "",
            "I would like to upgrade to Premium.",
            f"Name: {client_name or '-'}",
            f"Phone: {client_phone or '-'}",
            f"Country: {client_country or '-'}",
        ]
    else:
        lines = [
            "Bonjour AfriPay Afrika,",
            "",
            "Je souhaite passer à l’offre Premium.",
            f"Nom : {client_name or '-'}",
            f"Téléphone : {client_phone or '-'}",
            f"Pays : {client_country or '-'}",
        ]

    return "\n".join(lines)


def render_premium_page(user: dict | None) -> None:
    """
    Page Premium simple, stable et pilotée par session.
    """
    language = get_language()
    country_code = get_user_country_code(user) if user else get_selected_country()

    premium_phone = get_country_whatsapp_number(country_code) or get_support_whatsapp_number()
    premium_message = build_premium_whatsapp_message(user)
    premium_url = build_whatsapp_url(premium_phone, premium_message)

    st.title(t("premium_title"))
    st.caption(t("premium_subtitle"))

    if language == "en":
        st.markdown(
            """
            ### Premium benefits
            - Continue without FREE order limit
            - Continue without FREE amount cap
            - Priority operational handling
            - Better continuity for recurring users
            """
        )
    else:
        st.markdown(
            """
            ### Avantages Premium
            - Continuer sans blocage du nombre de commandes FREE
            - Continuer sans plafond FREE par commande
            - Traitement opérationnel prioritaire
            - Meilleure continuité pour les utilisateurs réguliers
            """
        )

    st.info(
        f"{t('free_box_limit_amount', amount=format_xaf(FREE_MAX_ORDER_XAF))} • "
        f"{t('free_box_remaining', count=get_free_orders_remaining(user)) if not is_premium_user(user) else t('premium_box_active')}"
    )

    col1, col2 = st.columns(2)

    with col1:
        if premium_url:
            st.link_button(
                t("premium_open_button"),
                premium_url,
                width="stretch",
            )
        else:
            st.warning(
                "Numéro WhatsApp Premium indisponible dans les paramètres."
                if language == "fr"
                else "Premium WhatsApp number is not available in settings."
            )

    with col2:
        if st.button(
            "⬅ Retour"
            if language == "fr"
            else "⬅ Back",
            key="close_premium_page_button",
            width="stretch",
        ):
            close_premium_page()
            st.rerun()

# =========================================================
# WHATSAPP ORDER FLOW HELPERS
# =========================================================
def build_order_whatsapp_message(
    user: dict | None,
    order_data: dict | None = None,
) -> str:
    """
    Prépare le message WhatsApp pour une commande ou un panier.
    Aucun numéro n'est codé en dur.
    """
    language = get_language()

    client_name = ""
    client_phone = ""
    client_country = get_selected_country()

    if user and isinstance(user, dict):
        client_name = clean_text(user.get("full_name") or user.get("name"))
        client_phone = clean_text(user.get("phone"))
        client_country = get_user_country_code(user)

    product_url = ""
    merchant_name = ""
    delivered_total_eur = ""
    transit_agent_name = ""
    transit_agent_address = ""

    if order_data and isinstance(order_data, dict):
        product_url = clean_text(
            order_data.get("product_url")
            or order_data.get("cart_url")
            or order_data.get("merchant_url")
        )
        merchant_name = clean_text(order_data.get("merchant_name"))
        delivered_total_eur = clean_text(order_data.get("merchant_total_eur"))
        transit_agent_name = clean_text(order_data.get("transit_agent_name"))
        transit_agent_address = clean_text(order_data.get("transit_agent_address"))

    if language == "en":
        lines = [
            "Hello AfriPay Afrika,",
            "",
            "I would like to submit my order/cart for WhatsApp validation.",
            f"Name: {client_name or '-'}",
            f"Phone: {client_phone or '-'}",
            f"Country: {client_country or '-'}",
            f"Merchant: {merchant_name or '-'}",
            f"Cart / Product URL: {product_url or '-'}",
            f"Delivered total shown by merchant (EUR): {delivered_total_eur or '-'}",
            f"Transit agent: {transit_agent_name or '-'}",
            f"Transit agent address: {transit_agent_address or '-'}",
        ]
    else:
        lines = [
            "Bonjour AfriPay Afrika,",
            "",
            "Je souhaite soumettre ma commande / mon panier pour validation WhatsApp.",
            f"Nom : {client_name or '-'}",
            f"Téléphone : {client_phone or '-'}",
            f"Pays : {client_country or '-'}",
            f"Marchand : {merchant_name or '-'}",
            f"Lien panier / produit : {product_url or '-'}",
            f"Total livré affiché par le marchand (EUR) : {delivered_total_eur or '-'}",
            f"Transitaire : {transit_agent_name or '-'}",
            f"Adresse du transitaire : {transit_agent_address or '-'}",
        ]

    return "\n".join(lines)


def get_order_whatsapp_number(user: dict | None = None) -> str:
    """
    Retourne le numéro WhatsApp opérationnel pour les commandes,
    selon le pays utilisateur ou le pays sélectionné.
    """
    country_code = get_user_country_code(user) if user else get_selected_country()
    return get_country_whatsapp_number(country_code) or get_support_whatsapp_number()


def build_order_whatsapp_url(
    user: dict | None,
    order_data: dict | None = None,
) -> str:
    """
    Construit l'URL WhatsApp de validation commande/panier.
    """
    phone = get_order_whatsapp_number(user)
    message = build_order_whatsapp_message(user, order_data)
    return build_whatsapp_url(phone, message)


def build_payment_proof_whatsapp_message(
    order_code: str,
    momo_provider: str = "",
) -> str:
    """
    Message simple pour l'envoi de preuve de paiement.
    """
    language = get_language()
    order_code = clean_text(order_code)
    momo_provider = clean_text(momo_provider)

    if language == "en":
        lines = [
            "Hello AfriPay Afrika,",
            "",
            "I am sending my payment proof.",
            f"Order reference: {order_code or '-'}",
            f"Operator: {momo_provider or '-'}",
        ]
    else:
        lines = [
            "Bonjour AfriPay Afrika,",
            "",
            "J'envoie ma preuve de paiement.",
            f"Référence commande : {order_code or '-'}",
            f"Opérateur : {momo_provider or '-'}",
        ]

    return "\n".join(lines)


def build_payment_proof_whatsapp_url(
    user: dict | None,
    order_code: str,
    momo_provider: str = "",
) -> str:
    """
    URL WhatsApp pour l'envoi de preuve de paiement.
    """
    phone = get_order_whatsapp_number(user)
    message = build_payment_proof_whatsapp_message(order_code, momo_provider)
    return build_whatsapp_url(phone, message)


def get_order_code_from_query_params() -> str:
    """
    Lecture tolérante d'une éventuelle référence commande
    dans les query params.
    """
    try:
        params = st.query_params
        return clean_text(
            params.get("order_code", "")
            or params.get("code", "")
            or params.get("ref", "")
        )
    except Exception:
        return ""


def try_get_order_from_query_params():
    """
    Essaie de charger une commande depuis l'URL.
    """
    order_code = get_order_code_from_query_params()
    if not order_code:
        return None

    try:
        return get_order_by_code(order_code)
    except Exception:
        return None


def render_home_intro(user: dict | None) -> None:
    """
    Intro d'accueil enrichie avec CTA WhatsApp.
    """
    language = get_language()
    order_whatsapp_url = build_order_whatsapp_url(user)

    if language == "en":
        st.title("AfriPay Afrika")
        st.write("International ordering flow with WhatsApp cart validation.")
        st.markdown(
            """
            ### How it works
            1. Submit your cart or product link
            2. AfriPay checks the link on WhatsApp
            3. You confirm
            4. You send payment proof
            """
        )
    else:
        st.title("AfriPay Afrika")
        st.write("Flow de commande internationale avec validation du panier par WhatsApp.")
        st.markdown(
            """
            ### Comment ça marche
            1. Vous soumettez votre panier ou lien produit
            2. AfriPay vérifie le lien sur WhatsApp
            3. Vous confirmez
            4. Vous envoyez la preuve de paiement
            """
        )

    if order_whatsapp_url:
        st.link_button(
            "📲 Envoyer mon panier sur WhatsApp"
            if language == "fr"
            else "📲 Send my cart on WhatsApp",
            order_whatsapp_url,
            width="stretch",
        )
    else:
        st.warning(
            "Numéro WhatsApp indisponible dans les paramètres."
            if language == "fr"
            else "WhatsApp number is not available in settings."
        )
    st.divider()
    render_order_entry_form(user)
# =========================================================
# ORDER FORM / FREE CONTROL
# =========================================================
def get_order_form_defaults() -> dict:
    """
    Valeurs par défaut du mini formulaire commande.
    """
    return {
        "merchant_name": "",
        "product_url": "",
        "merchant_total_eur": "",
        "transit_agent_name": "",
        "transit_agent_address": "",
        "estimated_total_xaf": 0,
    }


def parse_amount_input(value) -> float:
    """
    Convertit une saisie montant de manière tolérante.
    """
    if value is None:
        return 0.0

    raw = str(value).strip().replace(" ", "")
    raw = raw.replace(",", ".")

    try:
        return max(0.0, float(raw))
    except Exception:
        return 0.0


def estimate_order_total_xaf(merchant_total_eur: float) -> int:
    """
    Estimation simple XAF pour contrôle FREE.
    Base actuelle : conversion approximative puis arrondi métier.
    """
    eur_to_xaf = 655.957
    estimated = merchant_total_eur * eur_to_xaf

    try:
        return int(_round_xaf(estimated))
    except Exception:
        return int(round(estimated))


def render_order_entry_form(user: dict | None) -> None:
    """
    Formulaire minimal stable pour lancer le flow commande WhatsApp.
    """
    language = get_language()
    init_order_action_state()

    if language == "en":
        st.subheader("Order / Cart submission")
    else:
        st.subheader("Soumission commande / panier")

    defaults = get_order_form_defaults()

    merchant_name = st.text_input(
        "Nom du marchand" if language == "fr" else "Merchant name",
        value=defaults["merchant_name"],
        key="order_form_merchant_name",
    )

    product_url = st.text_input(
        "Lien produit / panier" if language == "fr" else "Product / cart URL",
        value=defaults["product_url"],
        key="order_form_product_url",
    )

    merchant_total_eur_input = st.text_input(
        "Total livré affiché par le marchand (EUR)"
        if language == "fr"
        else "Delivered total shown by merchant (EUR)",
        value=defaults["merchant_total_eur"],
        key="order_form_merchant_total_eur",
    )

    transit_agent_name = st.text_input(
        "Nom du transitaire / agent"
        if language == "fr"
        else "Transit agent name",
        value=defaults["transit_agent_name"],
        key="order_form_transit_agent_name",
    )

    transit_agent_address = st.text_area(
        "Adresse du transitaire / agent"
        if language == "fr"
        else "Transit agent address",
        value=defaults["transit_agent_address"],
        key="order_form_transit_agent_address",
        height=90,
    )

    merchant_total_eur = parse_amount_input(merchant_total_eur_input)
    estimated_total_xaf = estimate_order_total_xaf(merchant_total_eur)

    st.caption(
        (
            f"Estimation contrôle FREE : {format_xaf(estimated_total_xaf)} XAF"
            if language == "fr"
            else f"FREE control estimate: {format_xaf(estimated_total_xaf)} XAF"
        )
    )

    order_data = {
        "merchant_name": merchant_name,
        "product_url": product_url,
        "merchant_total_eur": merchant_total_eur_input,
        "transit_agent_name": transit_agent_name,
        "transit_agent_address": transit_agent_address,
        "estimated_total_xaf": estimated_total_xaf,
    }

    is_allowed, reason = can_user_create_order(user, estimated_total_xaf)
    whatsapp_url = build_order_whatsapp_url(user, order_data)
    preview_message = build_order_whatsapp_message(user, order_data)

    with st.expander(
        "Voir le message WhatsApp"
        if language == "fr"
        else "See WhatsApp message",
        expanded=False,
    ):
        st.code(preview_message)

    if is_allowed:
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "💾 Créer la commande"
                if language == "fr"
                else "💾 Create order",
                key="create_real_order_button",
                width="stretch",
            ):
                try_create_order_from_ui(user, order_data)
                st.rerun()

        with col2:
            if whatsapp_url:
                st.link_button(
                    "✅ Envoyer sur WhatsApp"
                    if language == "fr"
                    else "✅ Send on WhatsApp",
                    whatsapp_url,
                    width="stretch",
                )
            else:
                st.warning(
                    "Numéro WhatsApp indisponible dans les paramètres."
                    if language == "fr"
                    else "WhatsApp number is not available in settings."
                )
    else:
        if reason == "FREE_ORDER_LIMIT_REACHED":
            st.error(
                "Votre limite FREE de commandes est atteinte. Passez à Premium."
                if language == "fr"
                else "Your FREE order limit has been reached. Upgrade to Premium."
            )
        elif reason == "FREE_ORDER_AMOUNT_LIMIT_REACHED":
            st.error(
                f"Le montant estimé dépasse la limite FREE de {format_xaf(FREE_MAX_ORDER_XAF)} XAF."
                if language == "fr"
                else f"The estimated amount exceeds the FREE limit of {format_xaf(FREE_MAX_ORDER_XAF)} XAF."
            )
        else:
            st.error(
                "Commande temporairement bloquée."
                if language == "fr"
                else "Order temporarily blocked."
            )

        if st.button(
            t("premium_open_button"),
            key="order_form_open_premium_button",
            width="stretch",
        ):
            open_premium_page()
            st.rerun()

    render_created_order_result(user)

# =========================================================
# ORDER SERVICE BRIDGE
# =========================================================
def get_user_contact_snapshot(user: dict | None) -> dict:
    """
    Prépare un snapshot client cohérent pour la création réelle de commande.
    """
    if not user or not isinstance(user, dict):
        return {
            "client_name": "",
            "client_phone": "",
            "client_email": "",
            "country_code": get_selected_country(),
        }

    return {
        "client_name": clean_text(
            user.get("name")
            or user.get("full_name")
            or user.get("client_name")
        ),
        "client_phone": clean_text(user.get("phone")),
        "client_email": clean_text(user.get("email")),
        "country_code": get_user_country_code(user),
    }


def build_order_service_payload(user: dict | None, order_data: dict) -> dict:
    """
    Transforme les données UI en payload compatible avec create_order_for_user(...).
    """
    if not user or not user.get("id"):
        raise ValueError("Utilisateur non connecté.")

    contact = get_user_contact_snapshot(user)

    merchant_name = clean_text(order_data.get("merchant_name"))
    product_url = clean_text(order_data.get("product_url"))
    merchant_total_eur = parse_amount_input(order_data.get("merchant_total_eur"))
    transit_agent_name = clean_text(order_data.get("transit_agent_name"))
    transit_agent_address = clean_text(order_data.get("transit_agent_address"))

    delivery_address = transit_agent_address
    if transit_agent_name and transit_agent_address:
        delivery_address = f"{transit_agent_name} — {transit_agent_address}"
    elif transit_agent_name:
        delivery_address = transit_agent_name
    elif transit_agent_address:
        delivery_address = transit_agent_address

    estimated_total_xaf = estimate_order_total_xaf(merchant_total_eur)

    return {
        "user_id": int(user["id"]),
        "client_name": contact["client_name"],
        "client_phone": contact["client_phone"],
        "client_email": contact["client_email"],
        "site_name": merchant_name,
        "product_url": product_url,
        "product_title": merchant_name or "Commande client",
        "product_specs": f"Transitaire: {transit_agent_name}" if transit_agent_name else "",
        "product_price_eur": merchant_total_eur,
        "shipping_estimate_eur": 0.0,
        "delivery_address": delivery_address,
        "momo_provider": None,
        "merchant_total_amount": merchant_total_eur,
        "merchant_currency": "EUR",
        "country_code": contact["country_code"],
        "seller_fee_xaf": 0,
        "afripay_fee_xaf": 0,
        "total_xaf": estimated_total_xaf,
        "total_to_pay_eur": merchant_total_eur,
    }


def create_real_order_from_form(user: dict | None, order_data: dict) -> str:
    """
    Crée réellement une commande en base via services/order_service.py.
    Retourne le order_code créé.
    """
    payload = build_order_service_payload(user, order_data)
    return create_order_for_user(**payload)

# =========================================================
# ORDER CREATION ACTIONS
# =========================================================
def init_order_action_state() -> None:
    """
    Initialise les clés session liées à la création réelle de commande.
    """
    defaults = {
        "last_created_order_code": "",
        "last_order_error": "",
        "last_order_success": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_order_action_messages() -> None:
    st.session_state["last_order_error"] = ""
    st.session_state["last_order_success"] = ""


def render_created_order_result(user: dict | None) -> None:
    """
    Affiche le résultat de la dernière création réelle de commande.
    Version enrichie avec lecture commande réelle.
    """
    language = get_language()
    order_code = clean_text(st.session_state.get("last_created_order_code", ""))
    success_message = clean_text(st.session_state.get("last_order_success", ""))
    error_message = clean_text(st.session_state.get("last_order_error", ""))

    if success_message:
        st.success(success_message)

    if error_message:
        st.error(error_message)

    if order_code:
        set_order_code_in_query_params(order_code)

    render_order_lookup_from_url_notice()
    render_order_confirmation_panel(user)

    if not order_code and not get_order_code_from_query_params():
        return

    if st.button(
        "🧹 Effacer le résultat"
        if language == "fr"
        else "🧹 Clear result",
        key="clear_last_order_result_button",
        width="stretch",
    ):
        st.session_state["last_created_order_code"] = ""
        st.session_state["last_order_error"] = ""
        st.session_state["last_order_success"] = ""
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()


def try_create_order_from_ui(user: dict | None, order_data: dict) -> None:
    """
    Tente la création réelle de commande depuis l'UI.
    """
    language = get_language()
    reset_order_action_messages()

    try:
        order_code = create_real_order_from_form(user, order_data)
        st.session_state["last_created_order_code"] = clean_text(order_code)
        set_order_code_in_query_params(order_code)
        st.session_state["last_order_success"] = (
            f"Commande créée avec succès : {order_code}"
            if language == "fr"
            else f"Order created successfully: {order_code}"
        )
        st.session_state["last_order_error"] = ""
    except Exception as exc:
        st.session_state["last_created_order_code"] = ""
        st.session_state["last_order_success"] = ""
        st.session_state["last_order_error"] = str(exc) or (
            "La création de commande a échoué."
            if language == "fr"
            else "Order creation failed."
        )

# =========================================================
# ORDER CONFIRMATION / URL / STATUS VIEW
# =========================================================
def set_order_code_in_query_params(order_code: str) -> None:
    """
    Enregistre la référence commande dans l'URL.
    """
    order_code = clean_text(order_code)
    if not order_code:
        return

    try:
        st.query_params["order_code"] = order_code
    except Exception:
        pass


def get_active_order_code() -> str:
    """
    Retourne la référence commande active :
    1. dernière commande créée en session
    2. query params URL
    """
    session_code = clean_text(st.session_state.get("last_created_order_code", ""))
    if session_code:
        return session_code

    return get_order_code_from_query_params()


def get_active_order() -> dict | None:
    """
    Charge la commande active si trouvée.
    """
    order_code = get_active_order_code()
    if not order_code:
        return None

    try:
        return get_order_by_code(order_code)
    except Exception:
        return None


def get_order_field(order: dict | None, *keys, default=""):
    """
    Lecture tolérante d'un champ commande.
    """
    if not order or not isinstance(order, dict):
        return default

    for key in keys:
        if key in order and order.get(key) not in [None, ""]:
            return order.get(key)

    return default


def render_order_status_summary(order: dict | None) -> None:
    """
    Affichage simple des statuts de la commande.
    """
    if not order:
        return

    language = get_language()

    order_status = clean_text(get_order_field(order, "status", "order_status", default="CREEE"))
    payment_status = clean_text(get_order_field(order, "payment_status", default="PENDING"))
    merchant_status = clean_text(get_order_field(order, "merchant_status", default=""))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Statut commande" if language == "fr" else "Order status",
            order_status or ("Créée" if language == "fr" else "Created"),
        )

    with col2:
        st.metric(
            "Statut paiement" if language == "fr" else "Payment status",
            payment_status or "PENDING",
        )

    with col3:
        st.metric(
            "Suivi marchand" if language == "fr" else "Merchant tracking",
            merchant_status or ("En attente" if language == "fr" else "Pending"),
        )


def render_order_confirmation_panel(user: dict | None) -> None:
    """
    Affiche la confirmation enrichie de la commande active.
    """
    language = get_language()
    order = get_active_order()

    if not order:
        return

    order_code = clean_text(get_order_field(order, "order_code", default=""))
    merchant_name = clean_text(get_order_field(order, "site_name", "merchant_name", default=""))
    product_url = clean_text(get_order_field(order, "product_url", default=""))
    total_xaf = get_order_field(order, "total_xaf", default=0)
    payment_status = clean_text(get_order_field(order, "payment_status", default="PENDING"))

    set_order_code_in_query_params(order_code)

    st.divider()

    st.subheader(
        "Confirmation de commande" if language == "fr" else "Order confirmation"
    )


    st.info(
        f"Référence commande : {order_code}"
        if language == "fr"
        else f"Order reference: {order_code}"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.write(
            f"**Marchand :** {merchant_name or '-'}"
            if language == "fr"
            else f"**Merchant:** {merchant_name or '-'}"
        )
        st.write(
            f"**Lien produit / panier :** {product_url or '-'}"
            if language == "fr"
            else f"**Product / cart URL:** {product_url or '-'}"
        )

    with col2:
        st.write(
            f"**Montant total estimé :** {format_xaf(total_xaf)} XAF"
            if language == "fr"
            else f"**Estimated total amount:** {format_xaf(total_xaf)} XAF"
        )
        st.write(
            f"**Paiement :** {payment_status or 'PENDING'}"
            if language == "fr"
            else f"**Payment:** {payment_status or 'PENDING'}"
        )

    render_order_status_summary(order)

    proof_url = build_payment_proof_whatsapp_url(user, order_code)

    if payment_status.upper() not in {"CONFIRMED"}:
        st.markdown(
            "### Preuve de paiement"
            if language == "fr"
            else "### Payment proof"
        )

        st.write(
            "Après paiement, envoyez votre preuve de paiement par WhatsApp avec la référence de commande."
            if language == "fr"
            else "After payment, send your payment proof by WhatsApp with the order reference."
        )

        if proof_url:
            st.link_button(
                "📩 Envoyer la preuve de paiement"
                if language == "fr"
                else "📩 Send payment proof",
                proof_url,
                width="stretch",
            )
        else:
            st.warning(
                "Numéro WhatsApp indisponible dans les paramètres."
                if language == "fr"
                else "WhatsApp number is not available in settings."
            )


def render_order_lookup_from_url_notice() -> None:
    """
    Petit indicateur si une commande vient de l'URL.
    """
    language = get_language()
    query_code = get_order_code_from_query_params()
    session_code = clean_text(st.session_state.get("last_created_order_code", ""))

    if query_code and query_code != session_code:
        st.caption(
            f"Commande chargée depuis l’URL : {query_code}"
            if language == "fr"
            else f"Order loaded from URL: {query_code}"
        )

# =========================================================
# APP ROUTING
# =========================================================
def render_app_shell() -> None:
    """
    Structure principale minimale de l'application.
    Cette base sera enrichie dans les blocs suivants.
    """
    user = get_current_user()

    with st.sidebar:
        render_sidebar_language_country()
        render_sidebar_plan_card(user)

    render_branding_header()

    if st.session_state.get("premium_page_open", False):
        render_premium_page(user)
        return

    render_home_intro(user)




if __name__ == "__main__":
    render_app_shell()
