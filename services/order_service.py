import math
from datetime import datetime

from config.settings import now_iso
from data.database import get_conn
from services.admin_service import get_setting


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def round_xaf(value):
    """
    Règle AfriPay / XAF :
    - pas de centimes
    - si entier exact, on garde l'entier
    - sinon, on arrondit au franc supérieur
    Exemples :
    234.00 -> 234
    234.01 -> 235
    234.19 -> 235
    """
    value = _safe_float(value, 0.0)
    return int(value) if float(value).is_integer() else math.ceil(value)


def format_xaf_number(value):
    return f"{round_xaf(value):,}".replace(",", ".")


def round_eur(value):
    """
    L'EUR reste avec 2 décimales.
    """
    return round(_safe_float(value, 0.0), 2)


def get_current_rate():
    rate = get_setting("eur_xaf_rate", "655.957")
    return _safe_float(rate, 655.957)


def generate_order_code():
    conn = get_conn()
    cur = conn.cursor()

    year = datetime.utcnow().strftime("%Y")

    cur.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE substr(created_at, 1, 4) = ?",
        (year,),
    )
    row = cur.fetchone()
    count = int(row["n"]) if row else 0

    conn.close()
    return f"CMD-{year}-{count + 1:03d}"


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

    eur_xaf_rate_used = get_current_rate()

    site_name = (site_name or "").strip()
    product_url = (product_url or "").strip()
    product_title = (product_title or "").strip()
    product_specs = (product_specs or "").strip()
    delivery_address = (delivery_address or "").strip()
    momo_provider = (momo_provider or "").strip() or None

    product_price_eur = round_eur(product_price_eur)
    shipping_estimate_eur = round_eur(shipping_estimate_eur)

    # Le client saisit le total marchand + transport via les champs EUR actuels
    subtotal_eur = round_eur(product_price_eur + shipping_estimate_eur)

    # Commission AfriPay (8%)
    commission_eur = round_eur(subtotal_eur * 0.08)

    # Total final côté AfriPay
    total_to_pay_eur = round_eur(subtotal_eur + commission_eur)

    # Conversion XAF
    seller_fee_xaf = round_xaf(subtotal_eur * eur_xaf_rate_used)
    afripay_fee_xaf = round_xaf(commission_eur * eur_xaf_rate_used)
    total_xaf = round_xaf(total_to_pay_eur * eur_xaf_rate_used)

    created_at = now_iso()
    updated_at = created_at
    order_code = generate_order_code()

    payment_reference = f"PAY-{order_code}"
    payment_status = "EN_ATTENTE"
    order_status = "CREEE"

    cur.execute(
        """
        INSERT INTO orders(
            user_id,
            site_name,
            product_url,
            product_title,
            product_specs,
            product_image_path,
            product_price_eur,
            shipping_estimate_eur,
            commission_eur,
            total_to_pay_eur,
            eur_xaf_rate_used,
            total_to_pay_xaf,
            delivery_address,
            client_ack,
            payment_reference,
            payment_status,
            momo_provider,
            momo_tx_id,
            payment_proof_path,
            purchase_proof_path,
            tracking_number,
            tracking_url,
            order_status,
            created_at,
            updated_at,
            order_code,
            seller_fee_xaf,
            afripay_fee_xaf,
            total_xaf
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(user_id),
            site_name,
            product_url,
            product_title,
            product_specs,
            None,
            product_price_eur,
            shipping_estimate_eur,
            commission_eur,
            total_to_pay_eur,
            eur_xaf_rate_used,
            total_xaf,
            delivery_address,
            1,
            payment_reference,
            payment_status,
            momo_provider,
            None,
            None,
            None,
            None,
            None,
            order_status,
            created_at,
            updated_at,
            order_code,
            seller_fee_xaf,
            afripay_fee_xaf,
            total_xaf,
        ),
    )

    conn.commit()
    conn.close()

    return order_code


def list_orders_for_user(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            order_code,
            product_title AS product_name,
            product_title,
            site_name,
            product_url,
            product_specs,
            product_price_eur,
            shipping_estimate_eur,
            commission_eur,
            total_to_pay_eur,
            eur_xaf_rate_used,
            total_to_pay_xaf,
            seller_fee_xaf,
            afripay_fee_xaf,
            total_xaf,
            delivery_address,
            payment_reference,
            payment_status,
            momo_provider,
            order_status,
            created_at,
            updated_at,
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
            merchant_status
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (int(user_id),),
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def get_order_by_code(order_code):
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
        LEFT JOIN users u ON u.id = o.user_id
        WHERE o.order_code = ?
        LIMIT 1
        """,
        ((order_code or "").strip().upper(),),
    )

    row = cur.fetchone()
    conn.close()
    return row


def list_orders_all(limit=None):
    conn = get_conn()
    cur = conn.cursor()

    if limit is None:
        cur.execute(
            """
            SELECT
                o.*,
                u.name AS user_name,
                u.phone AS user_phone,
                u.email AS user_email
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            ORDER BY o.id DESC
            """
        )
    else:
        cur.execute(
            """
            SELECT
                o.*,
                u.name AS user_name,
                u.phone AS user_phone,
                u.email AS user_email
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            ORDER BY o.id DESC
            LIMIT ?
            """,
            (int(limit),),
        )

    rows = cur.fetchall()
    conn.close()
    return rows


def update_merchant_info(
    order_id,
    merchant_order_number,
    merchant_confirmation_url,
    merchant_tracking_url,
    merchant_purchase_date,
    merchant_status,
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE orders
        SET
            merchant_order_number = ?,
            merchant_confirmation_url = ?,
            merchant_tracking_url = ?,
            merchant_purchase_date = ?,
            merchant_status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            (merchant_order_number or "").strip() or None,
            (merchant_confirmation_url or "").strip() or None,
            (merchant_tracking_url or "").strip() or None,
            (merchant_purchase_date or "").strip() or None,
            (merchant_status or "").strip() or None,
            now_iso(),
            int(order_id),
        ),
    )

    conn.commit()
    conn.close()