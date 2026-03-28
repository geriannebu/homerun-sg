"""
app.py — HomeRun SG

Flow:
  1. Landing page  → "Get Started" opens an auth dialog (create account / log in)
  2. Onboarding    → step-by-step preferences
  3. Auto-search   → deck generated from prefs
  4. Discover      → swipe deck (primary screen)
  5. Saved         → cross-session saved flats
  6. Compare       → side-by-side comparison
  7. Account       → preferences + session history
"""

import streamlit as st
from pathlib import Path


def _resolve_logo() -> str:
    base = Path(__file__).parent / "frontend" / "assets"
    for name in ("homerunlogo.png", "homerunlogo.jpeg"):
        p = base / name
        if p.exists():
            return str(p)
    return ""


_LOGO_PATH = _resolve_logo()

from frontend.styles.css import inject_css
from frontend.state.session import init_session_state, create_search_session

from frontend.components.hero import get_logo_img_tag
from frontend.components.onboarding import (
    render_onboarding,
    build_inputs_from_prefs,
)

from backend.services.predictor_service import get_prediction_bundle
from backend.services.map_service import get_map_bundle

from frontend.pages.flat_outputs.best_matches import render_listing_tab
from frontend.pages.flat_outputs.price_story import render_price_story_tab
from frontend.pages.flat_outputs.map_view import render_map_tab
from frontend.pages.saved import render_saved_page
from frontend.pages.comparison_tool import render_comparison_page
from frontend.pages.account import render_account_page
from frontend.components.sections import render_section
from frontend.components.methodology import render_methodology
from frontend.components.cards import (
    render_value_cards,
    render_budget_banner,
    render_nestwise_pick,
)


st.set_page_config(
    page_title="HomeRun",
    page_icon=_LOGO_PATH,
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = ["Discover", "Saved", "Compare", "Account"]


# ── Auth dialog ───────────────────────────────────────────────────────────────

@st.dialog("Welcome to HomeRun", width="small")
def _show_auth_dialog(initial_tab: str = "create"):
    """Cancellable popup for account creation and login."""
    st.markdown(
        f"""
        <div style="text-align:center;margin-bottom:1.4rem;">
            <div style="display:inline-block;border-radius:20px;overflow:hidden;
                        box-shadow:0 4px 20px rgba(255,68,88,0.18);margin-bottom:0.9rem;">
                {get_logo_img_tag(64)}
            </div>
            <p style="font-size:0.88rem;color:#6b7280;margin:0;">
                Your personalised HDB flat finder
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    create_tab, login_tab = st.tabs(["Create account", "Log in"])

    with create_tab:
        email    = st.text_input("Email", placeholder="you@email.com",
                                 key="dialog_create_email")
        password = st.text_input("Password", type="password",
                                 placeholder="Choose a password",
                                 key="dialog_create_password")
        st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)
        if st.button("Create account & get started →", type="primary",
                     use_container_width=True, key="dialog_create_btn"):
            if not email or not password:
                st.warning("Please fill in both fields.")
            elif email in st.session_state.users:
                st.warning("An account with this email already exists. Try logging in.")
            else:
                st.session_state.users[email] = {"password": password}
                st.session_state.user_histories[email] = []
                st.session_state.current_user = email
                st.rerun()

    with login_tab:
        l_email    = st.text_input("Email", key="dialog_login_email")
        l_password = st.text_input("Password", type="password",
                                   key="dialog_login_password")
        st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)
        if st.button("Log in →", type="primary",
                     use_container_width=True, key="dialog_login_btn"):
            users = st.session_state.users
            if l_email in users and users[l_email]["password"] == l_password:
                st.session_state.current_user = l_email
                st.rerun()
            else:
                st.error("Invalid email or password.")

    st.markdown(
        "<p style='text-align:center;font-size:0.72rem;color:#b0b0c0;"
        "margin-top:1rem;'>Your data stays in this browser session only.</p>",
        unsafe_allow_html=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_session_state()
    inject_css()

    # ── 1. Auth gate ──────────────────────────────────────────────────────────
    if not st.session_state.get("current_user"):
        _render_landing_page()
        return

    # ── 2. Sidebar ────────────────────────────────────────────────────────────
    _render_sidebar()
    page = st.session_state.active_page

    # ── 3. Onboarding gate ────────────────────────────────────────────────────
    if page == "Discover" and not st.session_state.get("onboarding_complete"):
        _run_onboarding()
        return

    # ── 4. Route ──────────────────────────────────────────────────────────────
    if page == "Discover":
        _render_discover()
    elif page == "Saved":
        render_saved_page()
    elif page == "Compare":
        _render_compare()
    elif page == "Account":
        render_account_page()


# ── Landing page ──────────────────────────────────────────────────────────────

def _render_landing_page():
    """Clean landing page — logo, tagline, Get Started / Log in buttons."""
    st.markdown(
        f"""
        <div style="max-width:420px;margin:0 auto;padding:5rem 1rem 0;text-align:center;">
            <div style="display:inline-block;border-radius:24px;overflow:hidden;
                        box-shadow:0 0 0 1px rgba(255,68,88,0.1),
                                   0 12px 36px rgba(255,68,88,0.16);
                        margin-bottom:1.4rem;">
                {get_logo_img_tag(96)}
            </div>
            <h1 style="font-family:'DM Sans',sans-serif;font-size:2.2rem;font-weight:800;
                       letter-spacing:-0.045em;color:#0b132d;margin:0 0 0.5rem;">HomeRun</h1>
            <p style="font-size:0.95rem;color:#94a3b8;font-weight:500;margin-bottom:2.5rem;">
                Find the fair price of your dream HDB flat.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button("Get Started →", type="primary",
                     use_container_width=True, key="landing_get_started"):
            _show_auth_dialog()

        st.markdown(
            "<p style='text-align:center;font-size:0.78rem;color:#b0b0c0;"
            "margin-top:0.7rem;'>Already have an account? "
            "Click Get Started and switch to Log in.</p>",
            unsafe_allow_html=True,
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────

_PAGE_ICONS = {"Discover": "🔥", "Saved": "♥", "Compare": "⚖️", "Account": "👤"}


def _render_sidebar():
    from frontend.state.session import get_active_session

    # Logo
    try:
        st.logo(_LOGO_PATH, size="large")
    except Exception:
        pass

    logo_html = get_logo_img_tag(56)
    st.sidebar.markdown(
        f"""
        <div style="padding:1.2rem 1.1rem 0.9rem;
                    border-bottom:1px solid rgba(255,255,255,0.07);
                    display:flex;align-items:center;gap:11px;">
            <div style="flex-shrink:0;border-radius:14px;overflow:hidden;
                        box-shadow:0 4px 14px rgba(255,68,88,0.22);">
                {logo_html}
            </div>
            <div>
                <div style="font-family:'DM Sans',sans-serif;font-size:1rem;font-weight:800;
                            color:#fff;letter-spacing:-0.03em;line-height:1.1;">HomeRun</div>
                <div style="font-size:0.65rem;color:rgba(255,255,255,0.35);
                            font-weight:600;letter-spacing:0.05em;margin-top:3px;">
                    SG Flat Finder
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Nav ───────────────────────────────────────────────────────────────────
    st.sidebar.markdown(
        '<div class="nw-side-nav-label">Navigate</div>',
        unsafe_allow_html=True,
    )

    nav_display = [f"{_PAGE_ICONS[p]}  {p}" for p in PAGES]
    displayed   = st.sidebar.radio(
        "Nav", nav_display,
        index=PAGES.index(st.session_state.active_page),
        label_visibility="collapsed",
    )
    page = PAGES[nav_display.index(displayed)]
    if page != st.session_state.active_page:
        st.session_state.active_page = page
        st.rerun()

    # ── Current deck card ─────────────────────────────────────────────────────
    session = get_active_session()
    if session:
        n_liked  = len(session["liked_ids"])
        n_passed = len(session["passed_ids"])
        n_unseen = len(session["unseen_ids"])
        total    = n_liked + n_passed + n_unseen
        seen     = n_liked + n_passed
        pct      = int(seen / total * 100) if total else 0
        circ     = 213.6
        arc      = round(pct / 100 * circ, 1)

        st.sidebar.markdown(
            f"""
            <div class="nw-deck-card">
                <div class="nw-deck-label">Current deck</div>
                <div class="nw-deck-session-name">{session['label']}</div>
                <div class="nw-deck-ring-row">
                    <svg width="72" height="72" viewBox="0 0 80 80">
                        <circle cx="40" cy="40" r="34" fill="none"
                                stroke="rgba(255,255,255,0.10)" stroke-width="6"/>
                        <circle cx="40" cy="40" r="34" fill="none"
                                stroke="#FF6B6B" stroke-width="6"
                                stroke-dasharray="{arc} {circ}"
                                stroke-linecap="round"
                                transform="rotate(-90 40 40)"/>
                        <text x="40" y="46" text-anchor="middle"
                              fill="white" font-size="15" font-weight="800"
                              font-family="DM Sans, sans-serif">{pct}%</text>
                    </svg>
                    <div class="nw-deck-ring-meta">
                        <div class="nw-deck-ring-meta-item">
                            <span class="nw-deck-big" style="color:#FF6B6B;">{n_liked}</span>
                            <span class="nw-deck-key">♥ saved</span>
                        </div>
                        <div class="nw-deck-ring-meta-item">
                            <span class="nw-deck-big"
                                  style="color:rgba(255,255,255,0.9);">{n_unseen}</span>
                            <span class="nw-deck-key">left</span>
                        </div>
                        <div class="nw-deck-ring-meta-item">
                            <span class="nw-deck-big"
                                  style="color:rgba(255,255,255,0.35);">{n_passed}</span>
                            <span class="nw-deck-key">✕ passed</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.sidebar.markdown('<div class="nw-new-search">', unsafe_allow_html=True)
        if st.sidebar.button("🔍  New search", use_container_width=True):
            st.session_state.onboarding_step     = 1
            st.session_state.onboarding_complete = False
            st.session_state.active_page         = "Discover"
            st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # ── Logged-in-as footer ───────────────────────────────────────────────────
    user  = st.session_state.get("current_user", "")
    uname = user.split("@")[0] if "@" in user else user
    st.sidebar.markdown(
        f"""
        <div style="padding:0.85rem 1.1rem 0.7rem;border-top:1px solid rgba(255,255,255,0.07);
                    margin-top:auto;">
            <div style="font-size:0.68rem;color:rgba(255,255,255,0.32);font-weight:600;">
                Signed in as</div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.65);font-weight:600;
                        margin-top:2px;white-space:nowrap;overflow:hidden;
                        text-overflow:ellipsis;">{uname}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Onboarding ────────────────────────────────────────────────────────────────

def _run_onboarding():
    done = render_onboarding()
    if done:
        with st.spinner("Building your personalised deck…"):
            inputs     = build_inputs_from_prefs()
            bundle     = get_prediction_bundle(inputs)
            map_bundle = get_map_bundle(inputs, bundle["recommendations_df"])
        create_search_session(inputs, bundle, map_bundle)
        st.rerun()


# ── Discover ──────────────────────────────────────────────────────────────────

def _render_discover():
    from frontend.state.session import get_active_session

    session = get_active_session()
    if session is None:
        st.info("No active session. Complete onboarding to get started.")
        return

    bundle     = session["bundle"]
    inputs     = session["inputs"]
    map_bundle = session["map_bundle"]

    deck_tab, insights_tab, map_tab = st.tabs([
        "🃏 Discover",
        "📊 Insights",
        "📍 Map",
    ])

    with deck_tab:
        _render_value_strip(bundle, inputs)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        render_listing_tab(bundle["listings_df"])

    with insights_tab:
        render_nestwise_pick(inputs, bundle)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        render_value_cards(bundle, inputs.budget)
        render_budget_banner(bundle, inputs.budget)
        st.markdown("---")
        render_price_story_tab(bundle)
        st.markdown("---")
        render_section("M", "Methodology", "How HomeRun generates its estimates.")
        render_methodology()

    with map_tab:
        render_map_tab(inputs, map_bundle)


def _render_value_strip(bundle: dict, inputs):
    pred   = bundle.get("predicted_price", 0)
    budget = inputs.budget
    diff   = ((budget - pred) / pred * 100) if pred else 0
    sign   = "+" if diff >= 0 else ""
    color  = "#059669" if diff >= 0 else "#e11d48"
    bg     = "rgba(5,150,105,0.07)" if diff >= 0 else "rgba(225,29,72,0.07)"
    border = "rgba(5,150,105,0.20)" if diff >= 0 else "rgba(225,29,72,0.20)"

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;
                    background:#f8fafc;border:1px solid #eef2f7;border-radius:16px;
                    margin-bottom:6px;overflow:hidden;">
            <div style="flex:1;padding:10px 16px;">
                <div style="font-size:0.60rem;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.09em;color:#94a3b8;">Predicted</div>
                <div style="font-size:1.0rem;font-weight:800;color:#0f172a;
                             letter-spacing:-0.025em;margin-top:1px;">
                    S${pred:,.0f}
                </div>
            </div>
            <div style="width:1px;height:36px;background:#e8edf4;flex-shrink:0;"></div>
            <div style="flex:1;padding:10px 16px;">
                <div style="font-size:0.60rem;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.09em;color:#94a3b8;">Your budget</div>
                <div style="font-size:1.0rem;font-weight:800;color:#0f172a;
                             letter-spacing:-0.025em;margin-top:1px;">
                    S${budget:,.0f}
                </div>
            </div>
            <div style="width:1px;height:36px;background:#e8edf4;flex-shrink:0;"></div>
            <div style="flex:1;padding:10px 16px;background:{bg};border-left:2px solid {border};">
                <div style="font-size:0.60rem;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.09em;color:#94a3b8;">Headroom</div>
                <div style="font-size:1.0rem;font-weight:800;color:{color};
                             letter-spacing:-0.025em;margin-top:1px;">
                    {sign}{diff:.1f}%
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Compare ───────────────────────────────────────────────────────────────────

def _render_compare():
    from frontend.state.session import get_liked_df

    selected_ids = st.session_state.get("compare_selected_ids", [])

    if not selected_ids:
        st.markdown(
            "<h2 style='font-size:1.65rem;font-weight:800;letter-spacing:-0.03em;"
            "color:#1a1a2e;margin-bottom:0.8rem;'>Comparison</h2>",
            unsafe_allow_html=True,
        )
        st.info("Select flats in the **Saved** tab to compare them here. You need at least 2.")
        if st.button("Go to Saved →", type="primary"):
            st.session_state.active_page = "Saved"
            st.rerun()
        return

    liked_df = get_liked_df()
    if liked_df.empty:
        st.info("No saved flats found.")
        return

    compare_df = liked_df[liked_df["listing_id"].isin(selected_ids)]
    if len(compare_df) < 2:
        st.warning("Please select at least 2 flats in the Saved tab.")
        return

    session = st.session_state.search_sessions[0] if st.session_state.search_sessions else None
    if session is None:
        st.error("No session found.")
        return

    render_comparison_page(inputs=session["inputs"], listings_df=compare_df)


if __name__ == "__main__":
    main()
