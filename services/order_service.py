from datetime import datetime

from data.database import get_conn


DEFAULT_EXCHANGE_RATE = 655.0


def _round_xaf(value: float) -> int:
    value = float(value or 0)
    rounded = int(value) if value.is_integer() else int(value) + 1
    return rounded


def _generate_order_code() -> str:
    conn = get_conn()
    cur = conn.cursor()

    year = datetime.now().year
    prefix = f"CMD-{year}-"

    cur.execute(
        """
        SELECT order_code
        FROM orders
        WHERE order_code LIKE %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (f"{prefix}%",),
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return f"{prefix}001"

    last_code = row["order_code"] if isinstance(row, dict) else row[0]

    try:
        last_number = int(str(last_code).split("-")[-1])
    except Exception:
        last_number = 0

    return f"{prefix}{last_number + 1:03d}"


def create_order_for_user(
    user_id: int,
    site_name: str,
    product_url: str,
    product_title: str,
    product_specs: str,
    product_price_eur: float,
    shipping_estimate_eur: float,
    delivery_address: str,
    momo_provider: str | None = None,
) -> str:
    conn = get_conn()
    cur = conn.cursor()

    total_to_pay_eur = float(product_price_eur or 0) + float(shipping_estimate_eur or 0)
    total_xaf = _round_xaf(total_to_pay_eur * DEFAULT_EXCHANGE_RATE)

    seller_fee_xaf = 0
    afripay_fee_xaf = 0
    order_code = _generate_order_code()

    cur.execute(
        """
        INSERT INTO orders (
            user_id,
            order_code,
            site_name,
            product_url,
            product_title,
            product_name,
            product_specs,
            product_price_eur,
            shipping_estimate_eur,
            total_to_pay_eur,
            total_xaf,
            seller_fee_xaf,
            afripay_fee_xaf,
            delivery_address,
            momo_provider,
            order_status,
            payment_status,
            merchant_status,
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
            created_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        """,
        (
            int(user_id),
            order_code,
            site_name,
            product_url,
            product_title,
            product_title,
            product_specs,
            float(product_price_eur or 0),
            float(shipping_estimate_eur or 0),
            total_to_pay_eur,
            total_xaf,
            seller_fee_xaf,
            afripay_fee_xaf,
            delivery_address,
            momo_provider,
            "CREEE",
            "EN_ATTENTE",
            "",
            "",
            "",
            "",
            None,
        ),
    )

    conn.commit()
    cur.close()
    conn.close()

    return order_code


def list_orders_for_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            user_id,
            order_code,
            site_name,
            product_url,
            product_title,
            product_name,
            product_specs,
            product_price_eur,
            shipping_estimate_eur,
            total_to_pay_eur,
            total_xaf,
            seller_fee_xaf,
            afripay_fee_xaf,
            delivery_address,
            momo_provider,
            order_status,
            payment_status,
            merchant_status,
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
            created_at
        FROM orders
        WHERE user_id = %s
        ORDER BY id DESC
        """,
        (int(user_id),),
    )
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def get_order_by_code(order_code: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            user_id,
            order_code,
            site_name,
            product_url,
            product_title,
            product_name,
            product_specs,
            product_price_eur,
            shipping_estimate_eur,
            total_to_pay_eur,
            total_xaf,
            seller_fee_xaf,
            afripay_fee_xaf,
            delivery_address,
            momo_provider,
            order_status,
            payment_status,
            merchant_status,
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
            created_at
        FROM orders
        WHERE order_code = %s
        LIMIT 1
        """,
        (order_code.strip(),),
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


def list_orders_all():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            user_id,
            order_code,
            site_name,
            product_url,
            product_title,
            product_name,
            product_specs,
            product_price_eur,
            shipping_estimate_eur,
            total_to_pay_eur,
            total_xaf,
            seller_fee_xaf,
            afripay_fee_xaf,
            delivery_address,
            momo_provider,
            order_status,
            payment_status,
            merchant_status,
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
            created_at
        FROM orders
        ORDER BY id DESC
        """
    )
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def update_merchant_info(
    order_id: int,
    merchant_order_number: str = "",
    merchant_confirmation_url: str = "",
    merchant_tracking_url: str = "",
    merchant_purchase_date: str = "",
    merchant_status: str = "",
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE orders
        SET merchant_order_number = %s,
            merchant_confirmation_url = %s,
            merchant_tracking_url = %s,
            merchant_purchase_date = %s,
            merchant_status = %s
        WHERE id = %s
        """,
        (
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date or None,
            merchant_status,
            int(order_id),
        ),
    )

    conn.commit()
    cur.close()
    conn.close()