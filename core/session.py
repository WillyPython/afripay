import os
import streamlit as st


# =========================
# CONFIG ADMIN
# =========================
# Sur Render : lit la variable d'environnement ADMIN_PASSWORD
# En local : utilise "afripay" par défaut si rien n'est défini
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "afripay")


# =========================
# INITIALISATION SESSION
# =========================
def init_session() -> None:
    """Initialise toutes les clés nécessaires dans st.session_state."""
    defaults = {
        "client_logged_in": False,
        "client_phone": "",
        "client_name": "",
        "client_id": None,
        "otp_verified": False,
        "admin_logged_in": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =========================
# CLIENT
# =========================
def login_client(phone: str, name: str = "", client_id=None) -> None:
    """Connecte un client dans la session."""
    st.session_state["client_logged_in"] = True
    st.session_state["client_phone"] = (phone or "").strip()
    st.session_state["client_name"] = (name or "").strip()
    st.session_state["client_id"] = client_id
    st.session_state["otp_verified"] = True


def logout_client() -> None:
    """Déconnecte le client."""
    st.session_state["client_logged_in"] = False
    st.session_state["client_phone"] = ""
    st.session_state["client_name"] = ""
    st.session_state["client_id"] = None
    st.session_state["otp_verified"] = False


def is_client_logged_in() -> bool:
    """Retourne True si le client est connecté."""
    return bool(st.session_state.get("client_logged_in", False))


def get_client_phone() -> str:
    """Retourne le téléphone du client connecté."""
    return str(st.session_state.get("client_phone", "")).strip()


def get_client_name() -> str:
    """Retourne le nom du client connecté."""
    return str(st.session_state.get("client_name", "")).strip()


def get_client_id():
    """Retourne l'identifiant du client connecté."""
    return st.session_state.get("client_id")


def require_client() -> bool:
    """
    Vérifie qu'un client est connecté.
    Affiche un avertissement et retourne False sinon.
    """
    if not is_client_logged_in():
        st.warning("Veuillez vous connecter pour accéder à cette page.")
        return False
    return True


# =========================
# ADMIN
# =========================
def login_admin(password: str) -> bool:
    """
    Vérifie le mot de passe admin et ouvre la session admin.
    Compatible Render via variable d'environnement ADMIN_PASSWORD.
    """
    expected_password = os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    if (password or "").strip() == expected_password:
        st.session_state["admin_logged_in"] = True
        return True

    st.session_state["admin_logged_in"] = False
    return False


def logout_admin() -> None:
    """Déconnecte l'admin."""
    st.session_state["admin_logged_in"] = False


def is_admin_logged_in() -> bool:
    """Retourne True si l'admin est connecté."""
    return bool(st.session_state.get("admin_logged_in", False))


def require_admin() -> bool:
    """
    Vérifie qu'un admin est connecté.
    Affiche un avertissement et retourne False sinon.
    """
    if not is_admin_logged_in():
        st.warning("Accès administrateur requis.")
        return False
    return True