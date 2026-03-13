from datetime import datetime
import secrets

from data.database import get_conn
from services.admin_service import get_setting, DEFAULT_EUR_XAF_RATE


DEFAULT_SELLER_FEE_XAF = 0
DEFAULT_AFRIPAY_FEE_XAF = 0


# -------------------------------
# Générer un code de commande
# -------------------------------
def generate_order_code():
    year = datetime.utcnow().year
    rand = secrets.randbelow(900) + 100
    return f"CMD-{year}-{rand}"


# -------------------------------
# Helpers calcul
# -------------------------------
def _to_float(value, default=0.0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return float(default)


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


def get_eur_xaf_rate():
    rate = get_setting("eur_xaf_rate", DEFAULT_EUR_XAF_RATE)
    return _to_float(rate, float(DEFAULT_EUR_XAF_RATE))


def xaf_to_eur(value_xaf):
    rate = get_eur_xaf_rate()
    value_xaf = _to_float(value_xaf, 0.0)
    return value_xaf / rate if rate else 0.0


def calculate_order_amounts(product_price_eur, shipping_estimate_eur):
    """
    Calcule tous les montants cohérents de la commande.
    """
    product_price_eur = _to_float(product_price_eur, 0.0)
    shipping_estimate_eur = _to_float(shipping_estimate_eur, 0.0)

    total_eur = product_price_eur + shipping_estimate_eur
    rate = get_eur_xaf_rate()

    seller_fee_xaf = DEFAULT_SELLER_FEE_XAF
    afripay_fee_xaf = DEFAULT_AFRIPAY_FEE_XAF

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


# -------------------------------
# Création de commande
# -------------------------------
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
):
    conn = get_conn()
    cur = conn.cursor()

    order_code = generate_order_code()

    amounts = calculate_order_amounts(
        product_price_eur=product_price_eur,
        shipping_estimate_eur=shipping_estimate_eur,
    )

    clean_site_name = str(site_name or "").strip()
    clean_product_url = str(product_url or "").strip()
    clean_product_title = str(product_title or "").strip()
    clean_product_specs = str(product_specs or "").strip()
    clean_delivery_address = str(delivery_address or "").strip()
    clean_momo_provider = str(momo_provider).strip() if momo_provider else None
    clean_country_code = str(country_code or "CM").strip().upper()

    if merchant_total_amount is None:
        merchant_total_amount = amounts["total_to_pay_eur"]

    clean_merchant_total_amount = _to_float(merchant_total_amount, 0.0)
    clean_merchant_currency = str(merchant_currency or "EUR").strip().upper()

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
            'CREEE',
            'EN_ATTENTE',
            NOW(),
            NOW()
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
            amounts["product_price_eur"],
            amounts["shipping_estimate_eur"],
            amounts["total_to_pay_eur"],
            amounts["seller_fee_xaf"],
            amounts["afripay_fee_xaf"],
            amounts["total_xaf"],
            clean_delivery_address,
            clean_momo_provider,
            clean_merchant_total_amount,
            clean_merchant_currency,
        ),
    )

    row = cur.fetchone()
    result = row["order_code"] if row else order_code

    conn.commit()
    cur.close()
    conn.close()

    return result


# -------------------------------
# Lecture commande par id
# -------------------------------
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


# -------------------------------
# Mise à jour infos marchand (admin)
# -------------------------------
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
            str(merchant_order_number or "").strip(),
            str(merchant_confirmation_url or "").strip(),
            str(merchant_tracking_url or "").strip(),
            str(merchant_purchase_date or "").strip(),
            str(merchant_status or "").strip(),
            str(merchant_notes or "").strip(),
            int(order_id),
        ),
    )

    conn.commit()
    cur.close()
    conn.close()


# -------------------------------
# Liste commandes utilisateur
# -------------------------------
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


# -------------------------------
# Recherche commande par code
# -------------------------------
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
        (str(order_code).strip(),),
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


# -------------------------------
# Mise à jour statut commande
# -------------------------------
def update_order_status(order_id, order_status=None, payment_status=None):
    fields = []
    values = []

    if order_status is not None:
        fields.append("order_status = %s")
        values.append(str(order_status).strip())

    if payment_status is not None:
        fields.append("payment_status = %s")
        values.append(str(payment_status).strip())

    fields.append("updated_at = NOW()")

    if not values:
        return

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


# -------------------------------
# Liste complète (admin)
# -------------------------------
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