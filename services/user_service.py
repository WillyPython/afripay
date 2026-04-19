from datetime import datetime, timedelta

from data.database import get_cursor


PLAN_FREE = "FREE"
PLAN_PREMIUM = "PREMIUM"
PLAN_PREMIUM_PLUS = "PREMIUM_PLUS"

PREMIUM_PLUS_ALLOWED_DURATIONS = {"6M", "12M"}


# ------------------------------
# Helpers internes
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


def normalize_phone(phone: str) -> str:
    """
    Normalise fortement le numéro de téléphone pour éviter
    les doublons utilisateurs dus au format saisi.

    Exemples :
    +237 630 45 56 -> 2376304556
    237-630-45-56 -> 2376304556
    (237)6304556   -> 2376304556
    """
    if not phone:
        return ""

    raw = str(phone).strip()

    digits_only = "".join(ch for ch in raw if ch.isdigit())
    return digits_only


def normalize_plan(plan: str) -> str:
    """
    Normalise le plan utilisateur.
    Valeurs autorisées :
    - FREE
    - PREMIUM
    - PREMIUM_PLUS
    """
    cleaned = clean_text(plan).upper()

    if cleaned in {PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS}:
        return cleaned

    return PLAN_FREE


def normalize_subscription_duration(value: str):
    """
    Normalise la durée de souscription PREMIUM_PLUS.

    Valeurs finales autorisées :
    - 6M
    - 12M
    """
    raw = clean_text(value).upper().replace(" ", "")

    mapping = {
        "6M": "6M",
        "6MOIS": "6M",
        "6MONTHS": "6M",
        "6_MONTHS": "6M",
        "SEMESTRIEL": "6M",
        "SEMIANNUAL": "6M",
        "SEMI_ANNUAL": "6M",
        "12M": "12M",
        "12MOIS": "12M",
        "12MONTHS": "12M",
        "12_MONTHS": "12M",
        "ANNUEL": "12M",
        "ANNUAL": "12M",
        "YEARLY": "12M",
    }

    normalized = mapping.get(raw, raw)
    return normalized if normalized in PREMIUM_PLUS_ALLOWED_DURATIONS else None


def _parse_datetime(value):
    """
    Convertit un datetime ou une chaîne ISO vers datetime.
    Retourne None si vide ou invalide.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    text = clean_text(value)
    if not text:
        return None

    text = text.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _normalize_bool_to_db(value):
    """
    Convertit différentes formes de vérité en booléen Python.
    """
    if isinstance(value, bool):
        return value

    return clean_text(value).lower() in {
        "true",
        "1",
        "yes",
        "oui",
        "active",
        "actif",
        "paid",
        "paye",
        "payé",
    }


def _subscription_end_date_from_duration(start_date: datetime, duration: str) -> datetime:
    """
    Calcule une date de fin à partir de la durée normalisée.

    Approche simple et stable :
    - 6M  -> +183 jours
    - 12M -> +366 jours
    """
    normalized_duration = normalize_subscription_duration(duration)

    if normalized_duration == "6M":
        return start_date + timedelta(days=183)

    if normalized_duration == "12M":
        return start_date + timedelta(days=366)

    raise ValueError("Durée PREMIUM_PLUS invalide. Utilisez 6M ou 12M.")


# ------------------------------
# Récupérer utilisateur par téléphone
# ------------------------------
def get_user_by_phone(phone: str):
    """
    Récupère un utilisateur par son numéro de téléphone normalisé.

    Important :
    - compare sur une version digits-only pour éviter
      les doublons entre +237..., 237..., espaces, tirets, etc.
    - renvoie l'utilisateur le plus récent si plusieurs entrées
      historiques existent déjà avec le même numéro normalisé
    """
    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                phone,
                name,
                email,
                plan,
                free_orders_used,
                subscription_duration,
                subscription_paid,
                subscription_payment_status,
                subscription_start_date,
                subscription_end_date,
                created_at
            FROM users
            WHERE regexp_replace(COALESCE(phone, ''), '[^0-9]', '', 'g') = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized_phone,),
        )
        user = cur.fetchone()

    return user


# ------------------------------
# Récupérer utilisateur par ID
# ------------------------------
def get_user_by_id(user_id: int):
    """
    Récupère un utilisateur par son identifiant.
    Inclut les champs nécessaires au verrouillage PREMIUM_PLUS.
    """
    if not user_id:
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                phone,
                name,
                email,
                plan,
                free_orders_used,
                subscription_duration,
                subscription_paid,
                subscription_payment_status,
                subscription_start_date,
                subscription_end_date,
                created_at
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (int(user_id),),
        )
        user = cur.fetchone()

    return user


# ------------------------------
# Incrémenter commandes gratuites
# ------------------------------
def increment_free_orders_used(user_id: int) -> None:
    """
    Incrémente le compteur des commandes gratuites utilisées.
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE users
            SET free_orders_used = COALESCE(free_orders_used, 0) + 1
            WHERE id = %s
            """,
            (int(user_id),),
        )


# ------------------------------
# Réinitialiser compteur FREE
# ------------------------------
def reset_free_orders_used(user_id: int) -> None:
    """
    Réinitialise le compteur des commandes gratuites.
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE users
            SET free_orders_used = 0
            WHERE id = %s
            """,
            (int(user_id),),
        )


# ------------------------------
# Créer utilisateur
# ------------------------------
def create_user(phone: str, name: str = "", email: str = "") -> int:
    """
    Crée un nouvel utilisateur avec le plan FREE par défaut.

    Le numéro est stocké dans sa forme normalisée digits-only
    pour stabiliser l'identité du client dans le temps.
    """
    normalized_phone = normalize_phone(phone)
    cleaned_name = clean_text(name)
    cleaned_email = clean_text(email)

    if not normalized_phone:
        raise ValueError("Le numéro de téléphone est obligatoire.")

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO users (
                phone,
                name,
                email,
                plan,
                free_orders_used,
                subscription_duration,
                subscription_paid,
                subscription_payment_status,
                subscription_start_date,
                subscription_end_date,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                normalized_phone,
                cleaned_name,
                cleaned_email,
                PLAN_FREE,
                0,
                None,
                False,
                None,
                None,
                None,
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

    values.append(int(user_id))

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

    Important :
    - on cherche d'abord par téléphone normalisé
    - cela évite de recréer un nouveau compte pour le même client
      et donc de réinitialiser son compteur FREE
    """
    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        raise ValueError("Le numéro de téléphone est obligatoire.")

    cleaned_name = clean_text(name)
    cleaned_email = clean_text(email)

    existing_user = get_user_by_phone(normalized_phone)

    if existing_user:
        user_id = existing_user["id"] if isinstance(existing_user, dict) else existing_user[0]
        update_user(user_id, cleaned_name, cleaned_email)
        return user_id

    return create_user(normalized_phone, cleaned_name, cleaned_email)


# ------------------------------
# Changer plan utilisateur simple
# ------------------------------
def set_user_plan(user_id: int, plan: str) -> None:
    """
    Met à jour le plan utilisateur.

    Cas spéciaux :
    - FREE / PREMIUM : nettoie les champs d'abonnement PREMIUM_PLUS
    - PREMIUM_PLUS : ne doit pas être activé via cette fonction seule
      pour un vrai business flow. Utiliser activate_premium_plus().
    """
    normalized_plan = normalize_plan(plan)

    with get_cursor(commit=True) as cur:
        if normalized_plan in {PLAN_FREE, PLAN_PREMIUM}:
            cur.execute(
                """
                UPDATE users
                SET
                    plan = %s,
                    subscription_duration = NULL,
                    subscription_paid = FALSE,
                    subscription_payment_status = NULL,
                    subscription_start_date = NULL,
                    subscription_end_date = NULL
                WHERE id = %s
                """,
                (normalized_plan, int(user_id)),
            )
        else:
            cur.execute(
                """
                UPDATE users
                SET plan = %s
                WHERE id = %s
                """,
                (normalized_plan, int(user_id)),
            )


# ------------------------------
# Marquer paiement abonnement
# ------------------------------
def mark_premium_plus_payment_pending(user_id: int, duration: str) -> None:
    """
    Enregistre une demande PREMIUM_PLUS non encore validée.
    Aucun accès actif n'est donné ici.
    """
    normalized_duration = normalize_subscription_duration(duration)
    if normalized_duration is None:
        raise ValueError("Durée invalide. Utilisez 6M ou 12M.")

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE users
            SET
                plan = %s,
                subscription_duration = %s,
                subscription_paid = FALSE,
                subscription_payment_status = %s,
                subscription_start_date = NULL,
                subscription_end_date = NULL
            WHERE id = %s
            """,
            (
                PLAN_PREMIUM_PLUS,
                normalized_duration,
                "PENDING",
                int(user_id),
            ),
        )


# ------------------------------
# Activer PREMIUM_PLUS
# ------------------------------
def activate_premium_plus(user_id: int, duration: str, start_date=None) -> None:
    """
    Active réellement PREMIUM_PLUS seulement si :
    - durée valide : 6M ou 12M
    - activation backend explicite
    - dates calculées proprement

    Cette fonction représente le vrai moment d'activation après validation du paiement.
    """
    normalized_duration = normalize_subscription_duration(duration)
    if normalized_duration is None:
        raise ValueError("Durée invalide. Utilisez 6M ou 12M.")

    effective_start_date = _parse_datetime(start_date) or datetime.utcnow()
    effective_end_date = _subscription_end_date_from_duration(
        effective_start_date,
        normalized_duration,
    )

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE users
            SET
                plan = %s,
                subscription_duration = %s,
                subscription_paid = TRUE,
                subscription_payment_status = %s,
                subscription_start_date = %s,
                subscription_end_date = %s
            WHERE id = %s
            """,
            (
                PLAN_PREMIUM_PLUS,
                normalized_duration,
                "PAID",
                effective_start_date,
                effective_end_date,
                int(user_id),
            ),
        )


# ------------------------------
# Désactiver PREMIUM_PLUS expiré
# ------------------------------
def expire_premium_plus_if_needed(user_id: int) -> bool:
    """
    Si l'abonnement PREMIUM_PLUS est expiré, l'utilisateur repasse en PREMIUM.
    Retourne True si une modification a été faite, sinon False.
    """
    user = get_user_by_id(user_id)
    if not user:
        return False

    plan = normalize_plan(user.get("plan"))
    if plan != PLAN_PREMIUM_PLUS:
        return False

    end_date = _parse_datetime(user.get("subscription_end_date"))
    if end_date is None:
        return False

    if end_date >= datetime.utcnow():
        return False

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE users
            SET
                plan = %s,
                subscription_paid = FALSE,
                subscription_payment_status = %s
            WHERE id = %s
            """,
            (
                PLAN_PREMIUM,
                "EXPIRED",
                int(user_id),
            ),
        )

    return True


# ------------------------------
# Vérifier activité PREMIUM_PLUS
# ------------------------------
def is_premium_plus_active(user_id: int) -> bool:
    """
    Vérifie si un utilisateur a un PREMIUM_PLUS réellement actif.
    """
    user = get_user_by_id(user_id)
    if not user:
        return False

    plan = normalize_plan(user.get("plan"))
    if plan != PLAN_PREMIUM_PLUS:
        return False

    duration = normalize_subscription_duration(user.get("subscription_duration"))
    if duration is None:
        return False

    if not _normalize_bool_to_db(user.get("subscription_paid")):
        return False

    payment_status = clean_text(user.get("subscription_payment_status")).upper()
    if payment_status not in {"PAID", "CONFIRMED"}:
        return False

    start_date = _parse_datetime(user.get("subscription_start_date"))
    end_date = _parse_datetime(user.get("subscription_end_date"))

    if start_date is None or end_date is None:
        return False

    now = datetime.utcnow()
    return start_date <= now <= end_date


# ------------------------------
# Lire résumé abonnement
# ------------------------------
def get_user_subscription_summary(user_id: int):
    """
    Retourne un résumé simple d'abonnement pour affichage/UI.
    """
    user = get_user_by_id(user_id)
    if not user:
        return None

    plan = normalize_plan(user.get("plan"))
    duration = normalize_subscription_duration(user.get("subscription_duration"))
    paid = _normalize_bool_to_db(user.get("subscription_paid"))
    payment_status = clean_text(user.get("subscription_payment_status")).upper()
    start_date = _parse_datetime(user.get("subscription_start_date"))
    end_date = _parse_datetime(user.get("subscription_end_date"))

    return {
        "plan": plan,
        "free_orders_used": _to_int(user.get("free_orders_used"), 0),
        "subscription_duration": duration,
        "subscription_paid": paid,
        "subscription_payment_status": payment_status,
        "subscription_start_date": start_date,
        "subscription_end_date": end_date,
        "premium_plus_active": is_premium_plus_active(user_id),
    }
