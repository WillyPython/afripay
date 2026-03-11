import os
from typing import Any, Dict, Optional

import streamlit as st


ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "afripay")


SESSION_DEFAULTS: Dict[str, Any] = {
    "logged_in": False,
    "user_id": None,
    "otp_code": None,
    "otp_phone": None,
    "otp_verified": False,
    "client_logged_in": False,
    "client_phone": "",
    "client_name": "",
    "client_id": None,
    "admin_logged_in": False,
    "session_token": None,
}


def init_session() -> None:
    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_session_keys(keys: list[str]) -> None:
    for key in keys:
        if key in SESSION_DEFAULTS:
            st.session_state[key] = SESSION_DEFAULTS[key]
        else:
            st.session_state[key] = None


def reset_all_sessions() -> None:
    for key, default_value in SESSION_DEFAULTS.items():
        st.session_state[key] = default_value


def set_session_value(key: str, value: Any) -> None:
    st.session_state[key] = value


def get_session_value(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def login_user(
    user_id: Optional[int] = None,
    phone: str = "",
    name: str = "",
    session_token: Optional[str] = None,
) -> None:
    clean_phone = (phone or "").strip()
    clean_name = (name or "").strip()

    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user_id

    st.session_state["otp_phone"] = clean_phone
    st.session_state["otp_verified"] = True

    st.session_state["client_logged_in"] = True
    st.session_state["client_phone"] = clean_phone
    st.session_state["client_name"] = clean_name
    st.session_state["client_id"] = user_id

    st.session_state["session_token"] = session_token


def restore_user_session(
    user_id: int,
    phone: str = "",
    name: str = "",
    session_token: Optional[str] = None,
) -> None:
    """
    Restaure une session utilisateur depuis un token valide.
    """
    login_user(
        user_id=user_id,
        phone=phone,
        name=name,
        session_token=session_token,
    )


def logout_user() -> None:
    reset_session_keys(
        [
            "logged_in",
            "user_id",
            "otp_code",
            "otp_phone",
            "otp_verified",
            "client_logged_in",
            "client_phone",
            "client_name",
            "client_id",
            "session_token",
        ]
    )


def login_client(
    phone: str,
    name: str = "",
    client_id: Optional[int] = None,
    session_token: Optional[str] = None,
) -> None:
    login_user(
        user_id=client_id,
        phone=phone,
        name=name,
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
        phone = st.session_state.get("otp_phone", "")
    return str(phone or "").strip()


def get_client_name() -> str:
    return str(st.session_state.get("client_name", "") or "").strip()


def get_client_id() -> Optional[int]:
    client_id = st.session_state.get("client_id")
    if client_id is None:
        client_id = st.session_state.get("user_id")
    return client_id


def get_session_token() -> Optional[str]:
    return st.session_state.get("session_token")


def require_client() -> bool:
    if not is_client_logged_in():
        st.warning("Veuillez vous connecter pour accéder à cette page.")
        return False
    return True


def set_pending_otp(phone: str, otp_code: str) -> None:
    st.session_state["otp_phone"] = (phone or "").strip()
    st.session_state["otp_code"] = str(otp_code or "").strip()
    st.session_state["otp_verified"] = False


def clear_pending_otp() -> None:
    st.session_state["otp_code"] = None
    st.session_state["otp_phone"] = None
    st.session_state["otp_verified"] = False


def get_pending_otp_phone() -> str:
    return str(st.session_state.get("otp_phone", "") or "").strip()


def is_otp_verified() -> bool:
    return bool(st.session_state.get("otp_verified", False))


def login_admin(password: str) -> bool:
    expected_password = os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    if (password or "").strip() == str(expected_password).strip():
        st.session_state["admin_logged_in"] = True
        return True

    st.session_state["admin_logged_in"] = False
    return False


def logout_admin() -> None:
    st.session_state["admin_logged_in"] = False


def is_admin_logged_in() -> bool:
    return bool(st.session_state.get("admin_logged_in", False))


def require_admin() -> bool:
    if not is_admin_logged_in():
        st.warning("Accès administrateur requis.")
        return False
    return True