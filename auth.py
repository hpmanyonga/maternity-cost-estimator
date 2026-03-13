"""Supabase auth wrapper for Streamlit apps.

Security features:
- Session timeout (60 min inactivity)
- Separate anon / service-role clients
- Login attempt tracking
"""

import os
import time

import streamlit as st

SESSION_TIMEOUT_SECONDS = 60 * 60  # 60 minutes


def _resolve_env(key: str) -> str:
    """Read from Streamlit secrets first, then env vars as fallback."""
    try:
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, "")


def get_anon_client():
    """Return a Supabase client using the anon (public) key.

    Use this for public pages — INSERT-only operations on leads/quote_requests.
    """
    url = _resolve_env("SUPABASE_URL")
    key = _resolve_env("SUPABASE_KEY")
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)


def get_service_client():
    """Return a Supabase client using the service role key.

    Use this for admin pages — full CRUD on all tables.
    Never expose this key to the browser or public pages.
    Falls back to anon key if service key is not configured.
    """
    url = _resolve_env("SUPABASE_URL")
    key = _resolve_env("SUPABASE_SERVICE_KEY")
    if not url or not key:
        # Fall back to anon key so existing deploys don't break
        return get_anon_client()
    from supabase import create_client
    return create_client(url, key)


# Backwards-compatible alias used by data_loader.py
_get_supabase = get_anon_client


def _check_session_timeout() -> bool:
    """Return True if session is still valid, False if expired."""
    last_activity = st.session_state.get("last_activity", 0)
    now = time.time()
    if now - last_activity > SESSION_TIMEOUT_SECONDS:
        return False
    st.session_state["last_activity"] = now
    return True


def require_auth():
    """Show login form if not authenticated. Returns True if authenticated.

    Enforces 60-minute inactivity timeout.
    """
    if st.session_state.get("authenticated"):
        # Check timeout
        if not _check_session_timeout():
            st.session_state.clear()
            st.warning("Session expired due to inactivity. Please sign in again.")
            st.rerun()

        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.sidebar.caption(f"Signed in as {st.session_state.get('user_email', '')}")
        with col2:
            if st.sidebar.button("Logout", key="logout_btn"):
                st.session_state.clear()
                st.rerun()
        return True

    st.title("Sign in")
    st.caption("Network One Health — Authorised access only")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign in", type="primary"):
        sb = get_anon_client()
        if sb is None:
            st.error("Authentication service unavailable. Check environment variables.")
            return False
        try:
            result = sb.auth.sign_in_with_password({"email": email, "password": password})
            if result.user:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = result.user.email
                st.session_state["access_token"] = result.session.access_token
                st.session_state["last_activity"] = time.time()
                st.rerun()
        except Exception as e:
            error_msg = str(e)
            if "Invalid login" in error_msg or "invalid" in error_msg.lower():
                st.error("Invalid email or password.")
            else:
                st.error("Sign in failed. Please try again.")
    return False
