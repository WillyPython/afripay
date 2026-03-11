from data.database import get_conn
from datetime import datetime


# ------------------------------
# Normalisation téléphone
# ------------------------------

def normalize_phone(phone: str) -> str:
    """
    Nettoie le numéro de téléphone.
    Supprime espaces et caractères inutiles.
    """
    if not phone:
        return ""

    phone = phone.strip()
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")

    return phone


# ------------------------------
# Récupérer utilisateur
# ------------------------------

def get_user_by_phone(phone: str):

    conn = get_conn()
    cur = conn.cursor()

    normalized_phone = normalize_phone(phone)

    cur.execute(
        """
        SELECT id, phone, name, email, created_at
        FROM users
        WHERE phone = %s
        LIMIT 1
        """,
        (normalized_phone,)
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user


# ------------------------------
# Créer utilisateur
# ------------------------------

def create_user(phone: str, name: str = "", email: str = ""):

    conn = get_conn()
    cur = conn.cursor()

    normalized_phone = normalize_phone(phone)

    cur.execute(
        """
        INSERT INTO users (phone, name, email, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (
            normalized_phone,
            name,
            email,
            datetime.utcnow()
        )
    )

    row = cur.fetchone()

    user_id = row["id"] if isinstance(row, dict) else row[0]

    conn.commit()

    cur.close()
    conn.close()

    return user_id


# ------------------------------
# Mettre à jour utilisateur
# ------------------------------

def update_user(user_id: int, name: str = "", email: str = ""):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET name = %s,
            email = %s
        WHERE id = %s
        """,
        (name, email, user_id)
    )

    conn.commit()

    cur.close()
    conn.close()


# ------------------------------
# Créer ou mettre à jour
# ------------------------------

def upsert_user(phone: str, name: str = "", email: str = "") -> int:
    """
    Crée l'utilisateur s'il n'existe pas.
    Sinon met à jour ses informations.
    """

    user = get_user_by_phone(phone)

    if user:
        user_id = user["id"] if isinstance(user, dict) else user[0]
        update_user(user_id, name, email)
        return user_id

    return create_user(phone, name, email)