from config.settings import now_iso
from data.database import get_conn


def normalize_phone(phone):
    """
    Normalise le numéro sans le dénaturer :
    - supprime les espaces
    - supprime les parenthèses
    - supprime les tirets
    - garde le + si présent
    """
    phone = str(phone or "").strip()
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")
    phone = phone.replace("(", "")
    phone = phone.replace(")", "")
    return phone


def clean_text(value):
    return str(value or "").strip()


def upsert_user(phone, name="", email=""):
    """
    Crée l'utilisateur si le téléphone n'existe pas,
    sinon met à jour les informations utiles.
    Retourne toujours l'id utilisateur.
    """
    normalized_phone = normalize_phone(phone)
    clean_name = clean_text(name)
    clean_email = clean_text(email)

    if not normalized_phone:
        raise ValueError("Le téléphone est obligatoire.")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, email
        FROM users
        WHERE phone = ?
        LIMIT 1
        """,
        (normalized_phone,),
    )
    row = cur.fetchone()

    if row:
        user_id = int(row["id"])

        existing_name = clean_text(row["name"])
        existing_email = clean_text(row["email"])

        new_name = clean_name or existing_name
        new_email = clean_email or existing_email

        cur.execute(
            """
            UPDATE users
            SET name = ?, email = ?
            WHERE id = ?
            """,
            (new_name or None, new_email or None, user_id),
        )

        conn.commit()
        conn.close()
        return user_id

    created_at = now_iso()

    cur.execute(
        """
        INSERT INTO users(phone, name, email, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            normalized_phone,
            clean_name or None,
            clean_email or None,
            created_at,
        ),
    )

    user_id = cur.lastrowid

    conn.commit()
    conn.close()

    return int(user_id)


def get_user_by_phone(phone):
    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        return None

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, phone, name, email, created_at
        FROM users
        WHERE phone = ?
        LIMIT 1
        """,
        (normalized_phone,),
    )

    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, phone, name, email, created_at
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (int(user_id),),
    )

    row = cur.fetchone()
    conn.close()
    return row