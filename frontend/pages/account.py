"""
frontend/pages/account.py

Account tab: login/signup + inline preference editing + session history.

Each preference is individually editable — no full onboarding restart needed.
Saving any edit:
  1. Updates the stored preference
  2. Rebuilds UserInputs from current prefs
  3. Runs get_prediction_bundle() to generate a fresh listing deck
  4. Calls create_search_session() — old saves are preserved, tagged to their session
  5. Navigates user to Discover
"""

import streamlit as st

from frontend.components.onboarding import (
    build_inputs_from_prefs,
    get_preferences_display,
    AMENITY_ICONS,
    FLAT_TYPE_LABELS,
    FLAT_ICONS,
)
from backend.utils.constants import AMENITY_LABELS, FLAT_TYPES, TOWNS


# ── Public entry point ────────────────────────────────────────────────────────

def render_account_page():
    if st.session_state.current_user is None:
        _render_auth()
    elif st.session_state.current_user == "__guest__":
        _render_guest()
    else:
        _render_logged_in()


# ── Auth ──────────────────────────────────────────────────────────────────────

def _render_auth():
    # ── Branded header ─────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center;padding:2.8rem 0 2rem;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                        width:60px;height:60px;border-radius:18px;
                        background:#FFF0F1;border:1.5px solid rgba(255,68,88,0.20);
                        font-size:1.9rem;margin-bottom:1.1rem;box-shadow:0 8px 24px rgba(255,68,88,0.10);">
                🏠
            </div>
            <h1 style="font-size:2rem;font-weight:800;letter-spacing:-0.04em;
                       color:#1a1a2e;margin:0 0 0.45rem;">Welcome to HomeRun</h1>
            <p style="font-size:0.9rem;color:#6b7280;margin:0;">
                Your personalised HDB flat finder
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Centered form ──────────────────────────────────────────────────────────
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        login_tab, signup_tab = st.tabs(["  Log in  ", "  Create account  "])

        with login_tab:
            st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
            email    = st.text_input("Email address", key="login_email",
                                     placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="login_password",
                                     placeholder="Your password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Log in →", type="primary", key="login_btn",
                         use_container_width=True):
                users = st.session_state.users
                if email in users and users[email]["password"] == password:
                    st.session_state.current_user = email
                    st.success(f"Welcome back, {email}!")
                    st.rerun()
                else:
                    st.error("Incorrect email or password — please try again.")

        with signup_tab:
            st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
            new_email    = st.text_input("Email address", key="signup_email",
                                         placeholder="you@example.com")
            new_password = st.text_input("Password", type="password", key="signup_password",
                                         placeholder="Choose a strong password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Create account →", type="primary", key="signup_btn",
                         use_container_width=True):
                if not new_email or not new_password:
                    st.warning("Please fill in both fields.")
                elif new_email in st.session_state.users:
                    st.warning("An account with this email already exists.")
                else:
                    st.session_state.users[new_email] = {"password": new_password}
                    st.session_state.user_histories[new_email] = []
                    st.success("Account created — you can now log in! 🎉")


# ── Guest view ────────────────────────────────────────────────────────────────

def _render_guest():
    st.markdown(
        """
        <div style="text-align:center;padding:2.8rem 0 1.6rem;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                        width:60px;height:60px;border-radius:18px;
                        background:#FFF0F1;border:1.5px solid rgba(255,68,88,0.20);
                        font-size:1.9rem;margin-bottom:1.1rem;">
                👤
            </div>
            <div style="display:inline-block;font-size:0.68rem;font-weight:700;
                        letter-spacing:0.08em;text-transform:uppercase;
                        background:rgba(255,180,0,0.12);color:#D97706;
                        border-radius:8px;padding:3px 10px;margin-bottom:1rem;">
                Guest mode
            </div>
            <h2 style="font-size:1.7rem;font-weight:800;letter-spacing:-0.04em;
                       color:#1a1a2e;margin:0 0 0.5rem;">You're browsing as a guest</h2>
            <p style="font-size:0.9rem;color:#6b7280;max-width:380px;margin:0 auto 2rem;
                      line-height:1.65;">
                Create a free account to save your preferences, keep your search history,
                and pick up where you left off next time.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        signup_tab, login_tab = st.tabs(["  Create account  ", "  Log in  "])

        with signup_tab:
            st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
            new_email    = st.text_input("Email address", key="guest_signup_email",
                                         placeholder="you@example.com")
            new_password = st.text_input("Password", type="password",
                                         key="guest_signup_password",
                                         placeholder="Choose a password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Create account & continue →", type="primary",
                         key="guest_signup_btn", use_container_width=True):
                if not new_email or not new_password:
                    st.warning("Please fill in both fields.")
                elif new_email in st.session_state.users:
                    st.warning("An account with this email already exists.")
                else:
                    st.session_state.users[new_email] = {"password": new_password}
                    st.session_state.user_histories[new_email] = []
                    st.session_state.current_user = new_email
                    st.rerun()

        with login_tab:
            st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
            email    = st.text_input("Email address", key="guest_login_email",
                                     placeholder="you@example.com")
            password = st.text_input("Password", type="password",
                                     key="guest_login_password",
                                     placeholder="Your password")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Log in →", type="primary", key="guest_login_btn",
                         use_container_width=True):
                users = st.session_state.users
                if email in users and users[email]["password"] == password:
                    st.session_state.current_user = email
                    st.rerun()
                else:
                    st.error("Incorrect email or password.")

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.6, 1])
    with col2:
        if st.button("← Back to guest mode", key="guest_back_btn",
                     use_container_width=True):
            st.session_state.active_page = "Discover"
            st.rerun()


# ── Logged-in view ────────────────────────────────────────────────────────────

def _render_logged_in():
    user = st.session_state.current_user
    st.markdown(
        f"<h2 style='font-size:1.65rem;font-weight:800;letter-spacing:-0.03em;"
        f"color:#0f172a;margin-bottom:0.2rem;'>Account</h2>"
        f"<p style='font-size:0.85rem;color:#9ca3af;margin-bottom:1.4rem;'>"
        f"Logged in as <strong>{user}</strong></p>",
        unsafe_allow_html=True,
    )

    pref_tab, history_tab, settings_tab = st.tabs([
        "My preferences", "Search history", "Settings"
    ])

    with pref_tab:
        _render_preferences()
    with history_tab:
        _render_history()
    with settings_tab:
        _render_settings(user)


# ── Inline preference editor ──────────────────────────────────────────────────

# Which field is currently open for editing (None = all collapsed)
def _get_editing() -> str | None:
    return st.session_state.get("pref_editing_field", None)

def _set_editing(field: str | None):
    st.session_state.pref_editing_field = field


def _render_preferences():
    if not st.session_state.get("onboarding_complete"):
        st.info("Complete onboarding first to set your preferences.")
        return

    st.markdown(
        "<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.08em;color:#059E87;margin-bottom:0.2rem;'>"
        "Your preferences</p>"
        "<p style='font-size:0.8rem;color:#9ca3af;margin-bottom:1rem;'>"
        "Edit any single preference — we'll instantly generate a new deck for you.</p>",
        unsafe_allow_html=True,
    )

    _pref_row_budget()
    _pref_row_flat_type()
    _pref_row_floor_area()
    _pref_row_lease()
    _pref_row_town()
    _pref_row_amenity_rank()
    _pref_row_anchors()


# ── Shared row chrome ─────────────────────────────────────────────────────────

def _row_header(label: str, value_display: str, field_key: str):
    """
    Renders the collapsed row (label + value + Edit button).
    Returns True if this row is currently open.
    """
    editing = _get_editing()
    is_open = editing == field_key

    col_l, col_v, col_btn = st.columns([1.4, 2.2, 0.9])
    with col_l:
        st.markdown(
            f"<p style='font-size:0.8rem;color:#9ca3af;font-weight:600;"
            f"padding-top:0.55rem;'>{label}</p>",
            unsafe_allow_html=True,
        )
    with col_v:
        st.markdown(
            f"<p style='font-size:0.88rem;font-weight:700;color:#0f172a;"
            f"padding-top:0.55rem;'>{value_display}</p>",
            unsafe_allow_html=True,
        )
    with col_btn:
        btn_label = "Close" if is_open else "Edit"
        if st.button(btn_label, key=f"edit_btn_{field_key}", use_container_width=True):
            _set_editing(None if is_open else field_key)
            st.rerun()

    st.markdown(
        "<hr style='border:none;border-top:1px solid #e4e7ed;margin:4px 0 8px;'>",
        unsafe_allow_html=True,
    )
    return is_open


def _save_and_regenerate():
    """
    Called after any preference is updated.
    Builds fresh inputs → runs backend → creates new session → navigates to Discover.
    """
    from backend.services.predictor_service import get_prediction_bundle
    from backend.services.map_service import get_map_bundle
    from frontend.state.session import create_search_session

    _set_editing(None)

    with st.spinner("Generating your new deck…"):
        inputs     = build_inputs_from_prefs()
        bundle     = get_prediction_bundle(inputs)
        map_bundle = get_map_bundle(inputs, bundle["recommendations_df"])

    create_search_session(inputs, bundle, map_bundle)
    st.session_state.active_page = "Discover"
    st.rerun()


# ── Individual preference rows ────────────────────────────────────────────────

def _pref_row_budget():
    val   = st.session_state.get("pref_budget") or 650000
    label = f"S${val:,}"
    open_ = _row_header("Budget", label, "budget")
    if not open_:
        return

    new_val = st.slider(
        "Budget", 200000, 1500000, val, 10000,
        format="S$%d", key="edit_budget_slider", label_visibility="collapsed",
    )
    st.markdown(
        f"<div style='text-align:center;font-size:1.8rem;font-weight:800;"
        f"letter-spacing:-0.03em;color:#0f172a;margin:0.2rem 0 0.8rem;'>"
        f"S${new_val:,}</div>",
        unsafe_allow_html=True,
    )
    if st.button("Save & generate new deck →", key="save_budget",
                 type="primary", use_container_width=True):
        st.session_state.pref_budget = new_val
        _save_and_regenerate()


def _pref_row_flat_type():
    val   = st.session_state.get("pref_flat_type") or "4 ROOM"
    label = FLAT_TYPE_LABELS.get(val, val)
    open_ = _row_header("Flat type", label, "flat_type")
    if not open_:
        return

    current = st.session_state.get("pref_flat_type") or "4 ROOM"
    cols = st.columns(len(FLAT_TYPES))
    for i, ft in enumerate(FLAT_TYPES):
        selected = current == ft
        border = "2px solid #059E87" if selected else "1.5px solid #e4e7ed"
        bg     = "#e6f7f4" if selected else "#ffffff"
        color  = "#059E87" if selected else "#4b5563"
        with cols[i]:
            st.markdown(
                f"""<div style="border:{border};background:{bg};border-radius:12px;
                    padding:10px 4px;text-align:center;margin-bottom:4px;">
                    <div style="font-size:1.4rem;">{FLAT_ICONS[ft]}</div>
                    <div style="font-size:0.72rem;font-weight:700;color:{color};
                         margin-top:4px;">{FLAT_TYPE_LABELS[ft]}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button(FLAT_TYPE_LABELS[ft], key=f"edit_ft_{ft}",
                         use_container_width=True):
                st.session_state.pref_flat_type = ft
                _save_and_regenerate()


def _pref_row_floor_area():
    val   = st.session_state.get("pref_floor_area") or 95
    label = f"{val} sqm"
    open_ = _row_header("Floor area", label, "floor_area")
    if not open_:
        return

    new_val = st.slider(
        "Floor area", 35, 160, val, 5,
        format="%d sqm", key="edit_area_slider", label_visibility="collapsed",
    )
    st.markdown(
        f"<div style='text-align:center;font-size:1.8rem;font-weight:800;"
        f"letter-spacing:-0.03em;color:#0f172a;margin:0.2rem 0 0.8rem;'>"
        f"{new_val} sqm</div>",
        unsafe_allow_html=True,
    )
    if st.button("Save & generate new deck →", key="save_area",
                 type="primary", use_container_width=True):
        st.session_state.pref_floor_area = new_val
        _save_and_regenerate()


def _pref_row_lease():
    val   = st.session_state.get("pref_remaining_lease") or 60
    label = f"{val} years remaining"
    open_ = _row_header("Min. lease", label, "lease")
    if not open_:
        return

    new_val = st.slider(
        "Remaining lease", 20, 95, val, 1,
        format="%d years", key="edit_lease_slider", label_visibility="collapsed",
    )
    if new_val >= 80:   hint = "Near-new flat"
    elif new_val >= 60: hint = "Plenty of lease left"
    elif new_val >= 40: hint = "Moderate — check CPF rules"
    else:               hint = "Short lease — financing may be limited"

    st.markdown(
        f"<div style='text-align:center;font-size:1.8rem;font-weight:800;"
        f"letter-spacing:-0.03em;color:#0f172a;margin:0.2rem 0 0.2rem;'>"
        f"{new_val} years</div>"
        f"<div style='text-align:center;font-size:0.8rem;color:#9ca3af;"
        f"margin-bottom:0.8rem;'>{hint}</div>",
        unsafe_allow_html=True,
    )
    if st.button("Save & generate new deck →", key="save_lease",
                 type="primary", use_container_width=True):
        st.session_state.pref_remaining_lease = new_val
        _save_and_regenerate()


def _pref_row_town():
    val   = st.session_state.get("pref_town")
    label = val if val else "Recommendation mode"
    open_ = _row_header("Town", label, "town")
    if not open_:
        return

    if st.button("🗺️  Use recommendation mode", key="edit_town_reco",
                 use_container_width=True):
        st.session_state.pref_town = None
        _save_and_regenerate()

    st.markdown("<div style='margin:8px 0 4px;font-size:0.76rem;color:#9ca3af;font-weight:600;'>OR PICK A SPECIFIC TOWN</div>", unsafe_allow_html=True)
    current_idx = (sorted(TOWNS).index(val) + 1) if val in (TOWNS or []) else 0
    town_choice = st.selectbox(
        "Town", ["— select —"] + sorted(TOWNS),
        index=current_idx, key="edit_town_select", label_visibility="collapsed",
    )
    if town_choice != "— select —":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save & generate new deck →", key="save_town",
                         type="primary", use_container_width=True):
                st.session_state.pref_town = town_choice
                _save_and_regenerate()


def _pref_row_amenity_rank():
    rank  = st.session_state.get("pref_amenity_rank") or []
    label = " → ".join(
        f"{AMENITY_ICONS.get(k,'')} {AMENITY_LABELS.get(k,k)}" for k in rank[:3]
    ) + ("…" if len(rank) > 3 else "")
    label = label or "Not set"
    open_ = _row_header("Amenity rank", label, "amenity_rank")
    if not open_:
        return

    # Show current rank with remove buttons
    all_keys  = list(AMENITY_LABELS.keys())
    remaining = [k for k in all_keys if k not in rank]

    if rank:
        st.markdown(
            "<p style='font-size:0.76rem;color:#9ca3af;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px;'>"
            "Current ranking</p>",
            unsafe_allow_html=True,
        )
        for i, key in enumerate(rank):
            icon  = AMENITY_ICONS.get(key, "")
            lbl   = AMENITY_LABELS.get(key, key)
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;"
                    f"padding:8px 12px;background:#f7f8fa;border:1px solid #e4e7ed;"
                    f"border-radius:9px;margin-bottom:5px;'>"
                    f"<span style='font-size:0.68rem;font-weight:800;color:#059E87;"
                    f"min-width:16px;'>#{i+1}</span>"
                    f"<span style='font-size:1rem;'>{icon}</span>"
                    f"<span style='font-size:0.84rem;font-weight:600;color:#0f172a;'>{lbl}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("✕", key=f"rm_rank_{key}_{i}"):
                    st.session_state.pref_amenity_rank = rank[:i]
                    st.rerun()

    if remaining:
        st.markdown(
            "<p style='font-size:0.76rem;color:#9ca3af;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.07em;margin:10px 0 6px;'>"
            "Add next priority</p>",
            unsafe_allow_html=True,
        )
        chip_cols = st.columns(3)
        for i, key in enumerate(remaining):
            icon = AMENITY_ICONS.get(key, "")
            lbl  = AMENITY_LABELS.get(key, key)
            with chip_cols[i % 3]:
                if st.button(f"{icon} {lbl}", key=f"add_rank_{key}",
                             use_container_width=True):
                    new_rank = (st.session_state.pref_amenity_rank or []) + [key]
                    st.session_state.pref_amenity_rank = new_rank
                    st.rerun()

    if len(rank) == len(all_keys):
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("Save & generate new deck →", key="save_amenity",
                     type="primary", use_container_width=True):
            _save_and_regenerate()


def _pref_row_anchors():
    existing = st.session_state.get("pref_landmark_postals") or []
    label    = ", ".join(existing) if existing else "None"
    open_    = _row_header("Anchor locations", label, "anchors")
    if not open_:
        return

    c1, c2 = st.columns(2)
    with c1:
        v1 = st.text_input(
            "Postal code 1",
            value=existing[0] if len(existing) > 0 else "",
            placeholder="e.g. 119077", key="edit_anchor_1",
        )
    with c2:
        v2 = st.text_input(
            "Postal code 2",
            value=existing[1] if len(existing) > 1 else "",
            placeholder="e.g. 560215", key="edit_anchor_2",
        )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Clear anchors", key="clear_anchors", use_container_width=True):
            st.session_state.pref_landmark_postals = []
            _save_and_regenerate()
    with col_b:
        if st.button("Save & generate new deck →", key="save_anchors",
                     type="primary", use_container_width=True):
            postals = [p.strip() for p in [v1, v2] if p.strip()]
            st.session_state.pref_landmark_postals = postals
            _save_and_regenerate()


# ── Search history ────────────────────────────────────────────────────────────

def _render_history():
    sessions = st.session_state.get("search_sessions", [])
    if not sessions:
        st.info("No search sessions yet.")
        return

    st.session_state.setdefault("selected_history_session_id", None)

    st.markdown(
        f"<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.08em;color:#059E87;margin-bottom:0.8rem;'>"
        f"{len(sessions)} session{'s' if len(sessions) != 1 else ''}</p>",
        unsafe_allow_html=True,
    )

    for s in reversed(sessions):
        n_liked  = len(s["liked_ids"])
        n_pass   = len(s["passed_ids"])
        n_unseen = len(s["unseen_ids"])

        is_active = s["session_id"] == st.session_state.get("active_session_id")
        is_selected = s["session_id"] == st.session_state.get("selected_history_session_id")

        if is_active:
            border = "2px solid #059E87"
            bg = "#f0fdf9"
        elif is_selected:
            border = "2px solid #FF6B6B"
            bg = "#fff5f5"
        else:
            border = "1px solid #e4e7ed"
            bg = "#ffffff"

        active_badge = (
            "<span style='font-size:0.68rem;font-weight:700;color:#059E87;"
            "background:#e6f7f4;border:1px solid #a7e8dc;border-radius:999px;"
            "padding:2px 7px;margin-left:6px;'>Active</span>"
            if is_active else ""
        )

        selected_badge = (
            "<span style='font-size:0.68rem;font-weight:700;color:#b91c1c;"
            "background:#fee2e2;border:1px solid #fecaca;border-radius:999px;"
            "padding:2px 7px;margin-left:6px;'>Selected</span>"
            if is_selected and not is_active else ""
        )

        st.markdown(
            f"""
            <div style="border:{border};border-radius:14px;padding:14px 16px;
                        margin-bottom:10px;background:{bg};">
                <div style="display:flex;align-items:center;margin-bottom:4px;">
                    <span style="font-size:0.9rem;font-weight:700;color:#0f172a;">
                        {s['label']}</span>{active_badge}{selected_badge}
                </div>
                <div style="font-size:0.74rem;color:#9ca3af;margin-bottom:10px;">
                    {s['created_at']}
                </div>
                <div style="display:flex;gap:14px;flex-wrap:wrap;">
                    <span style="font-size:0.78rem;color:#059E87;font-weight:600;">
                        ♥ {n_liked} saved</span>
                    <span style="font-size:0.78rem;color:#9ca3af;font-weight:600;">
                        ✕ {n_pass} passed · ◌ {n_unseen} unseen</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not is_active:
            btn_label = "Selected" if is_selected else "Select this session"
            if st.button(btn_label, key=f"select_history_{s['session_id']}", use_container_width=True):
                st.session_state.selected_history_session_id = s["session_id"]
                st.rerun()

    selected_session_id = st.session_state.get("selected_history_session_id")
    if selected_session_id:
        selected_session = next(
            (s for s in sessions if s["session_id"] == selected_session_id),
            None
        )

        if selected_session and selected_session_id != st.session_state.get("active_session_id"):
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.info(f"Selected session: {selected_session['label']}")

            if st.button("Resume selected session →", type="primary", use_container_width=True):
                st.session_state.active_session_id = selected_session["session_id"]
                st.session_state.compare_selected_ids = []
                st.session_state.custom_compare_rows = []
                st.session_state.selected_history_session_id = None
                st.session_state.active_page = "Discover"
                st.rerun()

# ── Settings ──────────────────────────────────────────────────────────────────

def _render_settings(user: str):
    st.markdown(
        "<p style='font-size:0.88rem;color:#4b5563;margin-bottom:1.2rem;'>"
        "Manage your account.</p>",
        unsafe_allow_html=True,
    )

    if st.button("Log out", use_container_width=False):
        st.session_state.current_user = None
        st.rerun()

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    if st.button("Clear all search history & saved flats", use_container_width=False):
        st.session_state.search_sessions        = []
        st.session_state.active_session_id      = None
        st.session_state.insights_generated     = False
        st.session_state.compare_selected_ids   = []
        st.success("All history cleared.")
        st.rerun()
