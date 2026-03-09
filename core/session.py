import os
import streamlit as st


ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "afripay")


SESSION_DEFAULTS = {
    "logged_in": False,
    "user_id": None,
    "otp_code": None,
    "otp_phone": None,
    "admin_logged_in": False,
    "client_logged_in": False,
    "client_phone": "",
    "client_name": "",
    "client_id": None,
    "otp_verified": False,
}


def init_session() -> None:
    """Initialise toutes les clés nécessaires dans st.session_state."""
    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


# =========================
# CLIENT / USER
# =========================
def login_user(user_id=None, phone: str = "", name: str = "") -> None:
    """Connexion utilisateur compatible avec l'ancien code."""
    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user_id
    st.session_state["otp_phone"] = (phone or "").strip()

    st.session_state["client_logged_in"] = True
    st.session_state["client_phone"] = (phone or "").strip()
    st.session_state["client_name"] = (name or "").strip()
    st.session_state["client_id"] = user_id
    st.session_state["otp_verified"] = True


def logout_user() -> None:
    """Déconnecte l'utilisateur/client."""
    st.session_state["logged_in"] = False
    st.session_state["user_id"] = None
    st.session_state["otp_code"] = None
    st.session_state["otp_phone"] = None

    st.session_state["client_logged_in"] = False
    st.session_state["client_phone"] = ""
    st.session_state["client_name"] = ""
    st.session_state["client_id"] = None
    st.session_state["otp_verified"] = False


def login_client(phone: str, name: str = "", client_id=None) -> None:
    """Connexion client explicite."""
    login_user(user_id=client_id, phone=phone, name=name)


def logout_client() -> None:
    """Alias moderne de déconnexion client."""
    logout_user()


def is_client_logged_in() -> bool:
    """Retourne True si le client est connecté."""
    return bool(
        st.session_state.get("client_logged_in", False)
        or st.session_state.get("logged_in", False)
    )


def get_client_phone() -> str:
    """Retourne le téléphone du client connecté."""
    phone = st.session_state.get("client_phone", "")
    if not phone:
        phone = st.session_state.get("otp_phone", "")
    return str(phone).strip()


def get_client_name() -> str:
    """Retourne le nom du client connecté."""
    return str(st.session_state.get("client_name", "")).strip()


def get_client_id():
    """Retourne l'identifiant du client connecté."""
    client_id = st.session_state.get("client_id")
    if client_id is None:
        client_id = st.session_state.get("user_id")
    return client_id


def require_client() -> bool:
    """Vérifie qu'un client est connecté."""
    if not is_client_logged_in():
        st.warning("Veuillez vous connecter pour accéder à cette page.")
        return False
    return True


# =========================
# ADMIN
# =========================
def login_admin(password: str) -> bool:
    """Connexion administrateur via variable d'environnement Render."""
    expected_password = os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    if (password or "").strip() == expected_password:
        st.session_state["admin_logged_in"] = True
        return True

    st.session_state["admin_logged_in"] = False
    return False


def logout_admin() -> None:
    """Déconnecte uniquement l'administrateur."""
    st.session_state["admin_logged_in"] = False


def is_admin_logged_in() -> bool:
    """Retourne True si l'admin est connecté."""
    return bool(st.session_state.get("admin_logged_in", False))


def require_admin() -> bool:
    """Vérifie qu'un admin est connecté."""
    if not is_admin_logged_in():
        st.warning("Accès administrateur requis.")
        return False
    return True


def reset_all_sessions() -> None:
    """Réinitialise complètement toutes les sessions."""
    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state[key] = default_value