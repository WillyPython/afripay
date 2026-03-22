from datetime import datetime

from data.database import get_cursor


# ------------------------------
# Nettoyage texte
# ------------------------------
def clean_text(value: str) -> str:
    """
    Nettoie une valeur texte.
    Retourne une chaîne vide si None.
    Supprime les espaces inutiles en début/fin.
    """
    if value is None:
        return ""

    return str(value).strip()


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

    phone = str(phone).strip()
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")
    phone = phone.replace(".", "")
    phone = phone.replace("(", "")
    phone = phone.replace(")", "")

    return phone


# ------------------------------
# Récupérer utilisateur
# ------------------------------
def get_user_by_phone(phone: str):
    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, phone, name, email, created_at
            FROM users
            WHERE phone = %s
            LIMIT 1
            """,
            (normalized_phone,),
        )
        user = cur.fetchone()

    return user


# ------------------------------
# Créer utilisateur
# ------------------------------
def create_user(phone: str, name: str = "", email: str = "") -> int:
    normalized_phone = normalize_phone(phone)
    cleaned_name = clean_text(name)
    cleaned_email = clean_text(email)

    if not normalized_phone:
        raise ValueError("Le numéro de téléphone est obligatoire.")

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO users (phone, name, email, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                normalized_phone,
                cleaned_name,
                cleaned_email,
                datetime.utcnow(),
            ),
        )
        row = cur.fetchone()

    return row["id"] if row else None


# ------------------------------
# Mettre à jour utilisateur
# ------------------------------
def update_user(user_id: int, name: str = "", email: str = "") -> None:
    """
    Met à jour uniquement les champs fournis non vides.
    N'écrase jamais le nom ou l'email existant avec une valeur vide.
    """
    cleaned_name = clean_text(name)
    cleaned_email = clean_text(email)

    fields = []
    values = []

    if cleaned_name:
        fields.append("name = %s")
        values.append(cleaned_name)

    if cleaned_email:
        fields.append("email = %s")
        values.append(cleaned_email)

    if not fields:
        return

    values.append(user_id)

    query = f"""
        UPDATE users
        SET {", ".join(fields)}
        WHERE id = %s
    """

    with get_cursor(commit=True) as cur:
        cur.execute(query, tuple(values))


# ------------------------------
# Créer ou mettre à jour
# ------------------------------
def upsert_user(phone: str, name: str = "", email: str = "") -> int:
    """
    Crée l'utilisateur s'il n'existe pas.
    Sinon met à jour ses informations sans écraser
    les valeurs existantes avec du vide.
    """
    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        raise ValueError("Le numéro de téléphone est obligatoire.")

    cleaned_name = clean_text(name)
    cleaned_email = clean_text(email)

    user = get_user_by_phone(normalized_phone)

    if user:
        user_id = user["id"] if isinstance(user, dict) else user[0]
        update_user(user_id, cleaned_name, cleaned_email)
        return user_id

    return create_user(normalized_phone, cleaned_name, cleaned_email)