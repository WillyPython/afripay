from datetime import datetime
import secrets

from data.database import get_conn


# -------------------------------
# Générer un code de commande
# -------------------------------
def generate_order_code():
    year = datetime.utcnow().year
    rand = secrets.randbelow(900) + 100
    return f"CMD-{year}-{rand}"


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

    total_eur = float(product_price_eur or 0) + float(shipping_estimate_eur or 0)

    cur.execute(
        """
        INSERT INTO orders (
            order_code,
            user_id,
            site_name,
            product_title,
            product_specs,
            product_url,
            product_price_eur,
            shipping_estimate_eur,
            total_to_pay_eur,
            delivery_address,
            momo_provider,
            order_status,
            payment_status,
            created_at
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            'CREEE',
            'EN_ATTENTE',
            NOW()
        )
        RETURNING order_code
        """,
        (
            order_code,
            int(user_id),
            site_name,
            product_title,
            product_specs,
            product_url,
            product_price_eur,
            shipping_estimate_eur,
            total_eur,
            delivery_address,
            momo_provider,
        ),
    )

    result = cur.fetchone()[0]

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
        (order_code,),
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