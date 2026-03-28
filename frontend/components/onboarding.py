"""
frontend/components/onboarding.py

Conversational, step-by-step onboarding that collects user preferences.
Each step occupies the full screen — one question at a time, Tinder-style.

Steps:
  0  Welcome screen
  1  Budget
  2  Flat type  (chip select)
  3  Floor area
  4  Remaining lease
  5  Town preference
  6  Amenity ranking  (sequential chip pick — "choose your next most important")
  7  Anchor postals   (optional)
  8  Done → triggers search
"""

import streamlit as st
import streamlit.components.v1 as components

from backend.utils.constants import FLAT_TYPES, TOWNS, AMENITY_LABELS
from backend.schemas.inputs import UserInputs
from frontend.components.hero import get_logo_img_tag


TOTAL_STEPS = 9   # steps 1-9, step 0 is welcome

AMENITY_ICONS = {
    "mrt":        "🚇",
    "bus":        "🚌",
    "healthcare": "🏥",
    "schools":    "🏫",
    "hawker":     "🍜",
    "retail":     "🛍️",
}

FLAT_TYPE_LABELS = {
    "2 ROOM": "2-Room",
    "3 ROOM": "3-Room",
    "4 ROOM": "4-Room",
    "5 ROOM": "5-Room",
    "EXECUTIVE": "Executive",
}

FLAT_ICONS = {
    "2 ROOM": "🏠", "3 ROOM": "🏡", "4 ROOM": "🏘️",
    "5 ROOM": "🏗️", "EXECUTIVE": "🏛️",
}


ACCENT = "#FF4458"
ACCENT_BG = "rgba(255,68,88,0.08)"
ACCENT_BORDER = "#FF4458"


def _progress_bar(step: int):
    pct = int((step / TOTAL_STEPS) * 100)
    st.markdown(
        f"""
        <div style="width:100%;background:#f1f5f9;border-radius:6px;height:5px;margin-bottom:1.6rem;
                    box-shadow:inset 0 1px 3px rgba(0,0,0,0.06);">
            <div style="width:{pct}%;
                        background:linear-gradient(90deg,#FF4458,#FF6B6B);
                        height:5px;border-radius:6px;
                        transition:width 0.4s cubic-bezier(0.22,1,0.36,1);
                        box-shadow:0 2px 8px rgba(255,68,88,0.35);"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _step_label(step: int):
    st.markdown(
        f"<p style='font-family:\"DM Sans\",sans-serif;font-size:0.70rem;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:0.12em;color:#FF4458;margin-bottom:0.3rem;'>"
        f"Step {step} of {TOTAL_STEPS}</p>",
        unsafe_allow_html=True,
    )


def _heading(text: str, sub: str = ""):
    st.markdown(
        f"<h2 style='font-family:\"DM Sans\",sans-serif;font-size:1.75rem;font-weight:800;"
        f"letter-spacing:-0.04em;color:#0b132d;margin-bottom:{'0.3rem' if sub else '1.2rem'};'>{text}</h2>",
        unsafe_allow_html=True,
    )
    if sub:
        st.markdown(
            f"<p style='font-size:0.92rem;color:#64748b;margin-bottom:1.2rem;font-weight:500;'>{sub}</p>",
            unsafe_allow_html=True,
        )


def _next_btn(label: str = "Continue →", key: str = "next"):
    col = st.columns([1, 2, 1])[1]
    with col:
        return st.button(label, key=key, type="primary", use_container_width=True)


def _back_btn(key: str = "back"):
    if st.session_state.onboarding_step > 1:
        if st.button("← Back", key=key):
            st.session_state.onboarding_step -= 1
            st.rerun()


def render_onboarding() -> bool:
    """
    Renders the onboarding flow.
    Returns True when onboarding is complete and inputs are ready.
    """
    step = st.session_state.onboarding_step

    # Outer container — centred, max-width
    st.markdown(
        "<div style='max-width:560px;margin:0 auto;padding:2rem 0.5rem;'>",
        unsafe_allow_html=True,
    )

    if step == 0:
        _render_welcome()
    elif step == 1:
        _render_budget()
    elif step == 2:
        _render_flat_type()
    elif step == 3:
        _render_floor_area()
    elif step == 4:
        _render_lease()
    elif step == 5:
        _render_town()
    elif step == 6:
        _render_amenity_ranking()
    elif step == 7:
        _render_lifestyle()
    elif step == 8:
        _render_anchors()
    elif step == 9:
        _render_done()
        st.markdown("</div>", unsafe_allow_html=True)
        return True

    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ── Step 0: Welcome ──────────────────────────────────────────────────────────

def _render_welcome():
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="text-align:center;padding:1.5rem 0 2rem;">
            <div style="position:relative;display:inline-block;margin-bottom:1.2rem;">
                <div style="position:absolute;inset:-8px;border-radius:30px;
                            background:conic-gradient(from 0deg,rgba(255,68,88,0.50),rgba(255,107,107,0.14),rgba(255,68,88,0.50));
                            animation:nw-spin 8s linear infinite;"></div>
                <div style="position:absolute;inset:-2px;border-radius:24px;background:#fafafa;"></div>
                <div style="position:relative;z-index:1;border-radius:22px;overflow:hidden;
                            background:#fff;
                            box-shadow:0 0 0 1px rgba(255,68,88,0.10),0 10px 32px rgba(255,68,88,0.14);">
                    {get_logo_img_tag(96)}
                </div>
            </div>
            <style>@keyframes nw-spin{{to{{transform:rotate(360deg)}}}}</style>
            <h1 style="font-family:'DM Sans',sans-serif;font-size:2.1rem;font-weight:800;
                       letter-spacing:-0.045em;color:#0b132d;margin-bottom:0.6rem;line-height:1.05;">
                Find your flat,<br>the smarter way
            </h1>
            <p style="font-size:0.95rem;color:#64748b;max-width:380px;
                      margin:0 auto 2rem;line-height:1.7;font-weight:500;">
                Answer a few quick questions and we'll build a personalised
                discovery deck of HDB flats matched to your priorities.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("Get started →", key="welcome_next", type="primary", use_container_width=True):
            st.session_state.onboarding_step = 1
            st.rerun()


# ── Step 1: Budget ───────────────────────────────────────────────────────────

def _render_budget():
    _progress_bar(1)
    _step_label(1)
    _heading("What's your budget?", "We'll only show flats you can actually afford.")

    budget = st.slider(
        "Budget",
        min_value=200000, max_value=1500000,
        value=st.session_state.get("pref_budget") or 650000,
        step=10000,
        format="S$%d",
        label_visibility="collapsed",
    )
    st.markdown(
        f"<div style='text-align:center;font-family:\"DM Sans\",sans-serif;"
        f"font-size:2.4rem;font-weight:800;"
        f"letter-spacing:-0.05em;color:#0b132d;margin:0.4rem 0 1.6rem;'>"
        f"S${budget:,}</div>",
        unsafe_allow_html=True,
    )

    if _next_btn(key="budget_next"):
        st.session_state.pref_budget = budget
        st.session_state.onboarding_step = 2
        st.rerun()
    _back_btn("budget_back")


# ── Step 2: Flat type ────────────────────────────────────────────────────────

def _render_flat_type():
    _progress_bar(2)
    _step_label(2)
    _heading("What type of flat?", "Choose the size that works for you.")

    current = st.session_state.get("pref_flat_type") or "4 ROOM"

    cols = st.columns(len(FLAT_TYPES))
    for i, ft in enumerate(FLAT_TYPES):
        selected = current == ft
        with cols[i]:
            if st.button(
                f"{FLAT_ICONS[ft]} {FLAT_TYPE_LABELS[ft]}",
                key=f"ft_{ft}",
                use_container_width=True,
                type="primary" if selected else "secondary",
            ):
                st.session_state.pref_flat_type = ft
                st.rerun()

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    if _next_btn(key="ft_next"):
        if not st.session_state.get("pref_flat_type"):
            st.session_state.pref_flat_type = "4 ROOM"
        st.session_state.onboarding_step = 3
        st.rerun()
    _back_btn("ft_back")


# ── Step 3: Floor area ───────────────────────────────────────────────────────

def _render_floor_area():
    _progress_bar(3)
    _step_label(3)
    _heading("How much space do you need?", "Approximate floor area in square metres.")

    area = st.slider(
        "Floor area",
        min_value=35, max_value=160,
        value=st.session_state.get("pref_floor_area") or 95,
        step=5,
        format="%d sqm",
        label_visibility="collapsed",
    )
    st.markdown(
        f"<div style='text-align:center;font-size:2.2rem;font-weight:800;"
        f"letter-spacing:-0.04em;color:#0f172a;margin:0.4rem 0 1.6rem;'>"
        f"{area} sqm</div>",
        unsafe_allow_html=True,
    )

    if _next_btn(key="area_next"):
        st.session_state.pref_floor_area = area
        st.session_state.onboarding_step = 4
        st.rerun()
    _back_btn("area_back")


# ── Step 4: Remaining lease ──────────────────────────────────────────────────

def _render_lease():
    _progress_bar(4)
    _step_label(4)
    _heading("Minimum remaining lease?",
             "HDB flats have 99-year leases. How many years must be left?")

    lease = st.slider(
        "Remaining lease",
        min_value=20, max_value=95,
        value=st.session_state.get("pref_remaining_lease") or 60,
        step=1,
        format="%d years",
        label_visibility="collapsed",
    )

    # Helper labels
    if lease >= 80:   hint = "Near-new flat"
    elif lease >= 60: hint = "Plenty of lease left"
    elif lease >= 40: hint = "Moderate — check CPF rules"
    else:             hint = "Short lease — financing may be limited"

    st.markdown(
        f"<div style='text-align:center;margin:0.4rem 0 0.6rem;'>"
        f"<span style='font-size:2.2rem;font-weight:800;letter-spacing:-0.04em;"
        f"color:#0f172a;'>{lease} years</span></div>"
        f"<div style='text-align:center;font-size:0.82rem;color:#9ca3af;"
        f"margin-bottom:1.6rem;'>{hint}</div>",
        unsafe_allow_html=True,
    )

    if _next_btn(key="lease_next"):
        st.session_state.pref_remaining_lease = lease
        st.session_state.onboarding_step = 5
        st.rerun()
    _back_btn("lease_back")


# ── Step 5: Town ─────────────────────────────────────────────────────────────

def _render_town():
    _progress_bar(5)
    _step_label(5)
    _heading("Any preferred town?", "Skip to let us recommend the best match.")

    current = st.session_state.get("pref_town")
    no_pref = current is None

    if st.button(
        "🗺️  Recommend the best town for me",
        key="town_no_pref",
        use_container_width=True,
        type="primary" if no_pref else "secondary",
    ):
        st.session_state.pref_town = None
        st.rerun()

    st.markdown("<div style='margin:10px 0 6px;font-size:0.8rem;color:#9ca3af;font-weight:600;'>OR PICK A TOWN</div>", unsafe_allow_html=True)

    town_choice = st.selectbox(
        "Town",
        ["— select —"] + sorted(TOWNS),
        index=0 if current is None else (sorted(TOWNS).index(current) + 1 if current in TOWNS else 0),
        label_visibility="collapsed",
    )
    if town_choice != "— select —" and town_choice != current:
        st.session_state.pref_town = town_choice
        st.rerun()

    if _next_btn(key="town_next"):
        st.session_state.onboarding_step = 6
        st.rerun()
    _back_btn("town_back")


# ── Step 6: Amenity ranking ──────────────────────────────────────────────────
# UX pattern: "Choose your next most important amenity" sequential pick.
# User taps chips one by one; each pick appends to the ranked list.
# Once all 6 are ranked, we show the result and allow re-ordering by clicking
# the ranked list to remove the last pick.

def _render_amenity_ranking():
    _progress_bar(6)
    _step_label(6)

    ranked: list = st.session_state.get("pref_amenity_rank") or []
    all_keys = list(AMENITY_LABELS.keys())
    remaining = [k for k in all_keys if k not in ranked]

    if not ranked:
        _heading("What matters most to you?",
                 "Tap amenities in order of priority — most important first.")
    elif len(ranked) < len(all_keys):
        next_pos = len(ranked) + 1
        _heading(f"What's your #{next_pos} priority?",
                 "Keep going — tap the next most important amenity.")
    else:
        _heading("Your priority ranking is set ✓",
                 "Tap any item to remove it and re-rank from that point.")

    # Show already-ranked items
    if ranked:
        for i, key in enumerate(ranked):
            icon  = AMENITY_ICONS[key]
            label = AMENITY_LABELS[key]
            pos   = i + 1
            col_info, col_rm = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"""<div style="display:flex;align-items:center;gap:12px;
                        padding:10px 14px;background:#f9f9f9;border:1px solid #f0f0f0;
                        border-radius:10px;">
                        <span style="font-size:0.72rem;font-weight:800;color:{ACCENT};
                              min-width:18px;">#{pos}</span>
                        <span style="font-size:1.1rem;">{icon}</span>
                        <span style="font-size:0.88rem;font-weight:600;color:#1a1a2e;
                              flex:1;">{label}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col_rm:
                if st.button("✕", key=f"remove_{key}", use_container_width=True):
                    st.session_state.pref_amenity_rank = ranked[:i]
                    st.rerun()
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Show remaining chips
    if remaining:
        st.markdown("<div style='margin:12px 0 8px;font-size:0.78rem;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;'>AVAILABLE</div>", unsafe_allow_html=True)
        chip_cols = st.columns(3)
        for i, key in enumerate(remaining):
            with chip_cols[i % 3]:
                icon  = AMENITY_ICONS[key]
                label = AMENITY_LABELS[key]
                if st.button(f"{icon} {label}", key=f"pick_{key}",
                             use_container_width=True):
                    new_rank = (st.session_state.pref_amenity_rank or []) + [key]
                    st.session_state.pref_amenity_rank = new_rank
                    st.rerun()

    # Continue once all ranked
    if len(ranked) == len(all_keys):
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
        if _next_btn("Looks good →", key="amenity_next"):
            st.session_state.onboarding_step = 7
            st.rerun()

    _back_btn("amenity_back")



# ── Step 7: Lifestyle quiz ───────────────────────────────────────────────────

LIFESTYLE_QUESTIONS = [
    ("Which describes your typical evening?", [
        ("🍜  Hawker food", {"hawker": 3}),
        ("🛍️  Mall dinner",  {"retail": 3}),
        ("🍳  Cook at home", {"hawker": 1}),
    ]),
    ("How do you usually commute?", [
        ("🚇  MRT",        {"mrt": 3}),
        ("🚌  Bus",        {"bus": 3}),
        ("🚗  Car / Grab", {}),
    ]),
    ("What do you enjoy most on weekends?", [
        ("🛍️  Shopping & cafés",  {"retail": 3}),
        ("🍜  Food hunting",       {"hawker": 3}),
        ("🏫  Family / kids time", {"schools": 3}),
    ]),
]


def _render_lifestyle():
    _progress_bar(7)
    _step_label(7)

    q_idx = st.session_state.get("lifestyle_q", 0)

    if q_idx < len(LIFESTYLE_QUESTIONS):
        q, opts = LIFESTYLE_QUESTIONS[q_idx]
        _heading("Your lifestyle", q)

        # Sub-progress dots
        dots_html = "<div style='display:flex;gap:6px;justify-content:center;margin-bottom:1.4rem;'>"
        for i in range(len(LIFESTYLE_QUESTIONS)):
            if i < q_idx:
                col = ACCENT
                w = "16px"
                r = "3px"
            elif i == q_idx:
                col = ACCENT
                w = "24px"
                r = "3px"
            else:
                col = "#e2e8f0"
                w = "8px"
                r = "50%"
            dots_html += f"<div style='width:{w};height:8px;border-radius:{r};background:{col};transition:all 0.2s;'></div>"
        dots_html += "</div>"
        st.markdown(dots_html, unsafe_allow_html=True)

        cols = st.columns(len(opts))
        for i, (label, score) in enumerate(opts):
            with cols[i]:
                if st.button(label, key=f"ls_q{q_idx}_{i}", use_container_width=True):
                    # Accumulate lifestyle weights into amenity rank boosts
                    existing = st.session_state.get("lifestyle_boosts", {})
                    for k, v in score.items():
                        existing[k] = existing.get(k, 0) + v
                    st.session_state["lifestyle_boosts"] = existing
                    st.session_state["lifestyle_q"] = q_idx + 1
                    st.rerun()

        # Back within lifestyle sub-steps
        if q_idx > 0:
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
            if st.button("← Previous question", key=f"ls_back_{q_idx}"):
                st.session_state["lifestyle_q"] = q_idx - 1
                st.rerun()

    else:
        # All lifestyle questions answered — show summary and continue
        _heading("Lifestyle captured ✓", "We'll use this to fine-tune your recommendations.")

        boosts = st.session_state.get("lifestyle_boosts", {})
        if boosts:
            top = sorted(boosts.items(), key=lambda x: -x[1])
            summary_parts = []
            for k, v in top[:2]:
                icon = AMENITY_ICONS.get(k, "")
                label = {"mrt": "MRT access", "bus": "bus routes", "healthcare": "healthcare",
                         "schools": "schools", "hawker": "hawker food", "retail": "shopping"}.get(k, k)
                summary_parts.append(f"{icon} {label}")
            if summary_parts:
                st.markdown(
                    f"<p style='font-size:0.88rem;color:#64748b;text-align:center;"
                    f"margin-bottom:1.4rem;'>Top priorities detected: "
                    f"<strong style='color:#0b132d;'>{' · '.join(summary_parts)}</strong></p>",
                    unsafe_allow_html=True,
                )

        if _next_btn("Next →", key="lifestyle_next"):
            st.session_state["lifestyle_q"] = 0  # reset for next time
            st.session_state.onboarding_step = 8
            st.rerun()

    _back_btn("lifestyle_step_back")


# ── Step 8: Anchors (optional) ───────────────────────────────────────────────

def _render_anchors():
    _progress_bar(8)
    _step_label(8)
    _heading("Any anchor locations?",
             "Optional: add up to 2 postal codes (workplace, parents, etc.) "
             "so we can factor proximity into your deck.")

    p1, p2 = st.columns(2)
    existing = st.session_state.get("pref_landmark_postals") or []

    with p1:
        v1 = st.text_input("Postal code 1", value=existing[0] if len(existing) > 0 else "",
                           placeholder="e.g. 119077", key="anchor_1")
    with p2:
        v2 = st.text_input("Postal code 2", value=existing[1] if len(existing) > 1 else "",
                           placeholder="e.g. 560215", key="anchor_2")

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Skip this step", key="anchor_skip", use_container_width=True):
            st.session_state.pref_landmark_postals = []
            st.session_state.onboarding_step = 9
            st.rerun()
    with cols[1]:
        if st.button("Save & continue →", key="anchor_next",
                     type="primary", use_container_width=True):
            postals = [p.strip() for p in [v1, v2] if p.strip()]
            st.session_state.pref_landmark_postals = postals
            st.session_state.onboarding_step = 9
            st.rerun()

    _back_btn("anchor_back")


# ── Step 9: Done / trigger search ────────────────────────────────────────────

def _render_done():
    """
    This step finalises inputs and marks onboarding complete.
    The calling code (app.py) will detect step == 8 and trigger the search.
    """
    st.session_state.onboarding_complete = True


# ── Build UserInputs from session state ──────────────────────────────────────

def build_inputs_from_prefs() -> UserInputs:
    """Convert stored onboarding prefs into a UserInputs dataclass."""
    rank = st.session_state.pref_amenity_rank or list(AMENITY_LABELS.keys())
    n    = len(rank)

    # Convert rank to weights: rank[0] gets weight n, rank[-1] gets 1, normalised
    raw_weights = {key: (n - i) for i, key in enumerate(rank)}
    total       = sum(raw_weights.values())
    amenity_weights = {k: v / total for k, v in raw_weights.items()}

    # Ensure all amenity keys present
    for key in AMENITY_LABELS:
        if key not in amenity_weights:
            amenity_weights[key] = 0.0

    return UserInputs(
        budget=st.session_state.pref_budget or 650000,
        flat_type=st.session_state.pref_flat_type or "4 ROOM",
        floor_area_sqm=float(st.session_state.pref_floor_area or 95),
        remaining_lease_years=st.session_state.pref_remaining_lease or 60,
        town=st.session_state.pref_town,
        school_scope=st.session_state.get("pref_school_scope", "Any"),
        amenity_weights=amenity_weights,
        amenity_rank=rank,
        landmark_postals=st.session_state.pref_landmark_postals or [],
    )


def get_preferences_display() -> dict:
    """Return a human-readable dict of current preferences for the Account tab."""
    rank = st.session_state.get("pref_amenity_rank") or []
    return {
        "Budget":          f"S${(st.session_state.pref_budget or 0):,}",
        "Flat type":       FLAT_TYPE_LABELS.get(st.session_state.pref_flat_type or "", "—"),
        "Floor area":      f"{st.session_state.pref_floor_area or '—'} sqm",
        "Min. lease":      f"{st.session_state.pref_remaining_lease or '—'} years remaining",
        "Town":            st.session_state.pref_town or "Recommendation mode",
        "Amenity ranking": " → ".join(
            f"{AMENITY_ICONS.get(k,'')} {AMENITY_LABELS.get(k,k)}" for k in rank
        ) or "—",
        "Anchors":         ", ".join(st.session_state.pref_landmark_postals or []) or "None",
    }
