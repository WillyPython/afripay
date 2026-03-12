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
):
    conn = get_conn()
    cur = conn.cursor()

    order_code = generate_order_code()

    amounts = calculate_order_amounts(
        product_price_eur=product_price_eur,
        shipping_estimate_eur=shipping_estimate_eur,
    )

    cur.execute(
        """
        INSERT INTO orders (
            order_code,
            user_id,
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
            order_status,
            payment_status,
            created_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            'CREEE',
            'EN_ATTENTE',
            NOW()
        )
        RETURNING order_code
        """,
        (
            order_code,
            int(user_id),
            str(site_name or "").strip(),
            str(product_title or "").strip(),
            str(product_title or "").strip(),
            str(product_specs or "").strip(),
            str(product_url or "").strip(),
            amounts["product_price_eur"],
            amounts["shipping_estimate_eur"],
            amounts["total_to_pay_eur"],
            amounts["seller_fee_xaf"],
            amounts["afripay_fee_xaf"],
            amounts["total_xaf"],
            str(delivery_address or "").strip(),
            (str(momo_provider).strip() if momo_provider else None),
        ),
    )

    row = cur.fetchone()
    result = row["order_code"] if row else order_code

    conn.commit()
    cur.close()
    conn.close()

    return result


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
# Liste complète (admin)
# -------------------------------
def list_orders_all():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM orders
        ORDER BY created_at DESC
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows