from data.database import get_conn


def normalize_phone(phone: str) -> str:
    return phone.strip()


def upsert_user(phone: str, name: str = "", email: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()

    normalized_phone = normalize_phone(phone)

    # vérifier si utilisateur existe
    cur.execute(
        "SELECT id FROM users WHERE phone = %s LIMIT 1",
        (normalized_phone,)
    )

    row = cur.fetchone()

    if row:
        user_id = row["id"] if isinstance(row, dict) else row[0]

        cur.execute(
            """
            UPDATE users
            SET name = %s,
                email = %s
            WHERE id = %s
            """,
            (name, email, user_id)
        )

    else:
        cur.execute(
            """
            INSERT INTO users (phone, name, email)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (normalized_phone, name, email)
        )

        row = cur.fetchone()
        user_id = row["id"] if isinstance(row, dict) else row[0]

    conn.commit()
    cur.close()
    conn.close()

    return user_id