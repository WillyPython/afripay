"""
AfriBooks BTW - Session Service

Current phase:
- Simple Streamlit session management
- AfriBooks language
- Company profile
- Fiscal profile
- Future auth/security preparation

Important:
The real auth/ layer will come later with:
password hashing, OTP, email verification, tokens,
audit logs, roles, security middleware,
trusted browser, MFA.
"""

from __future__ import annotations

import streamlit as st


DEFAULT_LANGUAGE = "nl"
SUPPORTED_LANGUAGES = ("nl", "fr", "en")


def init_afribooks_session() -> None:
    """
    Initialize minimal AfriBooks session keys.
    Existing values are never overwritten.
    """

    st.session_state.setdefault("afribooks_language", DEFAULT_LANGUAGE)
    st.session_state.setdefault("company_profile", None)
    st.session_state.setdefault("fiscal_profile", None)
    st.session_state.setdefault("afribooks_user", None)
    st.session_state.setdefault("afribooks_authenticated", False)


def get_afribooks_language() -> str:
    """
    Return active AfriBooks language.
    """

    lang = st.session_state.get(
        "afribooks_language",
        DEFAULT_LANGUAGE,
    )

    if lang not in SUPPORTED_LANGUAGES:
        return DEFAULT_LANGUAGE

    return lang


def set_afribooks_language(lang: str) -> None:
    """
    Set active AfriBooks language.
    """

    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    st.session_state["afribooks_language"] = lang


def set_company_profile(profile: dict | None) -> None:
    """
    Store company profile in session.
    """

    st.session_state["company_profile"] = profile


def get_company_profile() -> dict | None:
    """
    Return company profile from session.
    """

    return st.session_state.get("company_profile")


def set_fiscal_profile(profile: dict | None) -> None:
    """
    Store fiscal profile in session.
    """

    st.session_state["fiscal_profile"] = profile


def get_fiscal_profile() -> dict | None:
    """
    Return fiscal profile from session.
    """

    return st.session_state.get("fiscal_profile")


def set_afribooks_user(user: dict | None) -> None:
    """
    Store current AfriBooks user.
    Current phase: simple user management.
    Future phase: auth/, OTP, MFA, roles.
    """

    st.session_state["afribooks_user"] = user
    st.session_state["afribooks_authenticated"] = (
        user is not None
    )


def get_afribooks_user() -> dict | None:
    """
    Return current AfriBooks user.
    """

    return st.session_state.get("afribooks_user")


def is_afribooks_authenticated() -> bool:
    """
    Return authentication state.
    """

    return bool(
        st.session_state.get(
            "afribooks_authenticated",
            False,
        )
    )


def clear_afribooks_session() -> None:
    """
    Clear only AfriBooks session keys.
    Does not touch AfriPay or Streamlit keys.
    """

    keys = [
        "afribooks_language",
        "company_profile",
        "fiscal_profile",
        "afribooks_user",
        "afribooks_authenticated",
    ]

    for key in keys:
        st.session_state.pop(key, None)
