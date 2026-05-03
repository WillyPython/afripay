from data.database import get_cursor

with get_cursor() as cur:
    cur.execute("""
        SELECT
            id, name, phone, plan,
            subscription_duration,
            subscription_payment_status,
            subscription_status,
            subscription_active,
            premium_plus_active,
            premium_plus_status
        FROM users
        WHERE phone LIKE '%65889089%'
           OR name ILIKE '%Bobolo%'
        ORDER BY id DESC;
    """)

    rows = cur.fetchall()

    if not rows:
        print("AUCUN RESULTAT BOBolo")
    else:
        for row in rows:
            print(dict(row))
            