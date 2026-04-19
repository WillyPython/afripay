from typing import Any, Dict, Optional

import streamlit as st

from services.admin_service import verify_admin_password


SESSION_DEFAULTS: Dict[str, Any] = {
    "logged_in": False,
    "user_id": None,
    "otp_code": None,
    "otp_phone": None,
    "otp_verified": False,
    "phone": "",
    "name": "",
    "email": "",
    "client_logged_in": False,
    "client_phone": "",
    "client_name": "",
    "client_email": "",
    "client_id": None,
    "admin_logged_in": False,
    "session_token": None,
}


# ------------------------------
# INITIALISATION
# ------------------------------
def init_session() -> None:
    """
    Initialise les clés minimales de session nécessaires à REBUILD.
    """
    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_session_keys(keys: list[str]) -> None:
    """
    Réinitialise un sous-ensemble de clés de session.
    """
    for key in keys:
        if key in SESSION_DEFAULTS:
            st.session_state[key] = SESSION_DEFAULTS[key]
        else:
            st.session_state[key] = None


def reset_all_sessions() -> None:
    """
    Réinitialise toutes les clés de session connues.
    """
    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state[key] = default_value


# ------------------------------
# HELPERS GÉNÉRAUX
# ------------------------------
def set_session_value(key: str, value: Any) -> None:
    st.session_state[key] = value


def get_session_value(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


# ------------------------------
# LOGIN / RESTORE UTILISATEUR
# ------------------------------
def login_user(
    user_id: Optional[int] = None,
    phone: str = "",
    name: str = "",
    email: str = "",
    session_token: Optional[str] = None,
) -> None:
    """
    Ouvre une session utilisateur/client cohérente.
    """
    clean_phone = _clean_text(phone)
    clean_name = _clean_text(name)
    clean_email = _clean_text(email)

    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user_id

    st.session_state["phone"] = clean_phone
    st.session_state["name"] = clean_name
    st.session_state["email"] = clean_email

    st.session_state["otp_phone"] = clean_phone
    st.session_state["otp_verified"] = True
    st.session_state["otp_code"] = None

    st.session_state["client_logged_in"] = True
    st.session_state["client_phone"] = clean_phone
    st.session_state["client_name"] = clean_name
    st.session_state["client_email"] = clean_email
    st.session_state["client_id"] = user_id

    st.session_state["session_token"] = session_token


def restore_user_session(
    user_id: int,
    phone: str = "",
    name: str = "",
    email: str = "",
    session_token: Optional[str] = None,
) -> None:
    """
    Restaure une session utilisateur depuis un token valide.
    """
    login_user(
        user_id=user_id,
        phone=phone,
        name=name,
        email=email,
        session_token=session_token,
    )


def logout_user() -> None:
    """
    Ferme proprement la session utilisateur/client.
    """
    reset_session_keys(
        [
            "logged_in",
            "user_id",
            "otp_code",
            "otp_phone",
            "otp_verified",
            "phone",
            "name",
            "email",
            "client_logged_in",
            "client_phone",
            "client_name",
            "client_email",
            "client_id",
            "session_token",
        ]
    )


# ------------------------------
# ALIAS CLIENT
# ------------------------------
def login_client(
    phone: str,
    name: str = "",
    email: str = "",
    client_id: Optional[int] = None,
    session_token: Optional[str] = None,
) -> None:
    """
    Alias métier explicite pour session client.
    """
    login_user(
        user_id=client_id,
        phone=phone,
        name=name,
        email=email,
        session_token=session_token,
    )


def logout_client() -> None:
    logout_user()


def is_client_logged_in() -> bool:
    return bool(
        st.session_state.get("client_logged_in", False)
        or st.session_state.get("logged_in", False)
    )


def get_client_phone() -> str:
    phone = st.session_state.get("client_phone", "")
    if not phone:
        phone = st.session_state.get("phone", "")
    if not phone:
        phone = st.session_state.get("otp_phone", "")
    return _clean_text(phone)


def get_client_name() -> str:
    name = st.session_state.get("client_name", "")
    if not name:
        name = st.session_state.get("name", "")
    return _clean_text(name)


def get_client_email() -> str:
    email = st.session_state.get("client_email", "")
    if not email:
        email = st.session_state.get("email", "")
    return _clean_text(email)


def get_client_id() -> Optional[int]:
    client_id = st.session_state.get("client_id")
    if client_id is None:
        client_id = st.session_state.get("user_id")
    return client_id


def require_client() -> bool:
    """
    Garde-fou UI pour les vues client connectées.
    """
    if not is_client_logged_in():
        st.warning("Veuillez vous connecter pour accéder à cette page.")
        return False
    return True


# ------------------------------
# OTP
# ------------------------------
def set_pending_otp(phone: str, otp_code: str) -> None:
    """
    Enregistre un OTP en attente de validation.
    """
    st.session_state["otp_phone"] = _clean_text(phone)
    st.session_state["otp_code"] = _clean_text(otp_code)
    st.session_state["otp_verified"] = False


def clear_pending_otp() -> None:
    """
    Nettoie l'état OTP en attente.
    """
    st.session_state["otp_code"] = None
    st.session_state["otp_phone"] = None
    st.session_state["otp_verified"] = False


def get_pending_otp_phone() -> str:
    return _clean_text(st.session_state.get("otp_phone", ""))


def get_pending_otp_code() -> str:
    return _clean_text(st.session_state.get("otp_code", ""))


def is_otp_verified() -> bool:
    return bool(st.session_state.get("otp_verified", False))


def get_session_token() -> Optional[str]:
    return st.session_state.get("session_token")


# ------------------------------
# ADMIN
# ------------------------------
def login_admin(password: str) -> bool:
    """
    Vérifie le mot de passe admin via la couche de service,
    puis marque la session admin comme connectée.
    """
    if verify_admin_password(password):
        st.session_state["admin_logged_in"] = True
        return True

    st.session_state["admin_logged_in"] = False
    return False


def logout_admin() -> None:
    st.session_state["admin_logged_in"] = False


def is_admin_logged_in() -> bool:
    return bool(st.session_state.get("admin_logged_in", False))


def require_admin() -> bool:
    """
    Garde-fou UI pour les vues administrateur.
    """
    if not is_admin_logged_in():
        st.warning("Accès administrateur requis.")
        return False
    return True
