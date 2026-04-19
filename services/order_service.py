from datetime import datetime
import secrets

from data.database import get_cursor
from services.admin_service import get_setting, DEFAULT_EUR_XAF_RATE
from services.user_service import get_user_by_id, increment_free_orders_used


DEFAULT_SELLER_FEE_XAF = 0
DEFAULT_AFRIPAY_FEE_XAF = 0

FREE_ORDER_LIMIT = 2
FREE_MAX_TOTAL_XAF = 50000

PLAN_FREE = "FREE"
PLAN_PREMIUM = "PREMIUM"
PLAN_PREMIUM_PLUS = "PREMIUM_PLUS"

PREMIUM_PLUS_ALLOWED_DURATIONS = {"6M", "12M"}

REFUND_STATUS_NONE = "NONE"
REFUND_STATUS_PENDING = "PENDING"
REFUND_STATUS_PROCESSING = "PROCESSING"
REFUND_STATUS_COMPLETED = "COMPLETED"
REFUND_STATUS_PROOF_SENT = "PROOF_SENT"
REFUND_STATUS_CONFIRMED = "CONFIRMED"

REFUND_STATUS_OPTIONS = [
    REFUND_STATUS_NONE,
    REFUND_STATUS_PENDING,
    REFUND_STATUS_PROCESSING,
    REFUND_STATUS_COMPLETED,
    REFUND_STATUS_PROOF_SENT,
    REFUND_STATUS_CONFIRMED,
]


# ===============================
# STATUTS OFFICIELS AFRIPAY
# ===============================
ORDER_STATUS_CREATED = "CREEE"
ORDER_STATUS_PAID = "PAYEE"
ORDER_STATUS_IN_PROGRESS = "EN_COURS"
ORDER_STATUS_DELIVERED = "LIVREE"
ORDER_STATUS_CANCELLED = "ANNULEE"

ORDER_STATUS_OPTIONS = [
    ORDER_STATUS_CREATED,
    ORDER_STATUS_PAID,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_CANCELLED,
]

ORDER_STATUS_LABELS = {
    ORDER_STATUS_CREATED: "Créée",
    ORDER_STATUS_PAID: "Payée",
    ORDER_STATUS_IN_PROGRESS: "En cours",
    ORDER_STATUS_DELIVERED: "Livrée",
    ORDER_STATUS_CANCELLED: "Annulée",
}


# ===============================
# STATUTS DE PAIEMENT FINTECH
# ===============================
PAYMENT_STATUS_PENDING = "PENDING"
PAYMENT_STATUS_PROOF_SENT = "PROOF_SENT"
PAYMENT_STATUS_PROOF_RECEIVED = "PROOF_RECEIVED"
PAYMENT_STATUS_CONFIRMED = "CONFIRMED"
PAYMENT_STATUS_REJECTED = "REJECTED"

PAYMENT_STATUS_OPTIONS = [
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_PROOF_SENT,
    PAYMENT_STATUS_PROOF_RECEIVED,
    PAYMENT_STATUS_CONFIRMED,
    PAYMENT_STATUS_REJECTED,
]

PAYMENT_STATUS_LABELS = {
    PAYMENT_STATUS_PENDING: "En attente de paiement",
    PAYMENT_STATUS_PROOF_SENT: "Preuve en cours d'envoi",
    PAYMENT_STATUS_PROOF_RECEIVED: "Preuve reçue - vérification en cours",
    PAYMENT_STATUS_CONFIRMED: "Paiement confirmé",
    PAYMENT_STATUS_REJECTED: "Paiement rejeté",
}


# ===============================
# STATUTS MARCHAND / TRACKING
# ===============================
MERCHANT_STATUS_ORDER_PLACED = "Commande passée"
MERCHANT_STATUS_PAYMENT_DONE = "Paiement effectué"
MERCHANT_STATUS_CONFIRMED = "Confirmée par le marchand"
MERCHANT_STATUS_PREPARING = "En préparation"
MERCHANT_STATUS_SHIPPED = "Expédiée"
MERCHANT_STATUS_IN_TRANSIT = "En transit"
MERCHANT_STATUS_DELIVERED_FORWARDER = "Livrée au transitaire"
MERCHANT_STATUS_CANCELLED = "Annulée"

MERCHANT_STATUS_OPTIONS = [
    "",
    MERCHANT_STATUS_ORDER_PLACED,
    MERCHANT_STATUS_PAYMENT_DONE,
    MERCHANT_STATUS_CONFIRMED,
    MERCHANT_STATUS_PREPARING,
    MERCHANT_STATUS_SHIPPED,
    MERCHANT_STATUS_IN_TRANSIT,
    MERCHANT_STATUS_DELIVERED_FORWARDER,
    MERCHANT_STATUS_CANCELLED,
]


# ===============================
# SATISFACTION CLIENT (préparation)
# ===============================
MIN_CUSTOMER_RATING = 1
MAX_CUSTOMER_RATING = 5


# ===============================
# GÉNÉRER UN CODE DE COMMANDE
# ===============================
def generate_order_code():
    """
    Génère un code commande robuste.
    Exemple : CMD-2026-482731
    """
    year = datetime.utcnow().year
    rand = secrets.randbelow(900000) + 100000
    return f"CMD-{year}-{rand}"


# ===============================
# HELPERS
# ===============================
def _to_float(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _clean_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def _clean_optional_text(value):
    cleaned = _clean_text(value, "")
    return cleaned if cleaned else None


def _round_xaf(value):
    """
    Arrondi au multiple de 5 le plus proche.
    Exemples :
    13801 -> 13800
    13819 -> 13820
    13804.68 -> 13805
    """
    value = _to_float(value, 0.0)
    return int(round(value / 5.0) * 5)


def _parse_datetime(value):
    """
    Parse une date/heure depuis un datetime ou une chaîne ISO.
    Retourne None si la valeur est vide ou invalide.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _is_truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "oui",
        "active",
        "actif",
        "paid",
        "paye",
        "payé",
    }


def _get_user_plan(user):
    if not user:
        return PLAN_FREE
    return _clean_text(user.get("plan"), PLAN_FREE).upper()


def _get_user_free_orders_used(user):
    if not user:
        return 0
    return _to_int(user.get("free_orders_used"), 0)


def _normalize_subscription_duration(value):
    """
    Normalise la durée d'abonnement PREMIUM_PLUS.

    Valeurs acceptées au final :
    - 6M
    - 12M
    """
    raw = _clean_text(value, "").upper().replace(" ", "")

    mapping = {
        "6M": "6M",
        "6MOIS": "6M",
        "6MONTHS": "6M",
        "6_MONTHS": "6M",
        "SEMESTRIEL": "6M",
        "SEMI_ANNUAL": "6M",
        "SEMIANNUAL": "6M",
        "12M": "12M",
        "12MOIS": "12M",
        "12MONTHS": "12M",
        "12_MONTHS": "12M",
        "ANNUEL": "12M",
        "ANNUAL": "12M",
        "YEARLY": "12M",
    }

    normalized = mapping.get(raw, raw)
    return normalized if normalized in PREMIUM_PLUS_ALLOWED_DURATIONS else None


def _is_subscription_paid(user):
    """
    Vérifie si le paiement PREMIUM_PLUS est réellement validé.
    """
    if not user:
        return False

    payment_flags = [
        user.get("subscription_paid"),
        user.get("premium_plus_paid"),
        user.get("is_subscription_paid"),
        user.get("premium_plus_payment_confirmed"),
        user.get("subscription_active"),
        user.get("premium_plus_active"),
    ]
    for flag in payment_flags:
        if _is_truthy(flag):
            return True

    payment_status = _clean_text(
        user.get("subscription_payment_status")
        or user.get("premium_plus_payment_status")
        or user.get("subscription_status")
        or user.get("premium_plus_status")
        or user.get("payment_status"),
        "",
    ).upper()

    return payment_status in {
        "PAID",
        "PAYE",
        "PAYÉ",
        "CONFIRMED",
        "CONFIRME",
        "CONFIRMÉ",
        "ACTIVE",
        "ACTIF",
    }


def _is_premium_plus_active(user):
    """
    Vérifie si PREMIUM_PLUS est réellement actif.

    Conditions strictes :
    - plan = PREMIUM_PLUS
    - paiement validé
    - durée autorisée = 6M ou 12M
    - start_date présente
    - end_date présente
    - now compris entre start_date et end_date
    """
    if not user:
        return False

    if _get_user_plan(user) != PLAN_PREMIUM_PLUS:
        return False

    duration = _normalize_subscription_duration(
        user.get("subscription_duration")
        or user.get("premium_plus_duration")
        or user.get("subscription_plan_duration")
        or user.get("premium_duration")
    )
    if duration is None:
        return False

    if not _is_subscription_paid(user):
        return False

    start_date = _parse_datetime(
        user.get("subscription_start_date")
        or user.get("premium_plus_start_date")
        or user.get("subscription_active_from")
        or user.get("premium_active_from")
    )
    end_date = _parse_datetime(
        user.get("subscription_end_date")
        or user.get("premium_plus_end_date")
        or user.get("subscription_active_until")
        or user.get("premium_active_until")
    )

    if start_date is None or end_date is None:
        return False

    now = datetime.utcnow()
    return start_date <= now <= end_date


def _compute_afripay_fee_xaf_for_plan(
    merchant_total_xaf: int,
    user_plan: str,
    premium_plus_active: bool = False,
) -> int:
    """
    Calcule les frais AfriPay selon le plan.

    Règles validées :
    - FREE         -> 0 XAF
    - PREMIUM      -> 20% du montant marchand
    - PREMIUM_PLUS -> 0 XAF seulement si actif
                      sinon comportement PREMIUM
    """
    merchant_total_xaf = int(merchant_total_xaf or 0)
    plan = _clean_text(user_plan, PLAN_FREE).upper()

    if merchant_total_xaf <= 0:
        return 0

    if plan == PLAN_FREE:
        return 0

    if plan == PLAN_PREMIUM:
        return _round_xaf(merchant_total_xaf * 0.20)

    if plan == PLAN_PREMIUM_PLUS:
        if premium_plus_active:
            return 0
        return _round_xaf(merchant_total_xaf * 0.20)

    return 0


def _build_locked_order_amounts(
    product_price_eur,
    shipping_estimate_eur,
    seller_fee_xaf,
    user_plan,
    premium_plus_active,
):
    """
    Construit les montants backend verrouillés de la commande.
    Aucun frais AfriPay ne doit être piloté depuis l'extérieur.
    """
    product_price_eur = _to_float(product_price_eur, 0.0)
    shipping_estimate_eur = _to_float(shipping_estimate_eur, 0.0)
    seller_fee_xaf = _round_xaf(seller_fee_xaf)

    total_to_pay_eur = product_price_eur + shipping_estimate_eur
    rate = get_eur_xaf_rate()

    merchant_total_xaf = _round_xaf(total_to_pay_eur * rate)
    afripay_fee_xaf = _compute_afripay_fee_xaf_for_plan(
        merchant_total_xaf=merchant_total_xaf,
        user_plan=user_plan,
        premium_plus_active=premium_plus_active,
    )
    total_xaf = _round_xaf(merchant_total_xaf + seller_fee_xaf + afripay_fee_xaf)

    return {
        "product_price_eur": product_price_eur,
        "shipping_estimate_eur": shipping_estimate_eur,
        "total_to_pay_eur": total_to_pay_eur,
        "eur_xaf_rate": rate,
        "merchant_total_xaf": merchant_total_xaf,
        "seller_fee_xaf": seller_fee_xaf,
        "afripay_fee_xaf": afripay_fee_xaf,
        "total_xaf": total_xaf,
    }


def _set_admin_note_sql():
    return """
        admin_note = CASE
            WHEN %s = '' THEN admin_note
            ELSE %s
        END,
        payment_admin_note = CASE
            WHEN %s = '' THEN payment_admin_note
            ELSE %s
        END
    """


def normalize_order_status(value, default=ORDER_STATUS_CREATED):
    cleaned = _clean_text(value, default).upper()
    return cleaned if cleaned in ORDER_STATUS_OPTIONS else default


def normalize_payment_status(value, default=PAYMENT_STATUS_PENDING):
    cleaned = _clean_text(value, default).upper()
    return cleaned if cleaned in PAYMENT_STATUS_OPTIONS else default


def normalize_merchant_status(value, default=""):
    cleaned = _clean_text(value, default)
    return cleaned if cleaned in MERCHANT_STATUS_OPTIONS else default


def normalize_refund_status(value, default=REFUND_STATUS_NONE):
    cleaned = _clean_text(value, default).upper()
    return cleaned if cleaned in REFUND_STATUS_OPTIONS else default


def get_order_status_label(status):
    normalized = normalize_order_status(status)
    return ORDER_STATUS_LABELS.get(normalized, normalized)


def get_payment_status_label(status):
    normalized = normalize_payment_status(status)
    return PAYMENT_STATUS_LABELS.get(normalized, normalized)


# ===============================
# BADGES VISUELS PRO
# ===============================
ORDER_STATUS_BADGE_STYLES = {
    ORDER_STATUS_CREATED: {
        "label": "Créée",
        "bg": "#EFF6FF",
        "text": "#1D4ED8",
        "border": "#BFDBFE",
    },
    ORDER_STATUS_PAID: {
        "label": "Payée",
        "bg": "#ECFDF5",
        "text": "#047857",
        "border": "#A7F3D0",
    },
    ORDER_STATUS_IN_PROGRESS: {
        "label": "En cours",
        "bg": "#FFFBEB",
        "text": "#B45309",
        "border": "#FDE68A",
    },
    ORDER_STATUS_DELIVERED: {
        "label": "Livrée",
        "bg": "#F0FDF4",
        "text": "#15803D",
        "border": "#BBF7D0",
    },
    ORDER_STATUS_CANCELLED: {
        "label": "Annulée",
        "bg": "#FEF2F2",
        "text": "#B91C1C",
        "border": "#FECACA",
    },
}


def get_order_status_badge_data(status):
    normalized = normalize_order_status(status)
    default_style = {
        "label": get_order_status_label(normalized),
        "bg": "#F3F4F6",
        "text": "#374151",
        "border": "#D1D5DB",
    }
    return ORDER_STATUS_BADGE_STYLES.get(normalized, default_style)


def render_order_status_badge(status):
    badge = get_order_status_badge_data(status)
    return (
        f"<span style='"
        f"display:inline-block;"
        f"padding:0.35rem 0.75rem;"
        f"border-radius:999px;"
        f"font-size:0.82rem;"
        f"font-weight:700;"
        f"line-height:1;"
        f"white-space:nowrap;"
        f"background:{badge['bg']};"
        f"color:{badge['text']};"
        f"border:1px solid {badge['border']};"
        f"'>"
        f"{badge['label']}"
        f"</span>"
    )


def is_valid_customer_rating(value):
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return False
    return MIN_CUSTOMER_RATING <= rating <= MAX_CUSTOMER_RATING


def can_request_customer_rating(order):
    """
    Une note ne doit être demandée qu'après livraison.
    """
    if not order:
        return False
    return normalize_order_status(order.get("order_status")) == ORDER_STATUS_DELIVERED


def build_promoter_whatsapp_message(order):
    """
    Prépare le futur message WhatsApp promoteur post-livraison.
    """
    if not order:
        return ""

    customer_name = _clean_text(
        order.get("client_name") or order.get("user_name"),
        "Cher client",
    )
    order_code = _clean_text(order.get("order_code"), "-")
    site_name = _clean_text(order.get("site_name"), "votre marchand")
    product_title = _clean_text(
        order.get("product_title") or order.get("product_name"),
        "votre commande",
    )

    return (
        f"Bonjour {customer_name},\n\n"
        f"Votre commande AfriPay Afrika {order_code} liée à {product_title} "
        f"chez {site_name} a été livrée.\n\n"
        f"Merci d’avoir utilisé AfriPay Afrika.\n"
        f"Comment évaluez-vous votre expérience sur une note de 1 à 5 étoiles ?\n\n"
        f"Votre avis nous aide à améliorer notre service."
    )


# ===============================
# TAUX ET CONVERSIONS
# ===============================
def get_eur_xaf_rate():
    rate = get_setting("eur_xaf_rate", DEFAULT_EUR_XAF_RATE)
    return _to_float(rate, float(DEFAULT_EUR_XAF_RATE))


def xaf_to_eur(value_xaf):
    rate = get_eur_xaf_rate()
    value_xaf = _to_float(value_xaf, 0.0)
    return value_xaf / rate if rate else 0.0


def calculate_order_amounts(
    product_price_eur,
    shipping_estimate_eur,
    seller_fee_xaf=DEFAULT_SELLER_FEE_XAF,
    afripay_fee_xaf=DEFAULT_AFRIPAY_FEE_XAF,
):
    """
    Calcule des montants génériques.
    La création de commande utilise cependant une logique backend verrouillée.
    """
    product_price_eur = _to_float(product_price_eur, 0.0)
    shipping_estimate_eur = _to_float(shipping_estimate_eur, 0.0)
    seller_fee_xaf = _round_xaf(seller_fee_xaf)
    afripay_fee_xaf = _round_xaf(afripay_fee_xaf)

    total_eur = product_price_eur + shipping_estimate_eur
    rate = get_eur_xaf_rate()

    merchant_total_xaf = _round_xaf(total_eur * rate)
    total_xaf = _round_xaf(merchant_total_xaf + seller_fee_xaf + afripay_fee_xaf)

    return {
        "product_price_eur": product_price_eur,
        "shipping_estimate_eur": shipping_estimate_eur,
        "total_to_pay_eur": total_eur,
        "eur_xaf_rate": rate,
        "seller_fee_xaf": seller_fee_xaf,
        "afripay_fee_xaf": afripay_fee_xaf,
        "merchant_total_xaf": merchant_total_xaf,
        "total_xaf": total_xaf,
    }


# ===============================
# CRÉATION DE COMMANDE
# ===============================
def create_order_for_user(
    user_id,
    client_name,
    client_phone,
    client_email,
    site_name,
    product_url,
    product_title,
    product_specs,
    product_price_eur,
    shipping_estimate_eur,
    delivery_address,
    momo_provider=None,
    merchant_total_amount=None,
    merchant_currency=None,
    country_code="CM",
    seller_fee_xaf=None,
    afripay_fee_xaf=None,
    total_xaf=None,
    total_to_pay_eur=None,
):
    """
    Crée une commande avec logique backend unique et verrouillée.

    Notes :
    - afripay_fee_xaf, total_xaf et total_to_pay_eur externes sont ignorés
      pour éviter toute incohérence.
    - les montants finaux sont recalculés côté backend.
    """
    _ = afripay_fee_xaf
    _ = total_xaf
    _ = total_to_pay_eur

    user = get_user_by_id(user_id)

    if not user:
        raise ValueError("Utilisateur introuvable. Veuillez vous reconnecter.")

    user_plan = _get_user_plan(user)
    free_orders_used = _get_user_free_orders_used(user)
    premium_plus_active = _is_premium_plus_active(user)

    clean_client_name = _clean_text(client_name)
    clean_client_phone = _clean_text(client_phone)
    clean_client_email = _clean_text(client_email)

    clean_site_name = _clean_text(site_name)
    clean_product_url = _clean_text(product_url)
    clean_product_title = _clean_text(product_title)
    clean_product_specs = _clean_text(product_specs)
    clean_delivery_address = _clean_text(delivery_address)
    clean_momo_provider = _clean_optional_text(momo_provider)
    clean_country_code = _clean_text(country_code or "CM", "CM").upper()
    clean_merchant_currency = _clean_text(merchant_currency or "EUR", "EUR").upper()

    effective_seller_fee_xaf = (
        _round_xaf(seller_fee_xaf)
        if seller_fee_xaf is not None
        else DEFAULT_SELLER_FEE_XAF
    )

    locked_amounts = _build_locked_order_amounts(
        product_price_eur=product_price_eur,
        shipping_estimate_eur=shipping_estimate_eur,
        seller_fee_xaf=effective_seller_fee_xaf,
        user_plan=user_plan,
        premium_plus_active=premium_plus_active,
    )

    final_total_to_pay_eur = locked_amounts["total_to_pay_eur"]
    final_seller_fee_xaf = locked_amounts["seller_fee_xaf"]
    final_afripay_fee_xaf = locked_amounts["afripay_fee_xaf"]
    final_total_xaf = locked_amounts["total_xaf"]
    merchant_total_xaf = locked_amounts["merchant_total_xaf"]

    if user_plan == PLAN_FREE:
        if free_orders_used >= FREE_ORDER_LIMIT:
            raise ValueError(
                "Limite FREE atteinte : 2 commandes maximum. Passez en Premium."
            )

        if merchant_total_xaf > FREE_MAX_TOTAL_XAF:
            raise ValueError(
                "Une commande FREE ne peut pas dépasser 50 000 XAF. Passez en Premium."
            )

    if merchant_total_amount is None:
        if clean_merchant_currency == "XAF":
            clean_merchant_total_amount = _to_float(merchant_total_xaf, 0.0)
        else:
            clean_merchant_total_amount = _to_float(final_total_to_pay_eur, 0.0)
    else:
        clean_merchant_total_amount = _to_float(merchant_total_amount, 0.0)

    order_code = generate_order_code()

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO orders (
                order_code,
                user_id,
                client_name,
                client_phone,
                client_email,
                country_code,
                site_name,
                product_title,
                product_name,
                product_specs,
                product_url,
                product_price_eur,
                shipping_estimate_eur,
                total_to_pay_eur,
                seller_fee_xaf,
                afripay_fee_xaf,
                total_xaf,
                delivery_address,
                momo_provider,
                payment_provider,
                merchant_total_amount,
                merchant_currency,
                order_status,
                payment_status,
                refund_status,
                refund_amount_xaf,
                refund_amount_eur,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            RETURNING order_code
            """,
            (
                order_code,
                int(user_id),
                clean_client_name,
                clean_client_phone,
                clean_client_email,
                clean_country_code,
                clean_site_name,
                clean_product_title,
                clean_product_title,
                clean_product_specs,
                clean_product_url,
                _to_float(product_price_eur, 0.0),
                _to_float(shipping_estimate_eur, 0.0),
                final_total_to_pay_eur,
                final_seller_fee_xaf,
                final_afripay_fee_xaf,
                final_total_xaf,
                clean_delivery_address,
                clean_momo_provider,
                clean_momo_provider,
                clean_merchant_total_amount,
                clean_merchant_currency,
                ORDER_STATUS_CREATED,
                PAYMENT_STATUS_PENDING,
                REFUND_STATUS_NONE,
                0,
                0.0,
            ),
        )
        row = cur.fetchone()

    if not row:
        raise ValueError("La commande n'a pas pu être créée.")

    if user_plan == PLAN_FREE:
        increment_free_orders_used(user_id)

    return row["order_code"]


# ===============================
# LECTURE COMMANDE PAR ID
# ===============================
def get_order_by_id(order_id):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM orders
            WHERE id = %s
            LIMIT 1
            """,
            (int(order_id),),
        )
        row = cur.fetchone()

    return row


# ===============================
# RECHERCHE COMMANDE PAR CODE
# ===============================
def get_order_by_code(order_code):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM orders
            WHERE order_code = %s
            LIMIT 1
            """,
            (_clean_text(order_code),),
        )
        row = cur.fetchone()

    return row


# ===============================
# LISTE COMMANDES UTILISATEUR
# ===============================
def list_orders_for_user(user_id):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (int(user_id),),
        )
        rows = cur.fetchall()

    return rows


# ===============================
# LISTE COMPLÈTE (ADMIN)
# ===============================
def list_orders_all():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                o.*,
                u.name AS user_name,
                u.phone AS user_phone,
                u.email AS user_email
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            """
        )
        rows = cur.fetchall()

    return rows


# ===============================
# MISE À JOUR INFOS MARCHAND (ADMIN)
# ===============================
def update_merchant_info(
    order_id,
    merchant_order_number="",
    merchant_confirmation_url="",
    merchant_tracking_url="",
    merchant_purchase_date="",
    merchant_status="",
    merchant_notes="",
):
    clean_purchase_date = _clean_optional_text(merchant_purchase_date)

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE orders
            SET
                merchant_order_number = %s,
                merchant_confirmation_url = %s,
                merchant_tracking_url = %s,
                merchant_purchase_date = %s,
                merchant_status = %s,
                merchant_notes = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                _clean_text(merchant_order_number),
                _clean_text(merchant_confirmation_url),
                _clean_text(merchant_tracking_url),
                clean_purchase_date,
                normalize_merchant_status(merchant_status),
                _clean_text(merchant_notes),
                int(order_id),
            ),
        )


# ===============================
# MISE À JOUR STATUT COMMANDE
# ===============================
def update_order_status(order_id, order_status=None, payment_status=None):
    fields = []
    values = []

    if order_status is not None:
        fields.append("order_status = %s")
        values.append(normalize_order_status(order_status))

    if payment_status is not None:
        fields.append("payment_status = %s")
        values.append(normalize_payment_status(payment_status))

    if not fields:
        return

    fields.append("updated_at = NOW()")
    values.append(int(order_id))

    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET {", ".join(fields)}
            WHERE id = %s
            """,
            tuple(values),
        )


# ===============================
# ACTIONS FINTECH SUR LE PAIEMENT
# ===============================
def mark_payment_proof_sent(order_code, provider=None, admin_note=""):
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                payment_status = %s,
                payment_provider = COALESCE(%s, payment_provider, momo_provider),
                proof_sent_at = NOW(),
                payment_proof_sent_at = NOW(),
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND payment_status = %s
            """,
            (
                PAYMENT_STATUS_PROOF_SENT,
                _clean_optional_text(provider),
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                PAYMENT_STATUS_PENDING,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def mark_payment_proof_received(order_code, admin_note=""):
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                payment_status = %s,
                proof_received_at = NOW(),
                payment_proof_received_at = NOW(),
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND payment_status IN (%s, %s)
            """,
            (
                PAYMENT_STATUS_PROOF_RECEIVED,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                PAYMENT_STATUS_PROOF_SENT,
                PAYMENT_STATUS_PENDING,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def confirm_payment(order_code, admin_note=""):
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                payment_status = %s,
                order_status = %s,
                payment_confirmed_at = NOW(),
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND payment_status IN (%s, %s)
            """,
            (
                PAYMENT_STATUS_CONFIRMED,
                ORDER_STATUS_PAID,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                PAYMENT_STATUS_PROOF_RECEIVED,
                PAYMENT_STATUS_PROOF_SENT,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def reject_payment(order_code, admin_note=""):
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                payment_status = %s,
                payment_rejected_at = NOW(),
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND payment_status IN (%s, %s, %s)
            """,
            (
                PAYMENT_STATUS_REJECTED,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                PAYMENT_STATUS_PENDING,
                PAYMENT_STATUS_PROOF_SENT,
                PAYMENT_STATUS_PROOF_RECEIVED,
            ),
        )
        updated = cur.rowcount > 0

    return updated


# ===============================
# ACTIONS FINTECH SUR LES COMMANDES
# ===============================
def start_order_processing(order_code, admin_note=""):
    """
    L'admin démarre le traitement uniquement après paiement confirmé.
    Résultat :
    - order_status = EN_COURS
    """
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                order_status = %s,
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND order_status IN (%s, %s)
              AND payment_status = %s
            """,
            (
                ORDER_STATUS_IN_PROGRESS,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                ORDER_STATUS_CREATED,
                ORDER_STATUS_PAID,
                PAYMENT_STATUS_CONFIRMED,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def deliver_order(order_code, admin_note=""):
    """
    L'admin marque la commande comme livrée.
    Résultat :
    - order_status = LIVREE
    """
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                order_status = %s,
                {_set_admin_note_sql()},
                delivered_at = NOW(),
                updated_at = NOW()
            WHERE order_code = %s
              AND order_status IN (%s, %s)
            """,
            (
                ORDER_STATUS_DELIVERED,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                ORDER_STATUS_IN_PROGRESS,
                ORDER_STATUS_PAID,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def cancel_order_by_user(order_code, user_id):
    """
    Le client peut annuler uniquement si :
    - il est propriétaire de la commande
    - order_status = CREEE
    - payment_status = PENDING
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE orders
            SET
                order_status = %s,
                updated_at = NOW()
            WHERE order_code = %s
              AND user_id = %s
              AND order_status = %s
              AND payment_status = %s
            """,
            (
                ORDER_STATUS_CANCELLED,
                _clean_text(order_code),
                int(user_id),
                ORDER_STATUS_CREATED,
                PAYMENT_STATUS_PENDING,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def cancel_order_by_admin(order_code, admin_note=""):
    """
    L'admin peut annuler une commande non déjà annulée.

    Règle :
    - order_status = ANNULEE
    - si payment_status est encore PENDING / PROOF_SENT / PROOF_RECEIVED,
      alors il passe à REJECTED
    - si payment_status est déjà CONFIRMED, on le laisse tel quel
      afin de permettre le pipeline remboursement
    """
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                order_status = %s,
                payment_status = CASE
                    WHEN payment_status IN (%s, %s, %s) THEN %s
                    ELSE payment_status
                END,
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND order_status <> %s
            """,
            (
                ORDER_STATUS_CANCELLED,
                PAYMENT_STATUS_PENDING,
                PAYMENT_STATUS_PROOF_SENT,
                PAYMENT_STATUS_PROOF_RECEIVED,
                PAYMENT_STATUS_REJECTED,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                ORDER_STATUS_CANCELLED,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def cancel_order(order_code, admin_note=""):
    """
    Alias de compatibilité utilisé par afripay_app_REBUILD.py
    """
    return cancel_order_by_admin(order_code, admin_note=admin_note)


# ===============================
# PIPELINE REMBOURSEMENT
# ===============================
def start_refund(order_code, refund_amount_xaf=None, refund_reason=""):
    """
    Initie un remboursement uniquement pour une commande :
    - annulée
    - avec paiement confirmé
    - sans remboursement déjà initié
    """
    order = get_order_by_code(order_code)
    if not order:
        return False

    if normalize_order_status(order.get("order_status")) != ORDER_STATUS_CANCELLED:
        return False

    if normalize_payment_status(order.get("payment_status")) != PAYMENT_STATUS_CONFIRMED:
        return False

    if normalize_refund_status(order.get("refund_status")) != REFUND_STATUS_NONE:
        return False

    base_total_xaf = _to_int(order.get("total_xaf"), 0)
    amount_xaf = _to_int(refund_amount_xaf, base_total_xaf)
    if amount_xaf <= 0:
        amount_xaf = base_total_xaf

    amount_eur = xaf_to_eur(amount_xaf)

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE orders
            SET
                refund_status = %s,
                refund_amount_xaf = %s,
                refund_amount_eur = %s,
                refund_reason = %s,
                refund_requested_at = NOW(),
                updated_at = NOW()
            WHERE order_code = %s
              AND order_status = %s
              AND payment_status = %s
              AND refund_status = %s
            """,
            (
                REFUND_STATUS_PENDING,
                amount_xaf,
                amount_eur,
                _clean_text(refund_reason),
                _clean_text(order_code),
                ORDER_STATUS_CANCELLED,
                PAYMENT_STATUS_CONFIRMED,
                REFUND_STATUS_NONE,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def mark_refund_processing(order_code, admin_note=""):
    """
    Passe le remboursement en cours de traitement.
    """
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                refund_status = %s,
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND refund_status = %s
            """,
            (
                REFUND_STATUS_PROCESSING,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                REFUND_STATUS_PENDING,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def mark_refund_completed(order_code, admin_note=""):
    """
    Marque le remboursement comme exécuté.
    """
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                refund_status = %s,
                refund_processed_at = NOW(),
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND refund_status IN (%s, %s)
            """,
            (
                REFUND_STATUS_COMPLETED,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                REFUND_STATUS_PENDING,
                REFUND_STATUS_PROCESSING,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def mark_refund_proof_sent(order_code, refund_proof_url="", admin_note=""):
    """
    Marque l'envoi de la preuve de remboursement.
    """
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                refund_status = %s,
                refund_proof_url = CASE
                    WHEN %s = '' THEN refund_proof_url
                    ELSE %s
                END,
                refund_proof_sent_at = NOW(),
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND refund_status = %s
            """,
            (
                REFUND_STATUS_PROOF_SENT,
                _clean_text(refund_proof_url),
                _clean_text(refund_proof_url),
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                REFUND_STATUS_COMPLETED,
            ),
        )
        updated = cur.rowcount > 0

    return updated


def mark_refund_confirmed(order_code, admin_note=""):
    """
    Confirmation finale du remboursement.
    """
    note = _clean_text(admin_note)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"""
            UPDATE orders
            SET
                refund_status = %s,
                refund_confirmed_at = NOW(),
                {_set_admin_note_sql()},
                updated_at = NOW()
            WHERE order_code = %s
              AND refund_status = %s
            """,
            (
                REFUND_STATUS_CONFIRMED,
                note,
                note,
                note,
                note,
                _clean_text(order_code),
                REFUND_STATUS_PROOF_SENT,
            ),
        )
        updated = cur.rowcount > 0

    return updated


# ===============================
# HELPERS DE TRANSITION MÉTIER
# ===============================
def can_user_cancel_order(order):
    """
    Retourne True si le client peut encore annuler lui-même la commande.
    """
    if not order:
        return False

    return (
        normalize_order_status(order.get("order_status")) == ORDER_STATUS_CREATED
        and normalize_payment_status(order.get("payment_status")) == PAYMENT_STATUS_PENDING
    )


def can_confirm_payment(order):
    """
    Paiement confirmable si une preuve a été envoyée ou reçue.
    """
    if not order:
        return False

    return normalize_payment_status(order.get("payment_status")) in {
        PAYMENT_STATUS_PROOF_SENT,
        PAYMENT_STATUS_PROOF_RECEIVED,
    }


def can_start_order_processing(order):
    """
    Traitement possible uniquement après paiement confirmé.
    """
    if not order:
        return False

    return (
        normalize_payment_status(order.get("payment_status")) == PAYMENT_STATUS_CONFIRMED
        and normalize_order_status(order.get("order_status")) in {
            ORDER_STATUS_CREATED,
            ORDER_STATUS_PAID,
        }
    )


def can_deliver_order(order):
    """
    Livraison possible si la commande est en cours
    ou déjà payée.
    """
    if not order:
        return False

    return normalize_order_status(order.get("order_status")) in {
        ORDER_STATUS_IN_PROGRESS,
        ORDER_STATUS_PAID,
    }


def can_admin_cancel_order(order):
    """
    L'admin peut annuler toute commande non déjà annulée.
    """
    if not order:
        return False

    return normalize_order_status(order.get("order_status")) != ORDER_STATUS_CANCELLED


def can_start_refund(order):
    """
    Remboursement possible uniquement si :
    - commande annulée
    - paiement confirmé
    - refund_status = NONE
    """
    if not order:
        return False

    return (
        normalize_order_status(order.get("order_status")) == ORDER_STATUS_CANCELLED
        and normalize_payment_status(order.get("payment_status")) == PAYMENT_STATUS_CONFIRMED
        and normalize_refund_status(order.get("refund_status")) == REFUND_STATUS_NONE
    )


def can_mark_refund_processing(order):
    if not order:
        return False
    return normalize_refund_status(order.get("refund_status")) == REFUND_STATUS_PENDING


def can_mark_refund_completed(order):
    if not order:
        return False
    return normalize_refund_status(order.get("refund_status")) in {
        REFUND_STATUS_PENDING,
        REFUND_STATUS_PROCESSING,
    }


def can_mark_refund_proof_sent(order):
    if not order:
        return False
    return normalize_refund_status(order.get("refund_status")) == REFUND_STATUS_COMPLETED


def can_mark_refund_confirmed(order):
    if not order:
        return False
    return normalize_refund_status(order.get("refund_status")) == REFUND_STATUS_PROOF_SENT
