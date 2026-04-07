import json
from pathlib import Path

import streamlit as st


_STORE_PATH = Path(__file__).resolve().parents[2] / "memory" / "user_store.json"


def load_user_store_into_session():
    if not _STORE_PATH.exists():
        return

    try:
        payload = json.loads(_STORE_PATH.read_text())
    except Exception:
        return

    st.session_state.users = payload.get("users", {}) or {}
    st.session_state.user_histories = payload.get("user_histories", {}) or {}


def save_user_store_from_session():
    payload = {
        "users": st.session_state.get("users", {}),
        "user_histories": st.session_state.get("user_histories", {}),
    }

    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(payload, indent=2))
