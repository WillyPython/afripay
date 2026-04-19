
import os
import secrets
import urllib.parse

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PIL import Image
import streamlit as st

from core.session import init_session, logout_user, logout_admin
from data.database import init_db, get_cursor
from services.order_service import (
    _round_xaf,
    confirm_payment,
    create_order_for_user,
    deliver_order,
    get_order_by_code,
    start_order_processing,
)
from services.settings_service import ensure_defaults
from services.user_service import get_user_by_id, upsert_user
from ui.branding import render_sidebar_branding

try:
    from services.admin_service import get_setting as admin_get_setting
except Exception:  # pragma: no cover
    admin_get_setting = None

try:
    from services.admin_service import verify_admin_password as service_verify_admin_password
except Exception:  # pragma: no cover
    service_verify_admin_password = None

try:
    from services.order_service import cancel_order
except Exception:  # pragma: no cover
    cancel_order = None

try:
    from services.order_service import mark_payment_proof_sent
except Exception:  # pragma: no cover
    mark_payment_proof_sent = None

try:
    from services.order_service import mark_payment_proof_received
except Exception:  # pragma: no cover
    mark_payment_proof_received = None


# =========================================================
# CONFIG
# =========================================================
APP_NAME = "AfriPay Afrika"
APP_TAGLINE = "Commandez vos achats internationaux avec un flow simple et sécurisé."
APP_BASE_COUNTRY = "CM"
DEFAULT_LANGUAGE = "fr"

OTP_COOLDOWN_SECONDS = 60
OTP_MAX_REQUESTS = 3
OTP_WINDOW_MINUTES = 5

PLAN_FREE = "FREE"
PLAN_PREMIUM = "PREMIUM"
PLAN_PREMIUM_PLUS = "PREMIUM_PLUS"

FREE_MAX_ORDERS = 2
FREE_MAX_ORDER_XAF = 50_000
SUPPORTED_COUNTRIES = ["CM", "CI", "CD", "GA", "NG", "KE", "MZ"]
PLAN_DURATION_OPTIONS = [6, 12]

ADMIN_VIEW_DASHBOARD = "dashboard"
ADMIN_VIEW_PAYMENT_SUMMARY = "payment_summary"
ADMIN_VIEW_PAYMENT_PROOFS = "payment_proofs"
ADMIN_VIEW_IN_PROGRESS = "in_progress"
ADMIN_VIEW_CANCELLED = "cancelled"
ADMIN_VIEW_HISTORY = "history"
ADMIN_VIEW_REFUNDS = "refunds"

REFUND_STATUS_NONE = "NONE"
REFUND_STATUS_PENDING = "PENDING"
REFUND_STATUS_PROCESSING = "PROCESSING"
REFUND_STATUS_COMPLETED = "COMPLETED"
REFUND_STATUS_PROOF_SENT = "PROOF_SENT"
REFUND_STATUS_CONFIRMED = "CONFIRMED"

UI_WIDTH_STRETCH = "stretch"

TRANSLATIONS = {
    "fr": {
        "page_title": "AfriPay Afrika",
        "hero_title": "Achetez à l'international, simplement.",
        "hero_text": "AfriPay Afrika vous accompagne dans votre commande internationale, avec validation avant paiement et suivi clair.",
        "sidebar_lang": "Langue",
        "sidebar_country": "Pays",
        "sidebar_account": "Compte",
        "sidebar_plan": "Plan actif",
        "sidebar_free_left": "Commandes FREE restantes",
        "sidebar_upgrade": "Voir les offres",
        "sidebar_upgrade_unavailable": "Upgrade temporairement indisponible",
        "sidebar_connected": "Connecté",
        "sidebar_not_connected": "Non connecté",
        "sidebar_logout": "Déconnexion",
        "account_title": "Connexion rapide",
        "account_intro": "Entrez votre numéro pour charger ou créer votre profil utilisateur.",
        "full_name": "Nom complet",
        "phone": "Téléphone",
        "email": "Email",
        "continue_btn": "Continuer",
        "otp_none": "Aucun OTP généré pour le moment.",
        "otp_other_phone": "Attention : ce code OTP semble lié à un autre numéro.",
        "otp_test_mode": "Mode test OTP",
        "otp_test_warning": "Le code affiché ci-dessous est un code de test visible localement pour validation.",
        "otp_linked_phone": "Numéro lié à l'OTP",
        "otp_test_code": "Code OTP de test",
        "otp_keep_info": "Utilisez ce code OTP pour finaliser la connexion.",
        "captcha_title": "Vérification humaine",
        "captcha_required": "Captcha obligatoire : vous devez entrer le résultat exact pour continuer.",
        "captcha_info": "Protection anti-bot AfriPay : veuillez résoudre l'opération suivante avant de continuer : **{a} + {b} = ?**",
        "captcha_input": "Résultat de l'opération *",
        "captcha_placeholder": "Captcha obligatoire : entrez le résultat exact",
        "captcha_help": "Ce captcha est obligatoire. Sans le bon résultat, vous ne pouvez pas continuer.",
        "captcha_ok": "Captcha correct ✅",
        "captcha_bad": "Captcha incorrect ❌",
        "captcha_refresh": "Nouveau",
        "captcha_caption": "Entrez le résultat exact de l'opération affichée.",
        "plan_title": "Plans AfriPay",
        "plan_free": "FREE",
        "plan_premium": "PREMIUM",
        "plan_premium_plus": "PREMIUM_PLUS",
        "plan_free_desc": "2 commandes maximum · 50 000 XAF maximum par commande · 0% frais AfriPay",
        "plan_premium_desc": "20% frais AfriPay par commande",
        "plan_premium_plus_desc": "0% frais AfriPay pendant la durée active · activation après paiement confirmé",
        "plan_pending_note": "Premium Plus non encore activé : comportement PREMIUM appliqué tant que le paiement n'est pas confirmé.",
        "upgrade_title": "Passer à PREMIUM ou PREMIUM_PLUS",
        "upgrade_intro": "Choisissez votre formule, envoyez votre demande sur WhatsApp, puis attendez la validation admin.",
        "premium_btn": "Passer en PREMIUM",
        "premium_plus_btn": "Choisir PREMIUM_PLUS",
        "duration_label": "Durée active",
        "duration_help": "Choisissez 6 mois ou 12 mois. L'activation ne commence qu'après confirmation du paiement.",
        "send_whatsapp": "Ouvrir WhatsApp",
        "payment_flow_title": "Flow AfriPay",
        "payment_flow_text": "Panier → WhatsApp AfriPay → validation AfriPay → confirmation client → preuve de paiement → validation admin → activation/statut",
        "order_title": "Créer une commande",
        "order_type": "Type de commande",
        "order_type_product": "Produit",
        "order_type_service": "Service",
        "site_name": "Nom du site / marchand",
        "product_url": "Lien produit / lien panier",
        "product_title": "Titre du produit / service",
        "product_specs": "Détails / spécifications",
        "merchant_total_eur": "Total livré marchand (EUR)",
        "forwarder_name": "Nom du transitaire / agent / agence",
        "delivery_address": "Adresse transitaire / livraison",
        "payment_method": "Mode de paiement",
        "create_order": "Créer la commande",
        "free_block_limit": "Votre quota FREE est épuisé. Passez à une offre payante pour continuer.",
        "free_block_amount": "Le plan FREE accepte au maximum 50 000 XAF par commande.",
        "free_block_limit_no_whatsapp": "Votre quota FREE est épuisé. L'upgrade n'est pas encore disponible car WhatsApp n'est pas configuré côté plateforme.",
        "free_upgrade_ready": "Votre quota FREE est épuisé. Vous pouvez maintenant passer à une offre payante.",
        "upgrade_unavailable_title": "Upgrade temporairement indisponible",
        "upgrade_unavailable_text": "Le parcours d'upgrade n'est pas encore disponible, car aucun numéro WhatsApp support n'est configuré dans les settings.",
        "order_blocked_upgrade_unavailable": "Création de commande bloquée : quota FREE épuisé et upgrade indisponible tant que WhatsApp n'est pas configuré côté plateforme.",
        "order_created": "Commande créée avec succès.",
        "order_summary": "Résumé commande",
        "order_code": "Code commande",
        "order_total_xaf": "Total à payer",
        "order_fee_xaf": "Frais AfriPay",
        "send_cart_whatsapp": "Envoyer le lien panier à AfriPay",
        "send_payment_proof": "Envoyer la preuve de paiement",
        "proof_intro": "Une fois la validation AfriPay reçue, envoyez votre preuve de paiement à l'équipe.",
        "proof_unavailable_text": "WhatsApp n'est pas encore configuré côté plateforme. La commande est créée, mais les actions WhatsApp restent indisponibles pour le moment.",
        "recent_orders": "Mes commandes récentes",
        "status": "Statut",
        "empty_orders": "Aucune commande pour le moment.",
        "login_success": "Compte chargé avec succès.",
        "login_error_phone": "Le numéro de téléphone est obligatoire.",
        "upgrade_cta_free": "Votre offre FREE est terminée. Passez à PREMIUM ou PREMIUM_PLUS.",
        "configured_missing_whatsapp": "Aucun numéro WhatsApp configuré dans les settings.",
        "subscription_active_until": "Actif jusqu'au",
        "subscription_status": "Statut abonnement",
        "admin_login_title": "Espace administrateur",
        "admin_password": "Mot de passe administrateur",
        "admin_login_button": "Se connecter (Admin)",
        "admin_logout": "🚪 Déconnexion Admin",
    },
    "en": {
        "page_title": "AfriPay Afrika",
        "hero_title": "International ordering, made simple.",
        "hero_text": "AfriPay Afrika helps you place international orders with validation before payment and a clear follow-up flow.",
        "sidebar_lang": "Language",
        "sidebar_country": "Country",
        "sidebar_account": "Account",
        "sidebar_plan": "Active plan",
        "sidebar_free_left": "FREE orders left",
        "sidebar_upgrade": "View plans",
        "sidebar_upgrade_unavailable": "Upgrade temporarily unavailable",
        "sidebar_connected": "Connected",
        "sidebar_not_connected": "Not connected",
        "sidebar_logout": "Log out",
        "account_title": "Quick sign in",
        "account_intro": "Enter your phone number to load or create your user profile.",
        "full_name": "Full name",
        "phone": "Phone",
        "email": "Email",
        "continue_btn": "Continue",
        "otp_none": "No OTP generated yet.",
        "otp_other_phone": "Warning: this OTP code seems linked to another phone number.",
        "otp_test_mode": "OTP test mode",
        "otp_test_warning": "The code shown below is a local test OTP for validation.",
        "otp_linked_phone": "Phone linked to OTP",
        "otp_test_code": "Test OTP code",
        "otp_keep_info": "Use this OTP code to complete the login.",
        "captcha_title": "Human verification",
        "captcha_required": "Captcha required: you must enter the exact result to continue.",
        "captcha_info": "AfriPay anti-bot protection: please solve the following operation before continuing: **{a} + {b} = ?**",
        "captcha_input": "Operation result *",
        "captcha_placeholder": "Captcha required: enter the exact result",
        "captcha_help": "This captcha is required. Without the correct result, you cannot continue.",
        "captcha_ok": "Captcha correct ✅",
        "captcha_bad": "Captcha incorrect ❌",
        "captcha_refresh": "Refresh",
        "captcha_caption": "Enter the exact result of the displayed operation.",
        "plan_title": "AfriPay plans",
        "plan_free": "FREE",
        "plan_premium": "PREMIUM",
        "plan_premium_plus": "PREMIUM_PLUS",
        "plan_free_desc": "Up to 2 orders · up to 50,000 XAF per order · 0% AfriPay fee",
        "plan_premium_desc": "20% AfriPay fee per order",
        "plan_premium_plus_desc": "0% AfriPay fee during the active period · activation only after confirmed payment",
        "plan_pending_note": "Premium Plus is not active yet: PREMIUM behavior still applies until payment is confirmed.",
        "upgrade_title": "Upgrade to PREMIUM or PREMIUM_PLUS",
        "upgrade_intro": "Choose your plan, send your request on WhatsApp, then wait for admin validation.",
        "premium_btn": "Upgrade to PREMIUM",
        "premium_plus_btn": "Choose PREMIUM_PLUS",
        "duration_label": "Active period",
        "duration_help": "Choose 6 months or 12 months. Activation starts only after payment confirmation.",
        "send_whatsapp": "Open WhatsApp",
        "payment_flow_title": "AfriPay flow",
        "payment_flow_text": "Cart link → AfriPay WhatsApp → AfriPay validation → client confirmation → payment proof → admin validation → activation/status",
        "order_title": "Create an order",
        "order_type": "Order type",
        "order_type_product": "Product",
        "order_type_service": "Service",
        "site_name": "Merchant / site name",
        "product_url": "Product link / cart link",
        "product_title": "Product / service title",
        "product_specs": "Details / specs",
        "merchant_total_eur": "Merchant delivered total (EUR)",
        "forwarder_name": "Freight forwarder / agent / agency",
        "delivery_address": "Freight forwarder / delivery address",
        "payment_method": "Payment method",
        "create_order": "Create order",
        "free_block_limit": "Your FREE quota is exhausted. Upgrade to continue.",
        "free_block_amount": "FREE plan accepts at most 50,000 XAF per order.",
        "free_block_limit_no_whatsapp": "Your FREE quota is exhausted. Upgrade is not available yet because platform WhatsApp is not configured.",
        "free_upgrade_ready": "Your FREE quota is exhausted. You can now move to a paid plan.",
        "upgrade_unavailable_title": "Upgrade temporarily unavailable",
        "upgrade_unavailable_text": "The upgrade flow is not available yet because no support WhatsApp number is configured in settings.",
        "order_blocked_upgrade_unavailable": "Order creation blocked: FREE quota is exhausted and upgrade is unavailable until platform WhatsApp is configured.",
        "order_created": "Order created successfully.",
        "order_summary": "Order summary",
        "order_code": "Order code",
        "order_total_xaf": "Total to pay",
        "order_fee_xaf": "AfriPay fee",
        "send_cart_whatsapp": "Send cart link to AfriPay",
        "send_payment_proof": "Send payment proof",
        "proof_intro": "Once AfriPay validates the cart, send your payment proof to the team.",
        "proof_unavailable_text": "WhatsApp is not configured on the platform yet. The order was created, but WhatsApp actions are not available for now.",
        "recent_orders": "My recent orders",
        "status": "Status",
        "empty_orders": "No orders yet.",
        "login_success": "Account loaded successfully.",
        "login_error_phone": "Phone number is required.",
        "upgrade_cta_free": "Your FREE offer is exhausted. Upgrade to PREMIUM or PREMIUM_PLUS.",
        "configured_missing_whatsapp": "No WhatsApp number configured in settings.",
        "subscription_active_until": "Active until",
        "subscription_status": "Subscription status",
        "admin_login_title": "Admin area",
        "admin_password": "Admin password",
        "admin_login_button": "Admin login",
        "admin_logout": "🚪 Admin logout",
    },
}

COUNTRY_LABELS = {
    "CM": "Cameroun",
    "CI": "Côte d'Ivoire",
    "CD": "RDC",
    "GA": "Gabon",
    "NG": "Nigeria",
    "KE": "Kenya",
    "MZ": "Mozambique",
}

ORDER_STATUS_COLORS = {
    "CREEE": ("#1E3A8A", "#FFFFFF"),
    "PAYEE": ("#065F46", "#FFFFFF"),
    "EN_COURS": ("#92400E", "#FFFFFF"),
    "LIVREE": ("#064E3B", "#FFFFFF"),
    "ANNULEE": ("#7F1D1D", "#FFFFFF"),
    "PENDING": ("#78350F", "#FFFFFF"),
    "PROOF_SENT": ("#92400E", "#FFFFFF"),
    "PROOF_RECEIVED": ("#1E40AF", "#FFFFFF"),
    "CONFIRMED": ("#065F46", "#FFFFFF"),
    "REJECTED": ("#7F1D1D", "#FFFFFF"),
    REFUND_STATUS_PENDING: ("#7C3AED", "#FFFFFF"),
    REFUND_STATUS_PROCESSING: ("#9333EA", "#FFFFFF"),
    REFUND_STATUS_COMPLETED: ("#0F766E", "#FFFFFF"),
    REFUND_STATUS_PROOF_SENT: ("#0369A1", "#FFFFFF"),
    REFUND_STATUS_CONFIRMED: ("#14532D", "#FFFFFF"),
}


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title=APP_NAME, page_icon="🌍", layout="wide")


# =========================================================
# STYLES
# =========================================================
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        [data-testid="stSidebar"] {background:#0F172A;}
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] span {
            color: white !important;
        }
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6 {
            color: #F8FAFC;
        }
        .af-card {
            background: rgba(255,255,255,0.88);
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 8px 24px rgba(15,23,42,0.06);
            margin-bottom: 12px;
        }
        .af-warning-card {
            background: rgba(254, 243, 199, 0.95);
            border: 1px solid rgba(217, 119, 6, 0.22);
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 12px;
        }
        .af-warning-card h4 {
            margin: 0 0 6px 0;
            color: #92400E !important;
        }
        .af-warning-card p {
            margin: 0;
            color: #78350F !important;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] {
            background: rgba(26, 188, 156, 0.15) !important;
            border: 1px solid rgba(26, 188, 156, 0.4) !important;
            border-radius: 14px !important;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] .af-card,
        [data-testid="stSidebar"] .af-card * {
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
        }
        [data-testid="stSidebar"] .stButton button {
            background: #1ABC9C !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 14px !important;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background: #17A589 !important;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] .stButton button p,
        [data-testid="stSidebar"] .stButton button span {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }
        .af-hero {
            background: linear-gradient(135deg, rgba(26,188,156,0.12), rgba(15,23,42,0.06));
            border-radius: 22px;
            padding: 22px;
            margin-bottom: 16px;
            border: 1px solid rgba(26,188,156,0.16);
        }
        .af-badge {
            display:inline-block;
            border-radius:999px;
            padding: 6px 12px;
            font-size: 0.85rem;
            font-weight:600;
            margin-top:4px;
        }
        .af-kpi {
            background: rgba(255,255,255,0.92);
            border-radius: 18px;
            padding: 16px;
            border: 1px solid rgba(15,23,42,0.08);
            box-shadow: 0 8px 24px rgba(15,23,42,0.06);
        }
        .af-muted {color:#475569;}
        .af-plan {
            border:1px solid rgba(15,23,42,0.08);
            border-radius:18px;
            padding:16px;
            background:#fff;
            box-shadow: 0 8px 24px rgba(15,23,42,0.04);
            min-height: 180px;
        }
        .af-small {font-size:0.9rem;color:#475569;}
        .admin-action-box {
            background: rgba(15,23,42,0.03);
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 14px;
            padding: 12px;
            margin-top: 10px;
            margin-bottom: 20px;
        }
        .admin-nav-title {
            font-size: 0.95rem;
            font-weight: 800;
            color: #F8FAFC;
            margin-top: 8px;
            margin-bottom: 8px;
        }
        .admin-section-card {
            background: linear-gradient(145deg, #1E293B, #0F172A);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.35);
        }
        .admin-money-line {
            color:#94A3B8;
            font-size:0.88rem;
            margin-top:4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# HELPERS
# =========================================================
def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def tr(key: str) -> str:
    lang = get_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE]).get(key, key)


def normalize_country_code(value: str, fallback: str = APP_BASE_COUNTRY) -> str:
    value = clean_text(value).upper()
    if not value:
        return fallback
    value = value[:2]
    return value if value in SUPPORTED_COUNTRIES else fallback


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    value = str(phone).strip()
    for char in [" ", "-", ".", "(", ")", "/"]:
        value = value.replace(char, "")
    return value


def sanitize_whatsapp_phone(phone: str) -> str:
    raw = normalize_phone(phone)
    if raw.startswith("+"):
        raw = raw[1:]
    return "".join(ch for ch in raw if ch.isdigit())


def format_xaf(value) -> str:
    try:
        return f"{int(round(float(value or 0))):,}".replace(",", " ")
    except Exception:
        return "0"


def format_eur(value) -> str:
    try:
        amount = float(value or 0)
        return f"{amount:,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"


def format_date_display(value) -> str:
    text = clean_text(value)
    if not text:
        return "-"
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return text


def format_datetime_display(value) -> str:
    text = clean_text(value)
    if not text:
        return "-"
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return text


def safe_int(value, default: int = 0) -> int:
    try:
        return int(round(float(value or 0)))
    except Exception:
        return default


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return default


def dict_row(row) -> dict:
    try:
        return dict(row or {})
    except Exception:
        return {}


def get_eur_xaf_rate() -> float:
    raw = get_setting("eur_xaf_rate", get_setting("EUR_XAF_RATE", "655.957"))
    try:
        value = float(raw)
        if value <= 0:
            return 655.957
        return value
    except Exception:
        return 655.957


def xaf_to_eur(amount_xaf) -> float:
    rate = get_eur_xaf_rate()
    try:
        return float(amount_xaf or 0) / rate if rate > 0 else 0.0
    except Exception:
        return 0.0


def format_dual_amount(amount_xaf) -> str:
    eur = xaf_to_eur(amount_xaf)
    return f"{format_xaf(amount_xaf)} XAF · {format_eur(eur)} EUR"


def format_dual_amount_multiline(amount_xaf) -> str:
    eur = xaf_to_eur(amount_xaf)
    return f"{format_xaf(amount_xaf)} XAF<br><span class='admin-money-line'>≈ {format_eur(eur)} EUR</span>"


# =========================================================
# SETTINGS
# =========================================================
def _read_setting_from_admin_service(key: str):
    if admin_get_setting is None:
        return None

    try:
        return admin_get_setting(key)
    except TypeError:
        try:
            return admin_get_setting(key, "")
        except Exception:
            return None
    except Exception:
        return None


def get_setting(key: str, default: str = "") -> str:
    key = clean_text(key)
    if not key:
        return default

    value = _read_setting_from_admin_service(key)
    if value not in [None, ""]:
        return clean_text(value)

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
    cc = normalize_country_code(country_code)
    candidates = [
        f"whatsapp_number_{cc.lower()}",
        f"whatsapp_number_{cc}",
        f"WHATSAPP_{cc}",
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


def get_support_whatsapp_number() -> str:
    for key in [
        "support_whatsapp_number",
        "SUPPORT_WHATSAPP_NUMBER",
        "whatsapp_default",
        "WHATSAPP_DEFAULT",
    ]:
        value = sanitize_whatsapp_phone(get_setting(key, ""))
        if value:
            return value
    return ""


def get_best_whatsapp_number(country_code: str) -> str:
    country_value = get_country_whatsapp_number(country_code)
    if country_value:
        return country_value
    return get_support_whatsapp_number()


def has_any_whatsapp_configured(country_code: str | None = None) -> bool:
    cc = normalize_country_code(country_code or get_default_country())
    return bool(get_best_whatsapp_number(cc))


def get_brand_name() -> str:
    return get_setting("brand_name", APP_NAME) or APP_NAME


def get_default_country() -> str:
    return normalize_country_code(
        get_setting("default_country_code", APP_BASE_COUNTRY),
        APP_BASE_COUNTRY,
    )


def get_premium_plus_price(months: int) -> str:
    if months == 12:
        return get_setting("premium_plus_price_12m", get_setting("premium_plus_price_annual", ""))
    return get_setting("premium_plus_price_6m", get_setting("premium_plus_price_semestrial", ""))


def get_admin_password_value() -> str:
    env_password = clean_text(os.getenv("ADMIN_PASSWORD", ""))
    if env_password:
        return env_password

    return clean_text(get_setting("admin_password", ""))


def build_whatsapp_url(phone: str, message: str) -> str:
    safe_phone = sanitize_whatsapp_phone(phone)
    if not safe_phone:
        return ""
    return f"https://wa.me/{safe_phone}?text={urllib.parse.quote(clean_text(message))}"


# =========================================================
# SESSION / USER
# =========================================================
def ensure_app_session() -> None:
    init_session()

    defaults = {
        "language": DEFAULT_LANGUAGE,
        "selected_country": get_default_country(),
        "premium_page_open": False,
        "last_order_code": "",
        "admin_filter": "ALL",
        "admin_view": ADMIN_VIEW_DASHBOARD,
        "is_admin": False,
        "selected_order_plan": "",
        "selected_order_plan_manual": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_language() -> str:
    lang = clean_text(st.session_state.get("language", DEFAULT_LANGUAGE)).lower()
    return lang if lang in {"fr", "en"} else DEFAULT_LANGUAGE


def get_selected_country() -> str:
    return normalize_country_code(
        st.session_state.get("selected_country", get_default_country()),
        get_default_country(),
    )


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


def render_captcha_block(prefix: str, title: str | None = None, allow_refresh: bool = True) -> str:
    ensure_captcha(prefix)

    a = st.session_state.get(f"{prefix}_captcha_a", 0)
    b = st.session_state.get(f"{prefix}_captcha_b", 0)

    st.markdown(f"### {title or tr('captcha_title')}")
    st.warning(tr("captcha_required"))
    st.info(tr("captcha_info").format(a=a, b=b))

    existing_error = get_captcha_error(prefix)
    if existing_error:
        st.error(existing_error)

    if allow_refresh:
        col1, col2 = st.columns([3, 1])
    else:
        col1 = st.container()
        col2 = None

    with col1:
        captcha_input = st.text_input(
            tr("captcha_input"),
            key=f"{prefix}_captcha_input",
            placeholder=tr("captcha_placeholder"),
            help=tr("captcha_help"),
        )

        status = get_captcha_status(prefix, captcha_input)
        if captcha_input.strip():
            if status == "ok":
                st.success(tr("captcha_ok"))
            elif status in {"invalid", "missing"}:
                st.error(tr("captcha_bad"))

    if allow_refresh and col2 is not None:
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(tr("captcha_refresh"), key=f"{prefix}_captcha_refresh", width=UI_WIDTH_STRETCH):
                refresh_captcha(prefix)
                clear_captcha_error(prefix)
                st.rerun()

    if "captcha_caption" in TRANSLATIONS.get(get_language(), {}):
        st.caption(tr("captcha_caption"))

    return captcha_input


def render_test_otp_panel(current_phone: str = "") -> None:
    current_phone = str(current_phone or "").strip()
    otp_code = str(st.session_state.get("otp_code", "") or "").strip()
    otp_phone = normalize_phone(
        st.session_state.get("otp_phone", "")
        or st.session_state.get("login_phone_input", "")
        or current_phone
    )

    if not otp_code:
        st.info(tr("otp_none"))
        return

    if current_phone and otp_phone and current_phone != otp_phone:
        st.warning(tr("otp_other_phone"))

    st.markdown(tr("otp_test_mode"))
    st.warning(tr("otp_test_warning"))

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
        {tr("otp_linked_phone")}
    </div>
    <div style="font-size: 28px; font-weight: 900; margin-bottom: 18px;">
        {otp_phone or "—"}
    </div>
    <div style="font-size: 18px; font-weight: 800; margin-bottom: 10px;">
        {tr("otp_test_code")}
    </div>
    <div style="font-size: 46px; font-weight: 900; letter-spacing: 10px; line-height: 1.2;">
        {otp_code}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.info(tr("otp_keep_info"))


def clear_login_test_otp() -> None:
    st.session_state.pop("otp_code", None)
    st.session_state.pop("otp_phone", None)


def request_login_form_reset() -> None:
    st.session_state["reset_login_form_pending"] = True


def apply_login_form_reset_if_needed() -> None:
    if not st.session_state.pop("reset_login_form_pending", False):
        return

    st.session_state["login_phone_input"] = ""
    st.session_state["login_otp_input"] = ""
    st.session_state["login_name_input"] = ""
    st.session_state["login_email_input"] = ""


def init_otp_rate_limit_state() -> None:
    if "otp_request_log" not in st.session_state:
        st.session_state["otp_request_log"] = {}


def get_now_utc() -> datetime:
    return datetime.now(UTC)


def get_phone_otp_requests(phone: str):
    init_otp_rate_limit_state()

    clean_phone = str(phone or "").strip()
    if not clean_phone:
        return []

    raw_requests = st.session_state["otp_request_log"].get(clean_phone, [])
    now = get_now_utc()
    window_start = now - timedelta(minutes=OTP_WINDOW_MINUTES)

    valid_requests = []
    for item in raw_requests:
        if isinstance(item, datetime):
            if item.tzinfo is None:
                item = item.replace(tzinfo=UTC)
            if item >= window_start:
                valid_requests.append(item)

    st.session_state["otp_request_log"][clean_phone] = valid_requests
    return valid_requests


def record_otp_request(phone: str) -> None:
    init_otp_rate_limit_state()

    clean_phone = str(phone or "").strip()
    if not clean_phone:
        return

    requests = get_phone_otp_requests(clean_phone)
    requests.append(get_now_utc())
    st.session_state["otp_request_log"][clean_phone] = requests


def get_otp_rate_limit_status(phone: str) -> dict:
    clean_phone = str(phone or "").strip()
    if not clean_phone:
        return {
            "allowed": True,
            "reason": "",
            "wait_seconds": 0,
            "wait_minutes": 0,
        }

    requests = get_phone_otp_requests(clean_phone)
    now = get_now_utc()

    if requests:
        last_request = requests[-1]
        cooldown_end = last_request + timedelta(seconds=OTP_COOLDOWN_SECONDS)
        if now < cooldown_end:
            remaining_seconds = int((cooldown_end - now).total_seconds()) + 1
            return {
                "allowed": False,
                "reason": "cooldown",
                "wait_seconds": remaining_seconds,
                "wait_minutes": 0,
            }

    if len(requests) >= OTP_MAX_REQUESTS:
        oldest_relevant_request = requests[0]
        retry_at = oldest_relevant_request + timedelta(minutes=OTP_WINDOW_MINUTES)
        if now < retry_at:
            remaining_seconds = int((retry_at - now).total_seconds()) + 1
            remaining_minutes = max(1, (remaining_seconds + 59) // 60)
            return {
                "allowed": False,
                "reason": "window_limit",
                "wait_seconds": remaining_seconds,
                "wait_minutes": remaining_minutes,
            }

    return {
        "allowed": True,
        "reason": "",
        "wait_seconds": 0,
        "wait_minutes": 0,
    }


def set_connected_user(user_id: int, phone: str, name: str = "", email: str = "") -> None:
    for key in [
        "user_id",
        "client_phone",
        "client_name",
        "client_email",
        "last_order_code",
    ]:
        st.session_state.pop(key, None)

    st.session_state["user_id"] = int(user_id)
    st.session_state["client_phone"] = normalize_phone(phone)
    st.session_state["client_name"] = clean_text(name)
    st.session_state["client_email"] = clean_text(email)


def get_current_user() -> dict | None:
    user_id = st.session_state.get("user_id")
    if not user_id:
        return None
    try:
        return get_user_by_id(int(user_id))
    except Exception:
        return None


# =========================================================
# PLAN LOGIC
# =========================================================
def get_user_country_code(user: dict | None) -> str:
    if user:
        value = user.get("country_code") or user.get("country")
        if value:
            return normalize_country_code(value)
    return get_selected_country()


def get_base_user_plan(user: dict | None) -> str:
    if not user:
        return PLAN_FREE
    value = clean_text(user.get("plan", PLAN_FREE)).upper()
    if value not in {PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return PLAN_FREE
    return value


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    text = clean_text(value).lower()
    return text in {"1", "true", "yes", "oui", "active", "confirmed", "paid"}


def is_premium_plus_active(user: dict | None) -> bool:
    if not user:
        return False

    explicit_flags = [
        user.get("premium_plus_active"),
        user.get("is_premium_plus_active"),
        user.get("subscription_active"),
    ]
    if any(_truthy(v) for v in explicit_flags):
        return True

    status_candidates = [
        clean_text(user.get("premium_plus_status")).upper(),
        clean_text(user.get("subscription_status")).upper(),
        clean_text(user.get("premium_status")).upper(),
    ]
    if any(v in {"ACTIVE", "CONFIRMED", "PAID"} for v in status_candidates if v):
        return True

    end_date = clean_text(
        user.get("subscription_end_date") or user.get("premium_plus_end_date") or ""
    )
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            reference_now = datetime.now(end_dt.tzinfo or UTC)
            return end_dt >= reference_now
        except Exception:
            pass

    return False


def get_effective_user_plan(user: dict | None) -> str:
    base_plan = get_base_user_plan(user)
    if base_plan == PLAN_PREMIUM_PLUS and not is_premium_plus_active(user):
        return PLAN_PREMIUM
    return base_plan


def get_free_orders_used(user: dict | None) -> int:
    if not user:
        return 0
    try:
        return max(0, int(user.get("free_orders_used", 0) or 0))
    except Exception:
        return 0


def get_free_orders_remaining(user: dict | None) -> int:
    if get_effective_user_plan(user) in {PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return FREE_MAX_ORDERS
    return max(0, FREE_MAX_ORDERS - get_free_orders_used(user))


def can_create_order(user: dict | None) -> bool:
    if get_effective_user_plan(user) in {PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return True
    return get_free_orders_remaining(user) > 0


def validate_free_order_rules(user: dict | None, merchant_total_xaf: float | int) -> str | None:
    if get_effective_user_plan(user) in {PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return None

    if get_free_orders_remaining(user) <= 0:
        return "FREE_LIMIT_REACHED"

    try:
        amount = int(round(float(merchant_total_xaf or 0)))
    except Exception:
        return "FREE_AMOUNT_LIMIT_EXCEEDED"

    if amount > FREE_MAX_ORDER_XAF:
        return "FREE_AMOUNT_LIMIT_EXCEEDED"

    return None


def estimate_merchant_total_xaf(merchant_total_eur: float) -> int:
    rate = get_setting("eur_xaf_rate", get_setting("EUR_XAF_RATE", "655.957"))
    try:
        rate_value = float(rate)
    except Exception:
        rate_value = 655.957
    return _round_xaf(float(merchant_total_eur or 0) * rate_value)


# =========================================================
# ORDER / WHATSAPP MESSAGES
# =========================================================
def build_cart_validation_message(user: dict | None, merchant_name: str, product_url: str) -> str:
    brand = get_brand_name()
    client_name = clean_text((user or {}).get("name") or st.session_state.get("client_name", "Client"))
    country = get_user_country_code(user)
    return (
        f"Bonjour {brand},\n\n"
        f"Je souhaite faire valider mon panier.\n"
        f"Client : {client_name}\n"
        f"Pays : {country}\n"
        f"Marchand : {clean_text(merchant_name)}\n"
        f"Lien : {clean_text(product_url)}\n\n"
        f"Merci de vérifier puis de me confirmer avant paiement."
    )


def build_upgrade_message(user: dict | None, target_plan: str, months: int | None = None) -> str:
    brand = get_brand_name()
    client_name = clean_text((user or {}).get("name") or st.session_state.get("client_name", "Client"))
    client_phone = clean_text((user or {}).get("phone") or st.session_state.get("client_phone", ""))
    country = get_user_country_code(user)

    lines = [
        f"Bonjour {brand},",
        "",
        "Je souhaite changer de formule.",
        f"Client : {client_name}",
        f"Téléphone : {client_phone}",
        f"Pays : {country}",
        f"Formule demandée : {target_plan}",
    ]

    if target_plan == PLAN_PREMIUM_PLUS and months in PLAN_DURATION_OPTIONS:
        price = get_premium_plus_price(months)
        lines.append(f"Durée : {months} mois")
        if price:
            lines.append(f"Montant annoncé : {price}")

    lines.extend([
        "",
        "Merci de m'envoyer les instructions de paiement.",
    ])
    return "\n".join(lines)


def build_payment_proof_message(order: dict | None, user: dict | None) -> str:
    brand = get_brand_name()
    client_name = clean_text((user or {}).get("name") or st.session_state.get("client_name", "Client"))
    client_phone = clean_text((user or {}).get("phone") or st.session_state.get("client_phone", ""))
    order_code = clean_text((order or {}).get("order_code", st.session_state.get("last_order_code", "")))
    total_xaf = format_xaf((order or {}).get("total_xaf", 0))
    return (
        f"Bonjour {brand},\n\n"
        f"J'envoie ma preuve de paiement.\n"
        f"Client : {client_name}\n"
        f"Téléphone : {client_phone}\n"
        f"Commande : {order_code}\n"
        f"Montant : {total_xaf} XAF\n\n"
        f"Je joins la capture de paiement pour validation."
    )


# =========================================================
# DATA ACCESS / FALLBACK DB HELPERS
# =========================================================
def _column_exists(table_name: str, column_name: str) -> bool:
    try:
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                LIMIT 1
                """,
                (table_name, column_name),
            )
            return cur.fetchone() is not None
    except Exception:
        return False


def get_recent_orders_for_user(user_id: int, limit: int = 10) -> list[dict]:
    queries = [
        """
        SELECT *
        FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC NULLS LAST, id DESC
        LIMIT %s
        """,
        """
        SELECT *
        FROM orders
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT %s
        """,
    ]
    for query in queries:
        try:
            with get_cursor() as cur:
                cur.execute(query, (int(user_id), int(limit)))
                rows = cur.fetchall() or []
                return [dict(row) for row in rows]
        except Exception:
            continue
    return []


def get_all_orders(limit: int = 100) -> list[dict]:
    rich_query = """
        SELECT
            id,
            order_code,
            user_id,
            client_name,
            client_phone,
            client_email,
            site_name,
            product_title,
            product_url,
            order_status,
            payment_status,
            total_xaf,
            merchant_total_xaf,
            afripay_fee_xaf,
            created_at,
            admin_note,
            payment_proof_sent_at,
            payment_proof_received_at,
            refund_status,
            refund_amount_xaf,
            refund_reason,
            refund_processed_at,
            refund_proof_sent_at,
            refund_confirmed_at,
            product_price_eur,
            freight_forwarder_name,
            freight_forwarder_address,
            payment_method
        FROM orders
        ORDER BY created_at DESC NULLS LAST, id DESC
        LIMIT %s
    """
    basic_query = """
        SELECT
            id,
            order_code,
            user_id,
            client_name,
            client_phone,
            client_email,
            site_name,
            product_title,
            order_status,
            payment_status,
            total_xaf,
            merchant_total_xaf,
            afripay_fee_xaf,
            created_at
        FROM orders
        ORDER BY created_at DESC NULLS LAST, id DESC
        LIMIT %s
    """

    for query in [rich_query, basic_query]:
        try:
            with get_cursor() as cur:
                cur.execute(query, (int(limit),))
                return [dict(row) for row in (cur.fetchall() or [])]
        except Exception:
            continue

    return []


def get_refund_status(row: dict) -> str:
    value = clean_text((row or {}).get("refund_status") or REFUND_STATUS_NONE).upper()
    return value or REFUND_STATUS_NONE


def get_admin_kpi_data() -> dict:
    rows = get_all_orders(limit=1000)
    now = datetime.now(UTC)
    today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    week_start = today_start - timedelta(days=7)

    total_orders = len(rows)
    total_paid = 0
    total_in_progress = 0
    total_delivered = 0
    total_cancelled = 0
    total_volume_xaf = 0
    gmv_today_xaf = 0
    gmv_week_xaf = 0
    total_commissions_xaf = 0
    total_refunds_xaf = 0

    for row in rows:
        order_status = clean_text(row.get("order_status") or "").upper()
        payment_status = clean_text(row.get("payment_status") or "").upper()
        refund_status = get_refund_status(row)
        total_xaf = safe_int(row.get("total_xaf", 0))
        fee_xaf = safe_int(row.get("afripay_fee_xaf", 0))
        refund_amount_xaf = safe_int(row.get("refund_amount_xaf", 0))

        created_at_text = clean_text(row.get("created_at"))
        created_at = None
        if created_at_text:
            try:
                created_at = datetime.fromisoformat(created_at_text.replace("Z", "+00:00"))
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=UTC)
            except Exception:
                created_at = None

        if order_status == "PAYEE":
            total_paid += 1
        if order_status == "EN_COURS":
            total_in_progress += 1
        if order_status == "LIVREE":
            total_delivered += 1
        if order_status == "ANNULEE":
            total_cancelled += 1

        total_volume_xaf += total_xaf

        if payment_status == "CONFIRMED":
            total_commissions_xaf += fee_xaf
            if created_at and created_at >= today_start:
                gmv_today_xaf += total_xaf
            if created_at and created_at >= week_start:
                gmv_week_xaf += total_xaf

        if refund_status in {REFUND_STATUS_COMPLETED, REFUND_STATUS_PROOF_SENT, REFUND_STATUS_CONFIRMED}:
            total_refunds_xaf += refund_amount_xaf if refund_amount_xaf > 0 else total_xaf

    return {
        "total_orders": total_orders,
        "total_paid": total_paid,
        "total_in_progress": total_in_progress,
        "total_delivered": total_delivered,
        "total_cancelled": total_cancelled,
        "total_volume_xaf": total_volume_xaf,
        "total_volume_eur": xaf_to_eur(total_volume_xaf),
        "gmv_today_xaf": gmv_today_xaf,
        "gmv_today_eur": xaf_to_eur(gmv_today_xaf),
        "gmv_week_xaf": gmv_week_xaf,
        "gmv_week_eur": xaf_to_eur(gmv_week_xaf),
        "total_commissions_xaf": total_commissions_xaf,
        "total_commissions_eur": xaf_to_eur(total_commissions_xaf),
        "total_refunds_xaf": total_refunds_xaf,
        "total_refunds_eur": xaf_to_eur(total_refunds_xaf),
    }


def mark_payment_proof_sent_db(order_code: str, admin_note: str = "") -> bool:
    try:
        with get_cursor() as cur:
            if _column_exists("orders", "payment_proof_sent_at") and _column_exists("orders", "admin_note"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        payment_status = 'PROOF_SENT',
                        payment_proof_sent_at = NOW(),
                        admin_note = COALESCE(NULLIF(%s, ''), admin_note)
                    WHERE order_code = %s
                    """,
                    (clean_text(admin_note), clean_text(order_code)),
                )
            elif _column_exists("orders", "payment_proof_sent_at"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        payment_status = 'PROOF_SENT',
                        payment_proof_sent_at = NOW()
                    WHERE order_code = %s
                    """,
                    (clean_text(order_code),),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET payment_status = 'PROOF_SENT'
                    WHERE order_code = %s
                    """,
                    (clean_text(order_code),),
                )
            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def mark_payment_proof_received_db(order_code: str, admin_note: str = "") -> bool:
    try:
        with get_cursor() as cur:
            if _column_exists("orders", "payment_proof_received_at") and _column_exists("orders", "admin_note"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        payment_status = 'PROOF_RECEIVED',
                        payment_proof_received_at = NOW(),
                        admin_note = COALESCE(NULLIF(%s, ''), admin_note)
                    WHERE order_code = %s
                    """,
                    (clean_text(admin_note), clean_text(order_code)),
                )
            elif _column_exists("orders", "payment_proof_received_at"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        payment_status = 'PROOF_RECEIVED',
                        payment_proof_received_at = NOW()
                    WHERE order_code = %s
                    """,
                    (clean_text(order_code),),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET payment_status = 'PROOF_RECEIVED'
                    WHERE order_code = %s
                    """,
                    (clean_text(order_code),),
                )
            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def cancel_order_fallback_db(order_code: str, admin_note: str = "") -> bool:
    try:
        with get_cursor() as cur:
            if _column_exists("orders", "admin_note"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        order_status = 'ANNULEE',
                        admin_note = COALESCE(NULLIF(%s, ''), admin_note)
                    WHERE order_code = %s
                    """,
                    (clean_text(admin_note), clean_text(order_code)),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET order_status = 'ANNULEE'
                    WHERE order_code = %s
                    """,
                    (clean_text(order_code),),
                )
            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def start_refund_db(order_code: str, refund_amount_xaf: int, refund_reason: str = "") -> bool:
    if not _column_exists("orders", "refund_status"):
        return False

    try:
        with get_cursor() as cur:
            cols = {
                "refund_amount_xaf": _column_exists("orders", "refund_amount_xaf"),
                "refund_reason": _column_exists("orders", "refund_reason"),
            }

            if cols["refund_amount_xaf"] and cols["refund_reason"]:
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        refund_status = %s,
                        refund_amount_xaf = %s,
                        refund_reason = %s
                    WHERE order_code = %s
                    """,
                    (
                        REFUND_STATUS_PENDING,
                        int(refund_amount_xaf or 0),
                        clean_text(refund_reason),
                        clean_text(order_code),
                    ),
                )
            elif cols["refund_amount_xaf"]:
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        refund_status = %s,
                        refund_amount_xaf = %s
                    WHERE order_code = %s
                    """,
                    (
                        REFUND_STATUS_PENDING,
                        int(refund_amount_xaf or 0),
                        clean_text(order_code),
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET refund_status = %s
                    WHERE order_code = %s
                    """,
                    (
                        REFUND_STATUS_PENDING,
                        clean_text(order_code),
                    ),
                )

            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def mark_refund_processing_db(order_code: str) -> bool:
    if not _column_exists("orders", "refund_status"):
        return False
    try:
        with get_cursor() as cur:
            cur.execute(
                """
                UPDATE orders
                SET refund_status = %s
                WHERE order_code = %s
                """,
                (REFUND_STATUS_PROCESSING, clean_text(order_code)),
            )
            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def mark_refund_completed_db(order_code: str) -> bool:
    if not _column_exists("orders", "refund_status"):
        return False
    try:
        with get_cursor() as cur:
            if _column_exists("orders", "refund_processed_at"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        refund_status = %s,
                        refund_processed_at = NOW()
                    WHERE order_code = %s
                    """,
                    (REFUND_STATUS_COMPLETED, clean_text(order_code)),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET refund_status = %s
                    WHERE order_code = %s
                    """,
                    (REFUND_STATUS_COMPLETED, clean_text(order_code)),
                )
            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def mark_refund_proof_sent_db(order_code: str) -> bool:
    if not _column_exists("orders", "refund_status"):
        return False
    try:
        with get_cursor() as cur:
            if _column_exists("orders", "refund_proof_sent_at"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        refund_status = %s,
                        refund_proof_sent_at = NOW()
                    WHERE order_code = %s
                    """,
                    (REFUND_STATUS_PROOF_SENT, clean_text(order_code)),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET refund_status = %s
                    WHERE order_code = %s
                    """,
                    (REFUND_STATUS_PROOF_SENT, clean_text(order_code)),
                )
            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def mark_refund_confirmed_db(order_code: str) -> bool:
    if not _column_exists("orders", "refund_status"):
        return False
    try:
        with get_cursor() as cur:
            if _column_exists("orders", "refund_confirmed_at"):
                cur.execute(
                    """
                    UPDATE orders
                    SET
                        refund_status = %s,
                        refund_confirmed_at = NOW()
                    WHERE order_code = %s
                    """,
                    (REFUND_STATUS_CONFIRMED, clean_text(order_code)),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET refund_status = %s
                    WHERE order_code = %s
                    """,
                    (REFUND_STATUS_CONFIRMED, clean_text(order_code)),
                )
            return (cur.rowcount or 0) > 0
    except Exception:
        return False


def mark_payment_proof_sent_safe(order_code: str, admin_note: str = "") -> bool:
    if mark_payment_proof_sent is not None:
        try:
            return bool(mark_payment_proof_sent(order_code, admin_note=admin_note))
        except TypeError:
            try:
                return bool(mark_payment_proof_sent(order_code))
            except Exception:
                pass
        except Exception:
            pass
    return mark_payment_proof_sent_db(order_code, admin_note=admin_note)


def mark_payment_proof_received_safe(order_code: str, admin_note: str = "") -> bool:
    if mark_payment_proof_received is not None:
        try:
            return bool(mark_payment_proof_received(order_code, admin_note=admin_note))
        except TypeError:
            try:
                return bool(mark_payment_proof_received(order_code))
            except Exception:
                pass
        except Exception:
            pass
    return mark_payment_proof_received_db(order_code, admin_note=admin_note)


def cancel_order_safe(order_code: str, admin_note: str = "") -> bool:
    if cancel_order is not None:
        try:
            return bool(cancel_order(order_code, admin_note=admin_note))
        except TypeError:
            try:
                return bool(cancel_order(order_code))
            except Exception:
                pass
        except Exception:
            pass
    return cancel_order_fallback_db(order_code, admin_note=admin_note)


def resolve_created_order(created_result) -> dict | None:
    if isinstance(created_result, dict):
        if created_result.get("order_code"):
            return created_result
        return None

    order_code = clean_text(created_result)
    if not order_code:
        return None

    try:
        return get_order_by_code(order_code)
    except Exception:
        return None



def set_selected_order_plan(plan: str) -> None:
    value = clean_text(plan).upper()
    if value not in {PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return

    st.session_state["selected_order_plan"] = value
    st.session_state["selected_order_plan_manual"] = True


def get_selected_order_plan(user: dict | None) -> str:
    manual = bool(st.session_state.get("selected_order_plan_manual", False))
    selected = clean_text(st.session_state.get("selected_order_plan", "")).upper()

    if manual and selected in {PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return selected

    if user:
        base_plan = get_base_user_plan(user)
        if base_plan in {PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
            return base_plan

    return ""


def get_plan_cta_label(plan: str) -> str:
    lang = get_language()
    mapping = {
        "fr": {
            PLAN_FREE: "Commander en FREE",
            PLAN_PREMIUM: "Commander en PREMIUM",
            PLAN_PREMIUM_PLUS: "Commander en PREMIUM_PLUS",
        },
        "en": {
            PLAN_FREE: "Order with FREE",
            PLAN_PREMIUM: "Order with PREMIUM",
            PLAN_PREMIUM_PLUS: "Order with PREMIUM_PLUS",
        },
    }
    return mapping.get(lang, mapping["fr"]).get(plan, plan)


def get_selected_plan_notice(plan: str) -> tuple[str, str]:
    lang = get_language()
    notices = {
        "fr": {
            PLAN_FREE: ("FREE sélectionné", "Votre commande sera créée sous l'option FREE avec ses limites applicables."),
            PLAN_PREMIUM: ("PREMIUM sélectionné", "Votre commande sera créée sous l'option PREMIUM avec frais AfriPay de 20%."),
            PLAN_PREMIUM_PLUS: ("PREMIUM_PLUS sélectionné", "Votre commande sera créée sous l'option PREMIUM_PLUS. Tant que l'abonnement n'est pas actif, le comportement PREMIUM s'applique."),
        },
        "en": {
            PLAN_FREE: ("FREE selected", "Your order will be created under FREE with its applicable limits."),
            PLAN_PREMIUM: ("PREMIUM selected", "Your order will be created under PREMIUM with a 20% AfriPay fee."),
            PLAN_PREMIUM_PLUS: ("PREMIUM_PLUS selected", "Your order will be created under PREMIUM_PLUS. Until the subscription is active, PREMIUM behavior applies."),
        },
    }
    return notices.get(lang, notices["fr"]).get(plan, ("", ""))


def sync_user_plan_for_selection(user: dict | None, selected_plan: str) -> None:
    if not user or not user.get("id"):
        return

    selected_plan = clean_text(selected_plan).upper()
    if selected_plan not in {PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return

    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE users
                SET plan = %s
                WHERE id = %s
                """,
                (selected_plan, int(user["id"])),
            )
    except Exception:
        pass


# =========================================================
# UI BLOCKS
# =========================================================
def render_hero() -> None:
    lang = get_language()

    base_dir = Path(__file__).resolve().parent
    assets_dir = base_dir / "assets"

    hero_banner_fr = assets_dir / "hero_banner_fr.png"
    hero_banner_en = assets_dir / "hero_banner_en.png"
    logo_path = assets_dir / "logo.png"

    if lang == "fr":
        banner_path = hero_banner_fr if hero_banner_fr.exists() else hero_banner_en
    else:
        banner_path = hero_banner_en if hero_banner_en.exists() else hero_banner_fr

    try:
        if banner_path.exists():
            img = Image.open(banner_path)
            st.image(img, width=UI_WIDTH_STRETCH)
            return
        if logo_path.exists():
            img = Image.open(logo_path)
            st.image(img, width=180)
            return
    except Exception:
        pass

    st.markdown(
        f"""
        <div class="af-hero">
            <h1 style="margin:0 0 8px 0;">{tr('hero_title')}</h1>
            <p style="margin:0; font-size:1.02rem; color:#334155;">{tr('hero_text')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_language_and_country_controls() -> None:
    lang_options = {"fr": "Français", "en": "English"}
    current_lang = get_language()
    selected_lang = st.sidebar.selectbox(
        tr("sidebar_lang"),
        options=list(lang_options.keys()),
        index=list(lang_options.keys()).index(current_lang),
        format_func=lambda x: lang_options[x],
    )

    if selected_lang != current_lang:
        st.session_state["language"] = selected_lang
        st.rerun()

    current_country = get_selected_country()
    selected_country = st.sidebar.selectbox(
        tr("sidebar_country"),
        options=SUPPORTED_COUNTRIES,
        index=SUPPORTED_COUNTRIES.index(current_country) if current_country in SUPPORTED_COUNTRIES else 0,
        format_func=lambda x: COUNTRY_LABELS.get(x, x),
    )
    st.session_state["selected_country"] = selected_country


def render_sidebar(user: dict | None) -> None:
    is_admin = st.session_state.get("is_admin", False)
    render_sidebar_branding()
    render_language_and_country_controls()

    if is_admin:
        st.sidebar.markdown('<div class="admin-nav-title">🛠️ Administration</div>', unsafe_allow_html=True)

        if st.sidebar.button("📊 Dashboard global", width=UI_WIDTH_STRETCH):
            st.session_state["admin_view"] = ADMIN_VIEW_DASHBOARD
            st.session_state["admin_filter"] = "ALL"

        if st.sidebar.button("💰 Récapitulatif paiement", width=UI_WIDTH_STRETCH):
            st.session_state["admin_view"] = ADMIN_VIEW_PAYMENT_SUMMARY
            st.session_state["admin_filter"] = "ALL"

        if st.sidebar.button("🧾 Preuves de paiement", width=UI_WIDTH_STRETCH):
            st.session_state["admin_view"] = ADMIN_VIEW_PAYMENT_PROOFS
            st.session_state["admin_filter"] = "ALL"

        if st.sidebar.button("🚚 Commandes en cours", width=UI_WIDTH_STRETCH):
            st.session_state["admin_view"] = ADMIN_VIEW_IN_PROGRESS
            st.session_state["admin_filter"] = "EN_COURS"

        if st.sidebar.button("❌ Commandes annulées", width=UI_WIDTH_STRETCH):
            st.session_state["admin_view"] = ADMIN_VIEW_CANCELLED
            st.session_state["admin_filter"] = "ANNULEE"

        if st.sidebar.button("🕓 Historique client", width=UI_WIDTH_STRETCH):
            st.session_state["admin_view"] = ADMIN_VIEW_HISTORY
            st.session_state["admin_filter"] = "ALL"

        if st.sidebar.button("💸 Remboursements", width=UI_WIDTH_STRETCH):
            st.session_state["admin_view"] = ADMIN_VIEW_REFUNDS
            st.session_state["admin_filter"] = "ALL"

        return

    st.sidebar.subheader(tr("sidebar_account"))

    if user:
        st.sidebar.success(tr("sidebar_connected"))
        st.sidebar.write(clean_text(user.get("name") or "-"))
        st.sidebar.write(clean_text(user.get("phone") or "-"))
    else:
        st.sidebar.info(tr("sidebar_not_connected"))

    effective_plan = get_effective_user_plan(user)
    free_left = get_free_orders_remaining(user)
    plan_key = f"plan_{effective_plan.lower()}"
    plan_label = tr(plan_key) if plan_key in TRANSLATIONS[get_language()] else effective_plan

    st.sidebar.markdown(
        f"""
        <div class="af-card">
            <div style="font-size:0.9rem;color:#475569;">{tr('sidebar_plan')}</div>
            <div style="font-size:1.1rem;font-weight:700;">{plan_label}</div>
            <div class="af-small">{tr('sidebar_free_left')}: {free_left if effective_plan == PLAN_FREE else '∞'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if user and get_base_user_plan(user) == PLAN_PREMIUM_PLUS and not is_premium_plus_active(user):
        st.sidebar.warning(tr("plan_pending_note"))

    should_show_offers_button = bool(
        not user
        or effective_plan == PLAN_FREE
        or (get_base_user_plan(user) == PLAN_PREMIUM_PLUS and not is_premium_plus_active(user))
    )

    if should_show_offers_button:
        if st.sidebar.button(tr("sidebar_upgrade"), width=UI_WIDTH_STRETCH):
            st.session_state["premium_page_open"] = True

    if user:
        if st.sidebar.button(tr("sidebar_logout"), width=UI_WIDTH_STRETCH):
            try:
                logout_user()
            except TypeError:
                try:
                    logout_user(st.session_state)
                except Exception:
                    pass
            except Exception:
                pass

            try:
                logout_admin()
            except Exception:
                pass

            for key in [
                "user_id",
                "client_phone",
                "client_name",
                "client_email",
                "last_order_code",
                "selected_order_plan",
                "selected_order_plan_manual",
            ]:
                st.session_state.pop(key, None)

            st.rerun()


def render_account_box(user: dict | None) -> dict | None:
    if user:
        return user

    apply_login_form_reset_if_needed()

    st.markdown(f"### {tr('account_title')}")
    st.info(tr("account_intro"))

    send_otp_label = "Envoyer OTP" if get_language() == "fr" else "Send OTP"
    enter_otp_label = "Code OTP" if get_language() == "fr" else "OTP code"
    otp_placeholder = "Entrez le code OTP reçu" if get_language() == "fr" else "Enter the OTP code"
    otp_success_text = "OTP généré avec succès." if get_language() == "fr" else "OTP generated successfully."
    ask_otp_first_text = "Veuillez d'abord demander un OTP." if get_language() == "fr" else "Please request an OTP first."
    otp_incorrect_text = "Code OTP incorrect." if get_language() == "fr" else "Incorrect OTP code."
    otp_wait_text = (
        "Veuillez attendre encore {seconds} seconde(s) avant une nouvelle demande."
        if get_language() == "fr"
        else "Please wait {seconds} more second(s) before requesting another OTP."
    )
    otp_limit_text = (
        "Trop de demandes OTP. Réessayez dans {minutes} minute(s)."
        if get_language() == "fr"
        else "Too many OTP requests. Try again in {minutes} minute(s)."
    )
    enter_phone_text = "Veuillez entrer votre numéro de téléphone." if get_language() == "fr" else "Please enter your phone number."
    otp_linked_text = (
        "Le code OTP affiché ci-dessous est lié au numéro saisi."
        if get_language() == "fr"
        else "The OTP code shown below is linked to the entered phone number."
    )

    default_phone = str(st.session_state.get("otp_phone", "") or "")
    if "login_phone_input" not in st.session_state:
        st.session_state["login_phone_input"] = default_phone
    elif default_phone and not str(st.session_state.get("login_phone_input", "")).strip():
        st.session_state["login_phone_input"] = default_phone

    phone = st.text_input(
        tr("phone"),
        key="login_phone_input",
        placeholder="+2376...",
    )

    render_test_otp_panel(current_phone=phone)
    st.caption(otp_linked_text)

    captcha_input = render_captcha_block("login", title=tr("captcha_title"), allow_refresh=True)

    if st.button(send_otp_label, width=UI_WIDTH_STRETCH, key="login_send_otp"):
        current_phone_value = normalize_phone(st.session_state.get("login_phone_input", "") or "")

        if not current_phone_value:
            st.error(enter_phone_text)
            return None

        captcha_status = get_captcha_status("login", captcha_input)

        if captcha_status == "empty":
            set_captcha_error("login", tr("captcha_required"))
            st.rerun()
            return None

        if captcha_status in {"invalid", "missing"}:
            set_captcha_error("login", tr("captcha_bad"))
            refresh_captcha("login")
            st.rerun()
            return None

        clear_captcha_error("login")

        otp_limit_status = get_otp_rate_limit_status(current_phone_value)

        if not otp_limit_status["allowed"]:
            if otp_limit_status["reason"] == "cooldown":
                st.error(otp_wait_text.format(seconds=otp_limit_status["wait_seconds"]))
                return None

            if otp_limit_status["reason"] == "window_limit":
                st.error(otp_limit_text.format(minutes=otp_limit_status["wait_minutes"]))
                return None

        otp = f"{secrets.randbelow(900000) + 100000}"

        st.session_state["otp_code"] = otp
        st.session_state["otp_phone"] = current_phone_value
        st.session_state["login_otp_input"] = ""

        record_otp_request(current_phone_value)

        st.success(otp_success_text)
        st.rerun()

    st.text_input(
        enter_otp_label,
        key="login_otp_input",
        placeholder=otp_placeholder,
    )
    st.text_input(
        tr("full_name"),
        key="login_name_input",
        value=clean_text(st.session_state.get("client_name", "")),
    )
    st.text_input(
        tr("email"),
        key="login_email_input",
        value=clean_text(st.session_state.get("client_email", "")),
    )

    if st.button(tr("continue_btn"), width=UI_WIDTH_STRETCH, key="login_continue"):
        stored_otp = str(st.session_state.get("otp_code", "") or "").strip()
        stored_phone = normalize_phone(st.session_state.get("otp_phone", "") or "")

        current_phone_value = normalize_phone(st.session_state.get("login_phone_input", "") or "")
        current_otp_value = str(st.session_state.get("login_otp_input", "") or "").strip()
        current_name_value = clean_text(st.session_state.get("login_name_input", "") or "")
        current_email_value = clean_text(st.session_state.get("login_email_input", "") or "")

        if not stored_otp or not stored_phone:
            st.error(ask_otp_first_text)
            return None

        if not current_phone_value:
            st.error(tr("login_error_phone"))
            return None

        if current_phone_value != stored_phone:
            mismatch_text = (
                "Le numéro utilisé pour la connexion doit être le même que celui utilisé pour demander l'OTP."
                if get_language() == "fr"
                else "The phone number used for login must be the same as the one used to request the OTP."
            )
            st.error(mismatch_text)
            return None

        if not current_otp_value:
            missing_otp_text = (
                "Veuillez entrer le code OTP."
                if get_language() == "fr"
                else "Please enter the OTP code."
            )
            st.error(missing_otp_text)
            return None

        if current_otp_value != stored_otp:
            st.error(otp_incorrect_text)
            return None

        user_id = upsert_user(
            current_phone_value,
            current_name_value,
            current_email_value,
        )
        set_connected_user(
            user_id,
            current_phone_value,
            current_name_value,
            current_email_value,
        )

        clear_captcha_error("login")
        refresh_captcha("login")
        clear_login_test_otp()
        request_login_form_reset()

        st.success(tr("login_success"))
        st.rerun()

    return get_current_user()


def render_plan_cards(user: dict | None) -> None:
    st.markdown(f"### {tr('plan_title')}")
    selected_plan = get_selected_order_plan(user)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="af-plan">
                <h4>{tr('plan_free')}</h4>
                <p class="af-small">{tr('plan_free_desc')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(get_plan_cta_label(PLAN_FREE), key="choose_plan_free", width=UI_WIDTH_STRETCH):
            set_selected_order_plan(PLAN_FREE)
            st.rerun()

    with col2:
        st.markdown(
            f"""
            <div class="af-plan">
                <h4>{tr('plan_premium')}</h4>
                <p class="af-small">{tr('plan_premium_desc')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(get_plan_cta_label(PLAN_PREMIUM), key="choose_plan_premium", width=UI_WIDTH_STRETCH):
            set_selected_order_plan(PLAN_PREMIUM)
            st.rerun()

    with col3:
        st.markdown(
            f"""
            <div class="af-plan">
                <h4>{tr('plan_premium_plus')}</h4>
                <p class="af-small">{tr('plan_premium_plus_desc')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(get_plan_cta_label(PLAN_PREMIUM_PLUS), key="choose_plan_premium_plus", width=UI_WIDTH_STRETCH):
            set_selected_order_plan(PLAN_PREMIUM_PLUS)
            st.rerun()

    if selected_plan:
        title, body = get_selected_plan_notice(selected_plan)
        if title and body:
            st.info(f"{title} — {body}")

    if user and get_base_user_plan(user) == PLAN_PREMIUM_PLUS and not is_premium_plus_active(user):
        st.warning(tr("plan_pending_note"))


def render_kpis(user: dict | None) -> None:
    effective_plan = get_effective_user_plan(user)
    plan_key = f"plan_{effective_plan.lower()}"
    plan_label = tr(plan_key) if plan_key in TRANSLATIONS[get_language()] else effective_plan
    left = get_free_orders_remaining(user)
    sub_status = clean_text((user or {}).get("subscription_status") or (user or {}).get("premium_plus_status") or "-")
    sub_end_date = clean_text((user or {}).get("subscription_end_date") or (user or {}).get("premium_plus_end_date") or "")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f'<div class="af-kpi"><div class="af-muted">{tr("sidebar_plan")}</div><div style="font-size:1.2rem;font-weight:700;">{plan_label}</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        value = left if effective_plan == PLAN_FREE else "∞"
        st.markdown(
            f'<div class="af-kpi"><div class="af-muted">{tr("sidebar_free_left")}</div><div style="font-size:1.2rem;font-weight:700;">{value}</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        detail = format_date_display(sub_end_date) if sub_end_date else (sub_status or "-")
        st.markdown(
            f'<div class="af-kpi"><div class="af-muted">{tr("subscription_status")}</div><div style="font-size:1.2rem;font-weight:700;">{detail}</div></div>',
            unsafe_allow_html=True,
        )


def render_upgrade_unavailable_notice() -> None:
    st.markdown(
        f"""
        <div class="af-warning-card">
            <h4>{tr('upgrade_unavailable_title')}</h4>
            <p>{tr('upgrade_unavailable_text')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upgrade_section(user: dict | None) -> None:
    st.markdown(f"### {tr('upgrade_title')}")

    country_code = get_user_country_code(user)
    whatsapp_number = get_best_whatsapp_number(country_code)
    if not whatsapp_number:
        render_upgrade_unavailable_notice()
        return

    st.info(tr("upgrade_intro"))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"#### {tr('plan_premium')}")
        st.write(tr("plan_premium_desc"))
        premium_message = build_upgrade_message(user, PLAN_PREMIUM)
        premium_url = build_whatsapp_url(whatsapp_number, premium_message)
        if premium_url:
            st.link_button(tr("premium_btn"), premium_url, width=UI_WIDTH_STRETCH)

    with col2:
        st.markdown(f"#### {tr('plan_premium_plus')}")
        duration = st.radio(
            tr("duration_label"),
            options=PLAN_DURATION_OPTIONS,
            index=0,
            horizontal=True,
            help=tr("duration_help"),
            key="premium_plus_duration",
        )
        price = get_premium_plus_price(duration)
        if price:
            st.write(f"**{price}**")
        st.write(tr("plan_premium_plus_desc"))
        premium_plus_message = build_upgrade_message(user, PLAN_PREMIUM_PLUS, duration)
        premium_plus_url = build_whatsapp_url(whatsapp_number, premium_plus_message)
        if premium_plus_url:
            st.link_button(tr("premium_plus_btn"), premium_plus_url, width=UI_WIDTH_STRETCH)

    st.caption(
        "Ces boutons servent aux instructions WhatsApp de souscription. La création de commande se fait via les boutons de formule au-dessus."
        if get_language() == "fr"
        else "These buttons are for WhatsApp subscription instructions. Order creation happens through the plan buttons above."
    )


def render_order_form(user: dict | None) -> None:
    st.markdown(f"### {tr('order_title')}")

    if not user:
        st.info(tr("account_intro"))
        return

    selected_plan = get_selected_order_plan(user)
    if not selected_plan:
        st.info(
            "Choisissez d'abord une formule FREE, PREMIUM ou PREMIUM_PLUS pour créer votre commande."
            if get_language() == "fr"
            else "Choose a FREE, PREMIUM or PREMIUM_PLUS option first to create your order."
        )
        return

    if selected_plan not in {PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        st.info(tr("account_intro"))
        return

    premium_plus_active = is_premium_plus_active(user)
    effective_selected_plan = (
        PLAN_PREMIUM if selected_plan == PLAN_PREMIUM_PLUS and not premium_plus_active else selected_plan
    )

    user_country = get_user_country_code(user)
    selected_user = dict(user or {})
    selected_user["plan"] = selected_plan

    title, body = get_selected_plan_notice(selected_plan)
    if title and body:
        st.markdown(
            f"""
            <div class="af-card">
                <div style="font-size:1rem;font-weight:800;margin-bottom:6px;">{title}</div>
                <div class="af-small">{body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if effective_selected_plan == PLAN_FREE and get_free_orders_remaining(user) <= 0:
        st.error(tr("free_block_limit"))
        return

    with st.form("create_order_form"):
        st.radio(
            tr("order_type"),
            options=[tr("order_type_product"), tr("order_type_service")],
            horizontal=True,
            key="order_type",
        )

        col1, col2 = st.columns(2)

        with col1:
            site_name = st.text_input(tr("site_name"))
            product_url = st.text_input(tr("product_url"))
            product_title = st.text_input(tr("product_title"))
            merchant_total_eur = st.number_input(
                tr("merchant_total_eur"),
                min_value=0.0,
                step=1.0,
                format="%.2f",
            )
            payment_method = st.selectbox(
                tr("payment_method"),
                options=["MTN MoMo", "Orange Money"],
                index=0,
                key="payment_method_input",
            )

        with col2:
            product_specs = st.text_area(tr("product_specs"), height=120)
            forwarder_name = st.text_input(tr("forwarder_name"))
            delivery_address = st.text_area(tr("delivery_address"), height=90)

        estimated_xaf_preview = estimate_merchant_total_xaf(merchant_total_eur)

        if effective_selected_plan == PLAN_FREE:
            fee_preview_xaf = 0
        elif effective_selected_plan == PLAN_PREMIUM:
            fee_preview_xaf = _round_xaf(estimated_xaf_preview * 0.20)
        else:
            fee_preview_xaf = 0

        total_preview_xaf = estimated_xaf_preview + fee_preview_xaf

        st.caption(
            (
                f"Marchand : {format_eur(merchant_total_eur)} EUR ≈ {format_xaf(estimated_xaf_preview)} XAF"
                f" · Frais AfriPay : {format_xaf(fee_preview_xaf)} XAF"
                f" · Total estimé : {format_xaf(total_preview_xaf)} XAF"
            )
        )

        submitted = st.form_submit_button(tr("create_order"), width=UI_WIDTH_STRETCH)

    if not submitted:
        return

    if not clean_text(forwarder_name):
        st.error(
            "Le nom du transitaire / agent / agence est obligatoire pour créer une commande."
            if get_language() == "fr"
            else "The freight forwarder / agent / agency name is required."
        )
        return

    if not clean_text(delivery_address):
        st.error(
            "L'adresse du transitaire / agence de réception est obligatoire pour créer une commande."
            if get_language() == "fr"
            else "The freight forwarder / delivery address is required."
        )
        return

    estimated_xaf = estimate_merchant_total_xaf(merchant_total_eur)
    free_error = None
    if effective_selected_plan == PLAN_FREE:
        free_error = validate_free_order_rules(selected_user, estimated_xaf)

    if free_error == "FREE_LIMIT_REACHED":
        st.error(tr("free_block_limit"))
        return

    if free_error == "FREE_AMOUNT_LIMIT_EXCEEDED":
        st.error(
            f"{tr('free_block_amount')} "
            + (
                "Choisissez PREMIUM ou PREMIUM_PLUS pour continuer avec ce montant."
                if get_language() == "fr"
                else "Choose PREMIUM or PREMIUM_PLUS to continue with this amount."
            )
        )
        return

    sync_user_plan_for_selection(user, selected_plan)

    created_result = None
    last_error = None

    create_attempts = [
        {
            "user_id": int(user["id"]),
            "client_name": clean_text(user.get("name") or st.session_state.get("client_name", "")),
            "client_phone": clean_text(user.get("phone") or st.session_state.get("client_phone", "")),
            "client_email": clean_text(user.get("email") or st.session_state.get("client_email", "")),
            "site_name": clean_text(site_name),
            "product_url": clean_text(product_url),
            "product_title": clean_text(product_title),
            "product_specs": clean_text(product_specs),
            "product_price_eur": float(merchant_total_eur or 0),
            "shipping_estimate_eur": 0.0,
            "delivery_address": clean_text(delivery_address),
            "freight_forwarder_name": clean_text(forwarder_name),
            "freight_forwarder_address": clean_text(delivery_address),
            "payment_method": clean_text(payment_method),
            "country_code": user_country,
        },
        {
            "user_id": int(user["id"]),
            "client_name": clean_text(user.get("name") or st.session_state.get("client_name", "")),
            "client_phone": clean_text(user.get("phone") or st.session_state.get("client_phone", "")),
            "client_email": clean_text(user.get("email") or st.session_state.get("client_email", "")),
            "site_name": clean_text(site_name),
            "product_url": clean_text(product_url),
            "product_title": clean_text(product_title),
            "product_specs": clean_text(product_specs),
            "merchant_total_eur": float(merchant_total_eur or 0),
            "shipping_estimate_eur": 0.0,
            "delivery_address": clean_text(delivery_address),
            "freight_forwarder_name": clean_text(forwarder_name),
            "freight_forwarder_address": clean_text(delivery_address),
            "payment_method": clean_text(payment_method),
            "country_code": user_country,
        },
        {
            "user_id": int(user["id"]),
            "client_name": clean_text(user.get("name") or st.session_state.get("client_name", "")),
            "client_phone": clean_text(user.get("phone") or st.session_state.get("client_phone", "")),
            "client_email": clean_text(user.get("email") or st.session_state.get("client_email", "")),
            "site_name": clean_text(site_name),
            "product_url": clean_text(product_url),
            "product_title": clean_text(product_title),
            "product_specs": clean_text(product_specs),
            "product_price_eur": float(merchant_total_eur or 0),
            "shipping_estimate_eur": 0.0,
            "delivery_address": clean_text(delivery_address),
            "country_code": user_country,
        },
        {
            "user_id": int(user["id"]),
            "client_name": clean_text(user.get("name") or st.session_state.get("client_name", "")),
            "client_phone": clean_text(user.get("phone") or st.session_state.get("client_phone", "")),
            "client_email": clean_text(user.get("email") or st.session_state.get("client_email", "")),
            "site_name": clean_text(site_name),
            "product_url": clean_text(product_url),
            "product_title": clean_text(product_title),
            "product_specs": clean_text(product_specs),
            "merchant_total_eur": float(merchant_total_eur or 0),
            "shipping_estimate_eur": 0.0,
            "delivery_address": clean_text(delivery_address),
            "country_code": user_country,
        },
    ]

    for payload in create_attempts:
        try:
            created_result = create_order_for_user(**payload)
            last_error = None
            break
        except TypeError as exc:
            last_error = exc
            continue
        except Exception as exc:
            last_error = exc
            break

    if last_error is not None and created_result is None:
        st.error(str(last_error))
        return

    order = resolve_created_order(created_result)
    if order:
        st.session_state["last_order_code"] = clean_text(order.get("order_code"))
    else:
        st.session_state["last_order_code"] = clean_text(created_result)

    render_order_success(user, order or {"order_code": clean_text(created_result)})


def render_order_success(user: dict | None, order: dict | None) -> None:
    if not order:
        return

    st.success(tr("order_created"))
    st.markdown(f"#### {tr('order_summary')}")

    total_xaf = safe_int(order.get("total_xaf", 0))
    total_eur = xaf_to_eur(total_xaf)
    fee_xaf = safe_int(order.get("afripay_fee_xaf", 0))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(tr("order_code"), clean_text(order.get("order_code", "-")))
    with col2:
        st.metric(tr("order_total_xaf"), f"{format_xaf(total_xaf)} XAF")
        st.caption(f"≈ {format_eur(total_eur)} EUR")
    with col3:
        st.metric(tr("order_fee_xaf"), f"{format_xaf(fee_xaf)} XAF")
        st.caption(f"≈ {format_eur(xaf_to_eur(fee_xaf))} EUR")

    country_code = get_user_country_code(user)
    whatsapp_number = get_best_whatsapp_number(country_code)
    if not whatsapp_number:
        st.warning(tr("proof_unavailable_text"))
        return

    cart_message = build_cart_validation_message(user, order.get("site_name", ""), order.get("product_url", ""))
    proof_message = build_payment_proof_message(order, user)
    cart_url = build_whatsapp_url(whatsapp_number, cart_message)
    proof_url = build_whatsapp_url(whatsapp_number, proof_message)

    col1, col2 = st.columns(2)
    with col1:
        if cart_url:
            st.link_button(tr("send_cart_whatsapp"), cart_url, width=UI_WIDTH_STRETCH)
    with col2:
        if proof_url:
            st.link_button(tr("send_payment_proof"), proof_url, width=UI_WIDTH_STRETCH)

    st.caption(tr("proof_intro"))


def render_orders_table(user: dict | None) -> None:
    st.markdown(f"### {tr('recent_orders')}")

    if not user:
        st.info(tr("empty_orders"))
        return

    try:
        rows = get_recent_orders_for_user(int(user["id"]), limit=20)
    except Exception:
        rows = []

    if not rows:
        st.info(tr("empty_orders"))
        return

    for row in rows:
        order_status = clean_text(row.get("order_status") or row.get("status") or "CREEE").upper()
        payment_status = clean_text(row.get("payment_status") or "PENDING").upper()
        display_status = order_status if order_status else payment_status

        bg, fg = ORDER_STATUS_COLORS.get(display_status, ("#E2E8F0", "#334155"))
        created_at = format_date_display(row.get("created_at"))

        st.markdown(
            f"""
            <div class="af-card">
                <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
                    <div>
                        <div style="font-weight:700;">{clean_text(row.get('product_title') or row.get('site_name') or '-')}</div>
                        <div class="af-small">{clean_text(row.get('order_code') or '-')} · {created_at}</div>
                    </div>
                    <div>
                        <span class="af-badge" style="background:{bg};color:{fg};">{display_status}</span>
                    </div>
                </div>
                <div style="margin-top:10px;" class="af-small">
                    {clean_text(row.get('site_name') or '')} · {format_dual_amount(row.get('total_xaf', 0))} · Paiement : {payment_status}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_flow_block() -> None:
    st.markdown(f"### {tr('payment_flow_title')}")
    st.info(tr("payment_flow_text"))


# =========================================================
# ADMIN HELPERS / VIEWS
# =========================================================
def render_admin_order_card(row: dict) -> None:
    order_code = clean_text(row.get("order_code"))
    status = clean_text(row.get("order_status") or "CREEE").upper()
    payment_status = clean_text(row.get("payment_status") or "PENDING").upper()
    refund_status = get_refund_status(row)

    bg, _fg = ORDER_STATUS_COLORS.get(status, ("#1E293B", "#E2E8F0"))

    total_xaf = safe_int(row.get("total_xaf", 0))
    refund_amount_xaf = safe_int(row.get("refund_amount_xaf", 0))

    refund_amount_display = ""
    if refund_amount_xaf > 0:
        refund_amount_display = f" · Remboursement : {format_dual_amount(refund_amount_xaf)}"

    proof_sent_at = format_datetime_display(row.get("payment_proof_sent_at"))
    proof_received_at = format_datetime_display(row.get("payment_proof_received_at"))

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(145deg, #1E293B, #0F172A);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.35);
        ">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:1.05rem;font-weight:700;color:#F8FAFC;">
                        {clean_text(row.get("product_title") or row.get("site_name") or "-")}
                    </div>
                    <div style="color:#CBD5E1;font-size:0.92rem;">
                        {clean_text(row.get("order_code") or "-")} · {clean_text(row.get("client_name") or "-")} · {clean_text(row.get("client_phone") or "-")}
                    </div>
                    <div style="color:#94A3B8;font-size:0.9rem;margin-top:6px;">
                        Marchand : {clean_text(row.get("site_name") or "-")} · Montant : {format_dual_amount(total_xaf)}
                    </div>
                    <div style="color:#94A3B8;font-size:0.88rem;margin-top:4px;">
                        Paiement : {payment_status} · Preuve envoyée : {proof_sent_at} · Preuve reçue : {proof_received_at}
                    </div>
                    <div style="color:#94A3B8;font-size:0.88rem;margin-top:4px;">
                        Refund : {refund_status}{refund_amount_display}
                    </div>
                </div>
                <div>
                    <span style="
                        display:inline-block;
                        background:{bg};
                        color:#FFFFFF;
                        border:1px solid rgba(255,255,255,0.18);
                        border-radius:999px;
                        padding:8px 14px;
                        font-weight:800;
                        font-size:0.9rem;
                        min-width:110px;
                        text-align:center;
                        box-shadow:0 2px 8px rgba(0,0,0,0.25);
                    ">
                        {status}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    can_mark_proof_sent = payment_status == "PENDING"
    can_mark_proof_received = payment_status in {"PENDING", "PROOF_SENT"}
    can_confirm_payment_now = payment_status in {"PROOF_SENT", "PROOF_RECEIVED"}
    can_start_processing_now = payment_status == "CONFIRMED" and status in {"CREEE", "PAYEE"}
    can_deliver_now = status in {"EN_COURS", "PAYEE"}
    can_cancel_now = status in {"CREEE", "PAYEE", "EN_COURS"} and refund_status in {REFUND_STATUS_NONE, ""}
    can_start_refund_now = status == "ANNULEE" and payment_status == "CONFIRMED" and refund_status in {REFUND_STATUS_NONE, ""}
    can_mark_refund_processing = refund_status == REFUND_STATUS_PENDING
    can_mark_refund_completed = refund_status in {REFUND_STATUS_PENDING, REFUND_STATUS_PROCESSING}
    can_mark_refund_proof_sent = refund_status == REFUND_STATUS_COMPLETED
    can_mark_refund_confirmed = refund_status == REFUND_STATUS_PROOF_SENT

    show_box = any([
        can_mark_proof_sent,
        can_mark_proof_received,
        can_confirm_payment_now,
        can_start_processing_now,
        can_deliver_now,
        can_cancel_now,
        can_start_refund_now,
        can_mark_refund_processing,
        can_mark_refund_completed,
        can_mark_refund_proof_sent,
        can_mark_refund_confirmed,
    ])

    if show_box:
        st.markdown('<div class="admin-action-box">', unsafe_allow_html=True)

        action_cols1 = st.columns(4)

        with action_cols1[0]:
            if can_mark_proof_sent:
                if st.button("📤 Preuve envoyée", key=f"proof_sent_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = mark_payment_proof_sent_safe(
                        order_code,
                        admin_note="Preuve de paiement signalée comme envoyée",
                    )
                    if updated:
                        st.success(f"Preuve envoyée : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible de marquer PROOF_SENT.")

        with action_cols1[1]:
            if can_mark_proof_received:
                if st.button("📥 Preuve reçue", key=f"proof_received_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = mark_payment_proof_received_safe(
                        order_code,
                        admin_note="Preuve de paiement reçue par administrateur",
                    )
                    if updated:
                        st.success(f"Preuve reçue : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible de marquer PROOF_RECEIVED.")

        with action_cols1[2]:
            if can_confirm_payment_now:
                if st.button("✅ Confirmer paiement", key=f"confirm_payment_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = confirm_payment(
                        order_code,
                        admin_note="Paiement confirmé par administrateur",
                    )
                    if updated:
                        st.success(f"Paiement confirmé : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Action impossible ou déjà effectuée.")

        with action_cols1[3]:
            if can_cancel_now:
                if st.button("❌ Annuler", key=f"cancel_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = cancel_order_safe(
                        order_code,
                        admin_note="Commande annulée par administrateur",
                    )
                    if updated:
                        st.success(f"Commande annulée : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible d'annuler cette commande.")

        action_cols2 = st.columns(4)

        with action_cols2[0]:
            if can_start_processing_now:
                if st.button("🚚 Mettre en traitement", key=f"start_processing_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = start_order_processing(
                        order_code,
                        admin_note="Commande mise en traitement par administrateur",
                    )
                    if updated:
                        st.success(f"Commande en traitement : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Action impossible ou déjà effectuée.")

        with action_cols2[1]:
            if can_deliver_now:
                if st.button("📦 Marquer livrée", key=f"deliver_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = deliver_order(
                        order_code,
                        admin_note="Commande livrée par administrateur",
                    )
                    if updated:
                        st.success(f"Commande livrée : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Action impossible ou déjà effectuée.")

        with action_cols2[2]:
            if can_start_refund_now:
                default_refund_amount = safe_int(row.get("total_xaf", 0))
                if st.button("💸 Initier remboursement", key=f"start_refund_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = start_refund_db(
                        order_code=order_code,
                        refund_amount_xaf=default_refund_amount,
                        refund_reason="Remboursement initié par administrateur",
                    )
                    if updated:
                        st.success(f"Remboursement initié : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible d'initier le remboursement. Vérifie les colonnes refund_* en base.")

        with action_cols2[3]:
            if can_mark_refund_processing:
                if st.button("🔄 Remboursement en cours", key=f"refund_processing_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = mark_refund_processing_db(order_code)
                    if updated:
                        st.success(f"Remboursement en cours : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible de passer à PROCESSING.")

        action_cols3 = st.columns(3)

        with action_cols3[0]:
            if can_mark_refund_completed:
                if st.button("💰 Remboursé", key=f"refund_completed_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = mark_refund_completed_db(order_code)
                    if updated:
                        st.success(f"Remboursement effectué : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible de marquer le remboursement comme effectué.")

        with action_cols3[1]:
            if can_mark_refund_proof_sent:
                if st.button("🧾 Preuve remboursement", key=f"refund_proof_sent_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = mark_refund_proof_sent_db(order_code)
                    if updated:
                        st.success(f"Preuve de remboursement envoyée : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible de marquer la preuve de remboursement.")

        with action_cols3[2]:
            if can_mark_refund_confirmed:
                if st.button("✅ Remboursement confirmé", key=f"refund_confirmed_{order_code}", width=UI_WIDTH_STRETCH):
                    updated = mark_refund_confirmed_db(order_code)
                    if updated:
                        st.success(f"Remboursement confirmé : {order_code}")
                        st.rerun()
                    else:
                        st.warning("Impossible de confirmer le remboursement.")

        st.markdown("</div>", unsafe_allow_html=True)


def render_admin_dashboard() -> None:
    st.markdown("## 🛠️ Dashboard Administrateur")

    kpis = get_admin_kpi_data()

    top1, top2, top3, top4, top5 = st.columns(5)
    with top1:
        st.metric("Total commandes", kpis["total_orders"])
    with top2:
        st.metric("Payées", kpis["total_paid"])
    with top3:
        st.metric("En cours", kpis["total_in_progress"])
    with top4:
        st.metric("Livrées", kpis["total_delivered"])
    with top5:
        st.metric("Annulées", kpis["total_cancelled"])

    st.markdown("### KPIs financiers")
    fin1, fin2, fin3, fin4 = st.columns(4)
    with fin1:
        st.metric("GMV jour", f"{format_xaf(kpis['gmv_today_xaf'])} XAF")
        st.caption(f"≈ {format_eur(kpis['gmv_today_eur'])} EUR")
    with fin2:
        st.metric("GMV semaine", f"{format_xaf(kpis['gmv_week_xaf'])} XAF")
        st.caption(f"≈ {format_eur(kpis['gmv_week_eur'])} EUR")
    with fin3:
        st.metric("Commissions AfriPay", f"{format_xaf(kpis['total_commissions_xaf'])} XAF")
        st.caption(f"≈ {format_eur(kpis['total_commissions_eur'])} EUR")
    with fin4:
        st.metric("Remboursements totalisés", f"{format_xaf(kpis['total_refunds_xaf'])} XAF")
        st.caption(f"≈ {format_eur(kpis['total_refunds_eur'])} EUR")

    st.markdown("### Volume global")
    st.metric("Volume total", f"{format_xaf(kpis['total_volume_xaf'])} XAF")
    st.caption(f"≈ {format_eur(kpis['total_volume_eur'])} EUR")

    st.markdown("### Commandes récentes")
    rows = get_all_orders(limit=20)

    if not rows:
        st.info("Aucune commande trouvée.")
        return

    for row in rows:
        render_admin_order_card(row)


def render_admin_payment_summary() -> None:
    st.markdown("## 💰 Récapitulatif paiement")

    rows = get_all_orders(limit=200)
    if not rows:
        st.info("Aucune commande trouvée.")
        return

    payment_counter = Counter()
    total_confirmed_xaf = 0
    total_pending_xaf = 0
    total_rejected_xaf = 0
    total_proof_waiting_xaf = 0

    for row in rows:
        payment_status = clean_text(row.get("payment_status") or "PENDING").upper()
        payment_counter[payment_status] += 1

        amount = safe_int(row.get("total_xaf", 0))

        if payment_status == "CONFIRMED":
            total_confirmed_xaf += amount
        elif payment_status in {"PENDING", "PROOF_SENT", "PROOF_RECEIVED"}:
            total_pending_xaf += amount
        elif payment_status == "REJECTED":
            total_rejected_xaf += amount

        if payment_status in {"PROOF_SENT", "PROOF_RECEIVED"}:
            total_proof_waiting_xaf += amount

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Paiements confirmés", payment_counter.get("CONFIRMED", 0))
        st.caption(format_dual_amount(total_confirmed_xaf))
    with col2:
        st.metric(
            "Paiements en attente",
            payment_counter.get("PENDING", 0) + payment_counter.get("PROOF_SENT", 0) + payment_counter.get("PROOF_RECEIVED", 0),
        )
        st.caption(format_dual_amount(total_pending_xaf))
    with col3:
        st.metric("Paiements rejetés", payment_counter.get("REJECTED", 0))
        st.caption(format_dual_amount(total_rejected_xaf))
    with col4:
        waiting_count = payment_counter.get("PROOF_SENT", 0) + payment_counter.get("PROOF_RECEIVED", 0)
        st.metric("Preuves à traiter", waiting_count)
        st.caption(format_dual_amount(total_proof_waiting_xaf))

    st.markdown("### Statuts de paiement")
    for status in ["PENDING", "PROOF_SENT", "PROOF_RECEIVED", "CONFIRMED", "REJECTED"]:
        count = payment_counter.get(status, 0)
        bg, fg = ORDER_STATUS_COLORS.get(status, ("#E2E8F0", "#334155"))
        st.markdown(
            f"""
            <div class="af-card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-weight:700;">{status}</div>
                    <span class="af-badge" style="background:{bg};color:{fg};">{count}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Commandes récentes liées aux paiements")
    filtered = []
    for row in rows:
        payment_status = clean_text(row.get("payment_status") or "PENDING").upper()
        if payment_status in {"PENDING", "PROOF_SENT", "PROOF_RECEIVED", "CONFIRMED", "REJECTED"}:
            filtered.append(row)

    for row in filtered[:20]:
        render_admin_order_card(row)


def render_admin_payment_proofs() -> None:
    st.markdown("## 🧾 Preuves de paiement")

    rows = get_all_orders(limit=200)
    filtered = [
        row for row in rows
        if clean_text(row.get("payment_status") or "PENDING").upper() in {"PENDING", "PROOF_SENT", "PROOF_RECEIVED"}
    ]

    if not filtered:
        st.info("Aucune preuve de paiement à traiter.")
        return

    proof_sent_count = 0
    proof_received_count = 0
    proof_waiting_amount = 0

    for row in filtered:
        payment_status = clean_text(row.get("payment_status") or "PENDING").upper()
        amount = safe_int(row.get("total_xaf", 0))
        if payment_status == "PROOF_SENT":
            proof_sent_count += 1
            proof_waiting_amount += amount
        elif payment_status == "PROOF_RECEIVED":
            proof_received_count += 1
            proof_waiting_amount += amount

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("PROOF_SENT", proof_sent_count)
    with col2:
        st.metric("PROOF_RECEIVED", proof_received_count)
    with col3:
        st.metric("Montant à traiter", f"{format_xaf(proof_waiting_amount)} XAF")
        st.caption(f"≈ {format_eur(xaf_to_eur(proof_waiting_amount))} EUR")

    for row in filtered:
        render_admin_order_card(row)


def render_admin_in_progress_orders() -> None:
    st.markdown("## 🚚 Commandes en cours")

    rows = get_all_orders(limit=100)
    filtered = [
        row for row in rows
        if clean_text(row.get("order_status") or "").upper() == "EN_COURS"
    ]

    if not filtered:
        st.info("Aucune commande en cours.")
        return

    for row in filtered:
        render_admin_order_card(row)


def render_admin_cancelled_orders() -> None:
    st.markdown("## ❌ Commandes annulées")

    rows = get_all_orders(limit=100)
    filtered = [
        row for row in rows
        if clean_text(row.get("order_status") or "").upper() == "ANNULEE"
    ]

    if not filtered:
        st.info("Aucune commande annulée.")
        return

    for row in filtered:
        render_admin_order_card(row)


def render_admin_history() -> None:
    st.markdown("## 🕓 Historique client")

    rows = get_all_orders(limit=200)
    if not rows:
        st.info("Aucune commande trouvée.")
        return

    grouped = defaultdict(list)
    for row in rows:
        client_key = clean_text(row.get("client_phone") or row.get("client_name") or "Client inconnu")
        grouped[client_key].append(row)

    for client_key, client_rows in grouped.items():
        total_client_xaf = sum(safe_int(r.get("total_xaf", 0)) for r in client_rows)
        confirmed_client_xaf = sum(
            safe_int(r.get("total_xaf", 0))
            for r in client_rows
            if clean_text(r.get("payment_status") or "").upper() == "CONFIRMED"
        )

        st.markdown(
            f"""
            <div class="af-card">
                <div style="font-weight:800;">{client_key}</div>
                <div class="af-small">
                    Commandes : {len(client_rows)} · Volume : {format_dual_amount(total_client_xaf)} · Confirmé : {format_dual_amount(confirmed_client_xaf)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for row in client_rows[:5]:
            status = clean_text(row.get("order_status") or "CREEE").upper()
            payment_status = clean_text(row.get("payment_status") or "PENDING").upper()
            refund_status = get_refund_status(row)
            created_at = format_date_display(row.get("created_at"))
            st.caption(
                f"{clean_text(row.get('order_code') or '-')} · {clean_text(row.get('product_title') or row.get('site_name') or '-')} · {status} · {payment_status} · Refund: {refund_status} · {created_at}"
            )


def render_admin_refunds() -> None:
    st.markdown("## 💸 Remboursements")

    rows = get_all_orders(limit=300)
    refund_rows = []
    for row in rows:
        refund_status = get_refund_status(row)
        order_status = clean_text(row.get("order_status") or "").upper()
        payment_status = clean_text(row.get("payment_status") or "").upper()
        if refund_status != REFUND_STATUS_NONE or (order_status == "ANNULEE" and payment_status == "CONFIRMED"):
            refund_rows.append(row)

    if not refund_rows:
        st.info("Aucun remboursement à traiter.")
        if not _column_exists("orders", "refund_status"):
            st.warning("Les colonnes refund_* ne semblent pas encore exister en base. La vue est prête, mais le pipeline DB doit être ajouté pour un fonctionnement complet.")
        return

    refund_counter = Counter()
    total_refund_amount = 0

    for row in refund_rows:
        refund_status = get_refund_status(row)
        refund_counter[refund_status] += 1
        refund_amount_xaf = safe_int(row.get("refund_amount_xaf", 0))
        if refund_status in {REFUND_STATUS_COMPLETED, REFUND_STATUS_PROOF_SENT, REFUND_STATUS_CONFIRMED}:
            total_refund_amount += refund_amount_xaf if refund_amount_xaf > 0 else safe_int(row.get("total_xaf", 0))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("À initier", refund_counter.get(REFUND_STATUS_NONE, 0))
    with col2:
        st.metric("En attente / cours", refund_counter.get(REFUND_STATUS_PENDING, 0) + refund_counter.get(REFUND_STATUS_PROCESSING, 0))
    with col3:
        st.metric("Preuves envoyées", refund_counter.get(REFUND_STATUS_PROOF_SENT, 0))
    with col4:
        st.metric("Montant remboursé", f"{format_xaf(total_refund_amount)} XAF")
        st.caption(f"≈ {format_eur(xaf_to_eur(total_refund_amount))} EUR")

    st.markdown("### Pipeline remboursement")
    for status in [
        REFUND_STATUS_NONE,
        REFUND_STATUS_PENDING,
        REFUND_STATUS_PROCESSING,
        REFUND_STATUS_COMPLETED,
        REFUND_STATUS_PROOF_SENT,
        REFUND_STATUS_CONFIRMED,
    ]:
        count = refund_counter.get(status, 0)
        bg, fg = ORDER_STATUS_COLORS.get(status, ("#475569", "#FFFFFF"))
        st.markdown(
            f"""
            <div class="af-card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-weight:700;">{status}</div>
                    <span class="af-badge" style="background:{bg};color:{fg};">{count}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Dossiers remboursement")
    for row in refund_rows[:50]:
        render_admin_order_card(row)


def render_admin_current_view() -> None:
    view = clean_text(st.session_state.get("admin_view", ADMIN_VIEW_DASHBOARD)).lower()

    if view == ADMIN_VIEW_PAYMENT_SUMMARY:
        render_admin_payment_summary()
        return

    if view == ADMIN_VIEW_PAYMENT_PROOFS:
        render_admin_payment_proofs()
        return

    if view == ADMIN_VIEW_IN_PROGRESS:
        render_admin_in_progress_orders()
        return

    if view == ADMIN_VIEW_CANCELLED:
        render_admin_cancelled_orders()
        return

    if view == ADMIN_VIEW_HISTORY:
        render_admin_history()
        return

    if view == ADMIN_VIEW_REFUNDS:
        render_admin_refunds()
        return

    render_admin_dashboard()


# =========================================================
# ADMIN UI / AUTH
# =========================================================
def inject_admin_dark_mode():
    st.markdown(
        """
    <style>
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {
        background: #0F172A !important;
        color: #E2E8F0 !important;
    }

    section[data-testid="stSidebar"] {
        background: #020B2D !important;
    }

    h1, h2, h3, h4, h5, h6,
    p, span, label {
        color: #E2E8F0 !important;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        background: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #1ABC9C, #16A085) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600;
    }

    [data-testid="stAlert"] {
        background: rgba(30, 41, 59, 0.95) !important;
        color: #E2E8F0 !important;
        border: 1px solid #334155 !important;
    }

    div[data-testid="column"] > div,
    div[data-testid="column"] > div > div,
    div[data-testid="column"] *,
    div[data-testid="stMetric"],
    div[data-testid="stMetric"] *,
    div[data-testid="stContainer"],
    div[data-testid="stContainer"] *,
    div[data-testid="stHorizontalBlock"] > div,
    div[data-testid="stHorizontalBlock"] > div * {
        background: transparent !important;
        color: #E2E8F0 !important;
    }

    div[data-testid="column"] > div,
    div[data-testid="stMetric"],
    div[data-testid="stContainer"],
    div[data-testid="stHorizontalBlock"] > div {
        background: linear-gradient(145deg, #1E293B, #0F172A) !important;
        border-radius: 16px !important;
        padding: 15px !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        box-shadow:
            0 4px 20px rgba(0,0,0,0.4),
            inset 0 1px 0 rgba(255,255,255,0.03) !important;
    }

    div[data-testid="column"] > div:hover {
        transform: translateY(-3px);
        transition: 0.2s ease;
    }

    div[data-testid="column"] > div,
    div[data-testid="stMetric"],
    div[data-testid="stContainer"],
    section[data-testid="stSidebar"] > div {
        backdrop-filter: blur(6px);
    }

    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
        background: linear-gradient(145deg, #1E293B, #0F172A) !important;
        border-radius: 14px !important;
        padding: 10px !important;
        border: 1px solid rgba(255,255,255,0.04) !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def verify_admin_password_local(password: str) -> bool:
    password = clean_text(password)
    if not password:
        return False

    if service_verify_admin_password is not None:
        try:
            return bool(service_verify_admin_password(password))
        except Exception:
            pass

    expected = get_admin_password_value()
    return bool(expected and password == expected)


def render_admin_login_box() -> None:
    st.markdown(f"### {tr('admin_login_title')}")

    with st.expander(tr("admin_login_title"), expanded=False):
        admin_password = st.text_input(
            tr("admin_password"),
            type="password",
            key="admin_password_input",
        )

        if st.button(
            tr("admin_login_button"),
            width=UI_WIDTH_STRETCH,
            key="admin_login_btn",
        ):
            if not clean_text(admin_password):
                st.error(
                    "Le mot de passe administrateur est obligatoire."
                    if get_language() == "fr"
                    else "Admin password is required."
                )
                return

            is_valid = verify_admin_password_local(admin_password)
            if not is_valid:
                st.error(
                    "Mot de passe administrateur incorrect."
                    if get_language() == "fr"
                    else "Invalid admin password."
                )
                return

            st.session_state["is_admin"] = True
            st.session_state["admin_view"] = ADMIN_VIEW_DASHBOARD
            st.session_state.pop("admin_password_input", None)

            st.success(
                "Connexion administrateur réussie."
                if get_language() == "fr"
                else "Admin login successful."
            )
            st.rerun()


def render_admin_logout():
    st.markdown("### 🔐 Session Administrateur")

    if st.button(tr("admin_logout"), width=UI_WIDTH_STRETCH):
        st.session_state["is_admin"] = False
        st.session_state["admin_view"] = ADMIN_VIEW_DASHBOARD
        st.session_state.pop("admin_password_input", None)
        st.success(
            "Déconnexion réussie."
            if get_language() == "fr"
            else "Logged out successfully."
        )
        st.rerun()


# =========================================================
# MAIN
# =========================================================
def main() -> None:
    try:
        ensure_defaults()
    except Exception:
        pass

    ensure_app_session()
    inject_css()

    user = get_current_user()

    if st.session_state.get("is_admin"):
        inject_admin_dark_mode()
        render_sidebar(None)
        render_admin_logout()
        render_admin_current_view()
        return

    render_sidebar(user)
    render_hero()

    user = render_account_box(user) or get_current_user()

    render_kpis(user)
    render_plan_cards(user)
    render_flow_block()
    render_admin_login_box()

    show_upgrade = bool(st.session_state.get("premium_page_open", False))
    if show_upgrade:
        render_upgrade_section(user)

    render_order_form(user)
    render_orders_table(user)

if __name__ == "__main__":
    init_db()
    main()   
