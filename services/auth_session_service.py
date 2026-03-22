from datetime import datetime, timedelta
from typing import Optional
import secrets

from config.settings import SESSION_DURATION_DAYS
from data.database import get_cursor


# =========================
# GENERATION TOKEN
# =========================
def generate_session_token() -> str:
    """
    Génère un token sécurisé pour une session utilisateur.
    """
    return secrets.token_urlsafe(48)


# =========================
# CREER SESSION
# =========================
def create_user_session(
    user_id: int,
    phone: str = "",
    duration_days: int = SESSION_DURATION_DAYS,
) -> str:
    """
    Crée une session persistante en base.
    Retourne le token de session.
    """
    token = generate_session_token()
    now = datetime.utcnow()
    expires_at = now + timedelta(days=duration_days)

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO user_sessions (
                user_id,
                session_token,
                phone,
                is_active,
                created_at,
                expires_at,
                last_seen_at
            )
            VALUES (%s, %s, %s, TRUE, %s, %s, %s)
            RETURNING session_token
            """,
            (
                user_id,
                token,
                (phone or "").strip(),
                now,
                expires_at,
                now,
            ),
        )
        row = cur.fetchone()

    return row["session_token"] if row else token


# =========================
# LIRE SESSION ACTIVE
# =========================
def get_active_session(token: str):
    """
    Retourne une session active si elle existe
    et n'est pas expirée.
    """
    clean_token = str(token or "").strip()
    if not clean_token:
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                us.id,
                us.user_id,
                us.session_token,
                us.phone,
                us.is_active,
                us.created_at,
                us.expires_at,
                us.last_seen_at,
                u.name,
                u.email
            FROM user_sessions us
            JOIN users u ON u.id = us.user_id
            WHERE us.session_token = %s
              AND us.is_active = TRUE
            LIMIT 1
            """,
            (clean_token,),
        )
        row = cur.fetchone()

    if not row:
        return None

    expires_at = row.get("expires_at") if isinstance(row, dict) else None
    if expires_at and expires_at < datetime.utcnow():
        deactivate_session(clean_token)
        return None

    return row


# =========================
# ACTUALISER SESSION
# =========================
def touch_session(token: str) -> None:
    """
    Met à jour last_seen_at pour une session active non expirée.
    """
    clean_token = str(token or "").strip()
    if not clean_token:
        return

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE user_sessions
            SET last_seen_at = %s
            WHERE session_token = %s
              AND is_active = TRUE
              AND (expires_at IS NULL OR expires_at > %s)
            """,
            (datetime.utcnow(), clean_token, datetime.utcnow()),
        )


# =========================
# DESACTIVER SESSION
# =========================
def deactivate_session(token: str) -> None:
    """
    Désactive une session spécifique.
    """
    clean_token = str(token or "").strip()
    if not clean_token:
        return

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE user_sessions
            SET is_active = FALSE
            WHERE session_token = %s
            """,
            (clean_token,),
        )


# =========================
# DESACTIVER TOUTES SESSIONS
# =========================
def deactivate_user_sessions(user_id: int) -> None:
    """
    Désactive toutes les sessions d'un utilisateur.
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE user_sessions
            SET is_active = FALSE
            WHERE user_id = %s
            """,
            (user_id,),
        )