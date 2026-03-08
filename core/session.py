import streamlit as st


SESSION_DEFAULTS = {
    "logged_in": False,
    "user_id": None,
    "otp_code": None,
    "otp_phone": None,
    "admin_logged_in": False,
}


def init_session():
    """
    Initialise toutes les clés de session nécessaires à l'application.
    """
    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def logout_user():
    """
    Déconnecte uniquement le client.
    """
    st.session_state["logged_in"] = False
    st.session_state["user_id"] = None
    st.session_state["otp_code"] = None
    st.session_state["otp_phone"] = None


def logout_admin():
    """
    Déconnecte uniquement l'administrateur.
    """
    st.session_state["admin_logged_in"] = False


def reset_all_sessions():
    """
    Réinitialise complètement les sessions client + admin.
    """
    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state[key] = default_value