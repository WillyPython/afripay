from datetime import datetime
import secrets

from data.database import get_conn
from services.admin_service import get_setting, DEFAULT_EUR_XAF_RATE


DEFAULT_SELLER_FEE_XAF = 0
DEFAULT_AFRIPAY_FEE_XAF = 0


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
    year = datetime.utcnow().year
    rand = secrets.randbelow(900) + 100
    return f"CMD-{year}-{rand}"


# ===============================
# HELPERS
# ===============================
def _to_float(value, default=0.0):
    try:
        return float(value or default)
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
    Arrondi au franc supérieur.
    Exemple :
    95939.01 -> 95940
    95939.00 -> 95939
    """
    value = _to_float(value, 0.0)
    integer = int(value)
    return integer if value == integer else integer + 1


def normalize_order_status(value, default=ORDER_STATUS_CREATED):
    cleaned = _clean_text(value, default).upper()
    return cleaned if cleaned in ORDER_STATUS_OPTIONS else default


def normalize_payment_status(value, default=PAYMENT_STATUS_PENDING):
    cleaned = _clean_text(value, default).upper()
    return cleaned if cleaned in PAYMENT_STATUS_OPTIONS else default


def normalize_merchant_status(value, default=""):
    cleaned = _clean_text(value, default)
    return cleaned if cleaned in MERCHANT_STATUS_OPTIONS else default


def get_order_status_label(status):
    normalized = normalize_order_status(status)
    return ORDER_STATUS_LABELS.get(normalized, normalized)


def get_payment_status_label(status):
    normalized = normalize_payment_status(status)
    return PAYMENT_STATUS_LABELS.get(normalized, normalized)


def is_valid_customer_rating(value):
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return False
    return MIN_CUSTOMER_RATING <= rating <= MAX_CUSTOMER_RATING


def can_request_customer_rating(order):
    """
    Prépare la future logique de satisfaction client.
    Une note ne doit être demandée qu'après livraison.
    """
    if not order:
        return False
    return normalize_order_status(order.get("order_status")) == ORDER_STATUS_DELIVERED


def build_promoter_whatsapp_message(order):
    """
    Prépare le futur message WhatsApp promoteur post-livraison.
    Ne modifie pas la base ; génère simplement le texte.
    """
    if not order:
        return ""

    customer_name = _clean_text(order.get("user_name"), "Cher client")
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
    Calcule tous les montants cohérents de la commande.
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
    conn = get_conn()
    cur = conn.cursor()

    order_code = generate_order_code()

    clean_site_name = _clean_text(site_name)
    clean_product_url = _clean_text(product_url)
    clean_product_title = _clean_text(product_title)
    clean_product_specs = _clean_text(product_specs)
    clean_delivery_address = _clean_text(delivery_address)
    clean_momo_provider = _clean_optional_text(momo_provider)
    clean_country_code = _clean_text(country_code or "CM", "CM").upper()

    clean_merchant_currency = _clean_text(merchant_currency or "EUR", "EUR").upper()

    base_amounts = calculate_order_amounts(
        product_price_eur=product_price_eur,
        shipping_estimate_eur=shipping_estimate_eur,
        seller_fee_xaf=seller_fee_xaf if seller_fee_xaf is not None else DEFAULT_SELLER_FEE_XAF,
        afripay_fee_xaf=afripay_fee_xaf if afripay_fee_xaf is not None else DEFAULT_AFRIPAY_FEE_XAF,
    )

    final_seller_fee_xaf = (
        _round_xaf(seller_fee_xaf)
        if seller_fee_xaf is not None
        else base_amounts["seller_fee_xaf"]
    )

    final_afripay_fee_xaf = (
        _round_xaf(afripay_fee_xaf)
        if afripay_fee_xaf is not None
        else base_amounts["afripay_fee_xaf"]
    )

    final_total_to_pay_eur = (
        _to_float(total_to_pay_eur, base_amounts["total_to_pay_eur"])
        if total_to_pay_eur is not None
        else base_amounts["total_to_pay_eur"]
    )

    final_total_xaf = (
        _round_xaf(total_xaf)
        if total_xaf is not None
        else _round_xaf(
            base_amounts["merchant_total_xaf"]
            + final_seller_fee_xaf
            + final_afripay_fee_xaf
        )
    )

    if merchant_total_amount is None:
        if clean_merchant_currency == "XAF":
            inferred_merchant_total_amount = base_amounts["merchant_total_xaf"]
        else:
            inferred_merchant_total_amount = _to_float(product_price_eur, 0.0) + _to_float(
                shipping_estimate_eur, 0.0
            )
        clean_merchant_total_amount = _to_float(inferred_merchant_total_amount, 0.0)
    else:
        clean_merchant_total_amount = _to_float(merchant_total_amount, 0.0)

    cur.execute(
        """
        INSERT INTO orders (
            order_code,
            user_id,
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
            merchant_total_amount,
            merchant_currency,
            order_status,
            payment_status,
            created_at,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, NOW(), NOW()
        )
        RETURNING order_code
        """,
        (
            order_code,
            int(user_id),
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
            clean_merchant_total_amount,
            clean_merchant_currency,
            ORDER_STATUS_CREATED,
            PAYMENT_STATUS_PENDING,
        ),
    )

    row = cur.fetchone()
    result = row["order_code"] if row else order_code

    conn.commit()
    cur.close()
    conn.close()

    return result


# ===============================
# LECTURE COMMANDE PAR ID
# ===============================
def get_order_by_id(order_id):
    conn = get_conn()
    cur = conn.cursor()

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

    cur.close()
    conn.close()

    return row


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
    conn = get_conn()
    cur = conn.cursor()

    clean_purchase_date = _clean_optional_text(merchant_purchase_date)

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

    conn.commit()
    cur.close()
    conn.close()


# ===============================
# LISTE COMMANDES UTILISATEUR
# ===============================
def list_orders_for_user(user_id):
    conn = get_conn()
    cur = conn.cursor()

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

    cur.close()
    conn.close()

    return rows


# ===============================
# RECHERCHE COMMANDE PAR CODE
# ===============================
def get_order_by_code(order_code):
    conn = get_conn()
    cur = conn.cursor()

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

    cur.close()
    conn.close()

    return row


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

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        f"""
        UPDATE orders
        SET {", ".join(fields)}
        WHERE id = %s
        """,
        tuple(values),
    )

    conn.commit()
    cur.close()
    conn.close()


# ===============================
# ACTIONS FINTECH SUR LE PAIEMENT
# ===============================
def mark_payment_proof_sent(order_code, provider=None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE orders
        SET
            payment_status = %s,
            payment_provider = COALESCE(%s, payment_provider, momo_provider),
            proof_sent_at = NOW(),
            updated_at = NOW()
        WHERE order_code = %s
          AND payment_status = %s
        """,
        (
            PAYMENT_STATUS_PROOF_SENT,
            _clean_optional_text(provider),
            _clean_text(order_code),
            PAYMENT_STATUS_PENDING,
        ),
    )

    updated = cur.rowcount > 0

    conn.commit()
    cur.close()
    conn.close()

    return updated


def mark_payment_proof_received(order_code, admin_note=""):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE orders
        SET
            payment_status = %s,
            proof_received_at = NOW(),
            payment_admin_note = %s,
            updated_at = NOW()
        WHERE order_code = %s
          AND payment_status IN (%s, %s)
        """,
        (
            PAYMENT_STATUS_PROOF_RECEIVED,
            _clean_text(admin_note),
            _clean_text(order_code),
            PAYMENT_STATUS_PROOF_SENT,
            PAYMENT_STATUS_PENDING,
        ),
    )

    updated = cur.rowcount > 0

    conn.commit()
    cur.close()
    conn.close()

    return updated


def confirm_payment(order_code, admin_note=""):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE orders
        SET
            payment_status = %s,
            payment_confirmed_at = NOW(),
            payment_admin_note = %s,
            updated_at = NOW()
        WHERE order_code = %s
          AND payment_status IN (%s, %s)
        """,
        (
            PAYMENT_STATUS_CONFIRMED,
            _clean_text(admin_note),
            _clean_text(order_code),
            PAYMENT_STATUS_PROOF_RECEIVED,
            PAYMENT_STATUS_PROOF_SENT,
        ),
    )

    updated = cur.rowcount > 0

    conn.commit()
    cur.close()
    conn.close()

    return updated


def reject_payment(order_code, admin_note=""):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE orders
        SET
            payment_status = %s,
            payment_rejected_at = NOW(),
            payment_admin_note = %s,
            updated_at = NOW()
        WHERE order_code = %s
          AND payment_status IN (%s, %s, %s)
        """,
        (
            PAYMENT_STATUS_REJECTED,
            _clean_text(admin_note),
            _clean_text(order_code),
            PAYMENT_STATUS_PENDING,
            PAYMENT_STATUS_PROOF_SENT,
            PAYMENT_STATUS_PROOF_RECEIVED,
        ),
    )

    updated = cur.rowcount > 0

    conn.commit()
    cur.close()
    conn.close()

    return updated


# ===============================
# LISTE COMPLÈTE (ADMIN)
# ===============================
def list_orders_all():
    conn = get_conn()
    cur = conn.cursor()

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

    cur.close()
    conn.close()

    return rows