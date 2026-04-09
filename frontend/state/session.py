"""
frontend/state/session.py

Session state schema for the redesigned NestWise.
Everything is initialised once; subsequent reruns skip keys that already exist.
"""

import streamlit as st
from datetime import datetime
from typing import List 


def init_session_state():
    defaults = {
        # ── Onboarding ──────────────────────────────────────────
        "onboarding_complete": False,   # True once preferences are saved
        "onboarding_step": 0,           # which step the user is on (0-based)
        "pref_budget": None,
        "pref_flat_type": None,
        "pref_floor_area": None,
        "pref_remaining_lease": None,
        "pref_town": [],                # [] = recommendation mode
        "pref_school_scope": "Any",
        "pref_amenity_rank": [],        # list of amenity keys, index 0 = top priority
        "pref_landmark_postals": [],

        # ── Search sessions ──────────────────────────────────────
        # Each session: {
        #   "session_id": str,
        #   "label": str,           # e.g. "4-room · Tampines · 14 Apr"
        #   "inputs": UserInputs,
        #   "bundle": dict,
        #   "map_bundle": dict,
        #   "liked_ids": [],
        #   "passed_ids": [],
        #   "unseen_ids": [],        # listing_ids not yet swiped
        #   "created_at": str,
        # }
        "search_sessions": [],
        "active_session_id": None,      # which session the deck is showing

        # Legacy keys kept for compatibility with existing backend calls
        "insights_generated": False,
        "latest_inputs": None,
        "latest_bundle": None,
        "latest_map_bundle": None,

        # ── Comparison ──────────────────────────────────────────
        "compare_selected_ids": [],     # ids selected across ALL sessions
        "custom_compare_rows": [],

        # ── UI state ────────────────────────────────────────────
        "active_page": "Discover",      # sidebar nav
        "deck_index": 0,                # which card is on top
        "detail_listing_id": None,      # if not None, show detail overlay

        # ── Auth ────────────────────────────────────────────────
        "current_user": None,
        "users": {},                    # email -> {"password": str, "preferences": dict}
        "user_histories": {},           # email -> [session dicts]
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def make_session_label(inputs) -> str:
    towns = inputs.town or []
    if len(towns) == 1:
        town_label = towns[0].title()
    elif len(towns) > 1:
        town_label = f"{towns[0].title()} +{len(towns) - 1}"
    else:
        town_label = "Reco mode"
    date = datetime.now().strftime("%d %b")
    return f"{inputs.flat_type} · {town_label} · {date}"


def create_search_session(inputs, bundle, map_bundle) -> str:
    """Create a new search session and return its ID."""
    import uuid

    session_id = str(uuid.uuid4())[:8]
    listing_ids = list(bundle["listings_df"]["listing_id"].values)

    session = {
        "session_id": session_id,
        "label": make_session_label(inputs),
        "inputs": inputs,
        "bundle": bundle,
        "map_bundle": map_bundle,
        "liked_ids": [],
        "passed_ids": [],
        "unseen_ids": listing_ids.copy(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    st.session_state.search_sessions.append(session)
    st.session_state.active_session_id = session_id
    st.session_state.deck_index = 0

    # Clear compare state for new session
    st.session_state.compare_selected_ids = []
    st.session_state.custom_compare_rows = []

    # Keep legacy keys working
    st.session_state.latest_inputs = inputs
    st.session_state.latest_bundle = bundle
    st.session_state.latest_map_bundle = map_bundle
    st.session_state.insights_generated = True

    return session_id


def get_active_session():
    sid = st.session_state.active_session_id
    if not sid:
        return None
    for s in st.session_state.search_sessions:
        if s["session_id"] == sid:
            return s
    return None


def record_swipe(session_id: str, listing_id: str, direction: str):
    """direction: 'right' | 'left' | 'up'"""
    for s in st.session_state.search_sessions:
        if s["session_id"] != session_id:
            continue
        if listing_id in s["unseen_ids"]:
            s["unseen_ids"].remove(listing_id)
        if direction in ("right", "up"):
            if listing_id not in s["liked_ids"]:
                s["liked_ids"].append(listing_id)
        elif direction == "left":
            if listing_id not in s["passed_ids"]:
                s["passed_ids"].append(listing_id)
        break


def get_all_liked_ids() -> List[str]:
    """Collect liked IDs across all sessions."""
    ids = []
    for s in st.session_state.search_sessions:
        for lid in s["liked_ids"]:
            if lid not in ids:
                ids.append(lid)
    return ids


def get_liked_df():
    """Return a DataFrame of all liked listings across all sessions, tagged with session label."""
    import pandas as pd
    rows = []
    for s in st.session_state.search_sessions:
        if s["bundle"] is None:
            continue
        df = s["bundle"]["listings_df"]
        for lid in s["liked_ids"]:
            match = df[df["listing_id"] == lid]
            if match.empty:
                continue
            row = match.iloc[0].to_dict()
            row["session_label"] = s["label"]
            row["session_id"]    = s["session_id"]
            rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def get_active_session_liked_df():
    """Return a DataFrame of liked listings for the currently active session only."""
    import pandas as pd

    session = get_active_session()
    if session is None or session.get("bundle") is None:
        return pd.DataFrame()

    df = session["bundle"]["listings_df"]
    rows = []

    for lid in session.get("liked_ids", []):
        match = df[df["listing_id"] == lid]
        if match.empty:
            continue

        row = match.iloc[0].to_dict()
        row["session_label"] = session["label"]
        row["session_id"] = session["session_id"]
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()

