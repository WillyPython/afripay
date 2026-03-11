import secrets
from datetime import datetime, timedelta
from typing import Optional

from data.database import get_conn


# durée de session par défaut (30 jours)
SESSION_DURATION_DAYS = 30


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
    duration_days: int = SESSION_DURATION_DAYS
) -> str:
    """
    Crée une session persistante en base.
    Retourne le token de session.
    """

    conn = get_conn()
    cur = conn.cursor()

    token = generate_session_token()

    now = datetime.utcnow()
    expires_at = now + timedelta(days=duration_days)

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
        )
    )

    row = cur.fetchone()

    conn.commit()

    cur.close()
    conn.close()

    return row["session_token"] if isinstance(row, dict) else row[0]


# =========================
# LIRE SESSION ACTIVE
# =========================
def get_active_session(token: str):
    """
    Retourne une session active si elle existe
    et n'est pas expirée.
    """

    if not token:
        return None

    conn = get_conn()
    cur = conn.cursor()

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
        (token,)
    )

    row = cur.fetchone()

    # vérification expiration
    if row:
        expires_at = row["expires_at"] if isinstance(row, dict) else None

        if expires_at and expires_at < datetime.utcnow():
            cur.execute(
                """
                UPDATE user_sessions
                SET is_active = FALSE
                WHERE session_token = %s
                """,
                (token,)
            )

            conn.commit()
            row = None

    cur.close()
    conn.close()

    return row


# =========================
# ACTUALISER SESSION
# =========================
def touch_session(token: str) -> None:
    """
    Met à jour last_seen_at pour une session active.
    """

    if not token:
        return

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE user_sessions
        SET last_seen_at = %s
        WHERE session_token = %s
          AND is_active = TRUE
        """,
        (datetime.utcnow(), token)
    )

    conn.commit()

    cur.close()
    conn.close()


# =========================
# DESACTIVER SESSION
# =========================
def deactivate_session(token: str) -> None:
    """
    Désactive une session spécifique.
    """

    if not token:
        return

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE user_sessions
        SET is_active = FALSE
        WHERE session_token = %s
        """,
        (token,)
    )

    conn.commit()

    cur.close()
    conn.close()


# =========================
# DESACTIVER TOUTES SESSIONS
# =========================
def deactivate_user_sessions(user_id: int) -> None:
    """
    Désactive toutes les sessions d'un utilisateur.
    """

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE user_sessions
        SET is_active = FALSE
        WHERE user_id = %s
        """,
        (user_id,)
    )

    conn.commit()

    cur.close()
    conn.close()