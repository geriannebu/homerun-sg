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
        return st.session_state.get("done_confirmed", False)

    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ── Step 0: Welcome ──────────────────────────────────────────────────────────

def _render_welcome():
    components.html(
        """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;font-family:'DM Sans',-apple-system,sans-serif;background:transparent;overflow:hidden;}

/* floating animations */
@keyframes f1{0%,100%{transform:translate(0,0) rotate(0deg)}25%{transform:translate(14px,-22px) rotate(10deg)}75%{transform:translate(-10px,14px) rotate(-7deg)}}
@keyframes f2{0%,100%{transform:translate(0,0) rotate(0deg)}33%{transform:translate(-18px,16px) rotate(-12deg)}67%{transform:translate(13px,-11px) rotate(8deg)}}
@keyframes f3{0%,100%{transform:translate(0,0) rotate(0deg)}50%{transform:translate(11px,20px) rotate(15deg)}}
@keyframes f4{0%,100%{transform:translate(0,0) rotate(0deg)}40%{transform:translate(-13px,-18px) rotate(-9deg)}80%{transform:translate(9px,9px) rotate(5deg)}}
@keyframes f5{0%,100%{transform:translate(0,0) rotate(0deg)}30%{transform:translate(17px,11px) rotate(13deg)}70%{transform:translate(-15px,-13px) rotate(-8deg)}}
@keyframes f6{0%,100%{transform:translate(0,0) rotate(0deg)}50%{transform:translate(-9px,22px) rotate(-14deg)}}

/* content reveals */
@keyframes up{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}
@keyframes pop{from{opacity:0;transform:scale(0.35) rotate(-8deg)}to{opacity:1;transform:scale(1) rotate(0deg)}}
@keyframes shine{0%{background-position:200% center}100%{background-position:-200% center}}
@keyframes pulse{0%,100%{opacity:0.5}50%{opacity:0.9}}

.scene{
  position:relative;width:100%;height:490px;overflow:hidden;
  background:linear-gradient(155deg,#07071a 0%,#0f0823 55%,#07071a 100%);
  border-radius:24px;
}
.glow{
  position:absolute;top:28%;left:50%;transform:translate(-50%,-50%);
  width:500px;height:300px;
  background:radial-gradient(ellipse,rgba(255,68,88,0.20) 0%,transparent 65%);
  animation:pulse 4s ease-in-out infinite;pointer-events:none;
}
.p{position:absolute;line-height:1;}

/* center column */
.centre{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;z-index:10;padding:1.5rem 2rem;text-align:center;
}
.hero-emoji{
  font-size:4.2rem;line-height:1;margin-bottom:1rem;
  filter:drop-shadow(0 0 24px rgba(255,68,88,0.60));
  animation:pop 0.75s cubic-bezier(0.22,1,0.36,1) both;animation-delay:0.1s;
}
.eyebrow{
  font-size:0.62rem;font-weight:700;letter-spacing:0.22em;text-transform:uppercase;
  color:rgba(255,140,110,0.85);margin-bottom:0.9rem;
  animation:up 0.5s ease both;animation-delay:0.35s;
}
.line1{
  font-size:clamp(1.9rem,5.5vw,2.8rem);font-weight:800;letter-spacing:-0.05em;
  color:#fff;line-height:1.0;margin-bottom:0.1rem;
  animation:up 0.6s ease both;animation-delay:0.5s;
}
.line2{
  font-size:clamp(1.9rem,5.5vw,2.8rem);font-weight:800;letter-spacing:-0.05em;
  line-height:1.0;margin-bottom:1.5rem;
  background:linear-gradient(120deg,#FF6B6B 0%,#FF4458 30%,#FFB347 60%,#FF6B6B 100%);
  background-size:220% auto;
  -webkit-background-clip:text;background-clip:text;color:transparent;
  animation:up 0.6s ease both,shine 3.5s linear 1.3s infinite;animation-delay:0.6s;animation-fill-mode:both;
}
.sub{
  font-size:0.88rem;color:rgba(255,255,255,0.48);max-width:310px;
  line-height:1.75;font-weight:500;
  animation:up 0.6s ease both;animation-delay:0.78s;
}
</style>
</head>
<body>
<div class="scene">

  <div class="glow"></div>

  <!-- floating emojis -->
  <span class="p" style="top:7%;left:7%;font-size:2.4rem;opacity:0.72;animation:f1 7s ease-in-out infinite;">🏠</span>
  <span class="p" style="top:19%;left:16%;font-size:1.3rem;opacity:0.42;animation:f3 10s ease-in-out infinite;animation-delay:-2.5s;">🌳</span>
  <span class="p" style="top:5%;left:30%;font-size:1rem;opacity:0.28;animation:f2 12s ease-in-out infinite;animation-delay:-5s;">✨</span>

  <span class="p" style="top:6%;right:9%;font-size:2.2rem;opacity:0.65;animation:f2 8.5s ease-in-out infinite;animation-delay:-1s;">🏡</span>
  <span class="p" style="top:21%;right:18%;font-size:1.25rem;opacity:0.45;animation:f4 10.5s ease-in-out infinite;animation-delay:-3.5s;">🔑</span>
  <span class="p" style="top:9%;right:33%;font-size:0.95rem;opacity:0.26;animation:f1 13s ease-in-out infinite;animation-delay:-7s;">💫</span>

  <span class="p" style="top:43%;left:5%;font-size:1.8rem;opacity:0.55;animation:f5 9s ease-in-out infinite;animation-delay:-2s;">👨‍👩‍👧</span>
  <span class="p" style="top:63%;left:11%;font-size:1.1rem;opacity:0.38;animation:f3 13.5s ease-in-out infinite;animation-delay:-6s;">🪴</span>

  <span class="p" style="top:41%;right:5%;font-size:1.9rem;opacity:0.50;animation:f4 8s ease-in-out infinite;animation-delay:-4s;">🛋️</span>
  <span class="p" style="top:63%;right:13%;font-size:1.05rem;opacity:0.35;animation:f6 11.5s ease-in-out infinite;animation-delay:-8s;">💕</span>

  <span class="p" style="bottom:14%;left:8%;font-size:1.5rem;opacity:0.48;animation:f2 9s ease-in-out infinite;animation-delay:-1.8s;">🏘️</span>
  <span class="p" style="bottom:12%;right:10%;font-size:1.6rem;opacity:0.46;animation:f1 7.5s ease-in-out infinite;animation-delay:-4.5s;">🌿</span>
  <span class="p" style="bottom:25%;left:25%;font-size:0.85rem;opacity:0.20;animation:f5 15s ease-in-out infinite;animation-delay:-9s;">✨</span>
  <span class="p" style="bottom:22%;right:27%;font-size:0.85rem;opacity:0.20;animation:f3 12.5s ease-in-out infinite;animation-delay:-10s;">💫</span>
  <span class="p" style="bottom:8%;left:42%;font-size:1rem;opacity:0.28;animation:f6 10s ease-in-out infinite;animation-delay:-3s;">🛏️</span>

  <!-- centre content -->
  <div class="centre">
    <div class="hero-emoji">🔑</div>
    <div class="eyebrow">HomeRun &middot; Singapore</div>
    <div class="line1">Find your flat,</div>
    <div class="line2">the smarter way</div>
    <p class="sub">Answer a few quick questions and we'll build a personalised discovery deck of HDB flats matched to your priorities.</p>
  </div>

</div>
</body>
</html>""",
        height=500,
        scrolling=False,
    )
    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("Get started →", key="welcome_next", type="primary", use_container_width=True):
            st.session_state.onboarding_step = 1
            st.rerun()


# ── Step 1: Budget ───────────────────────────────────────────────────────────

_NO_BUDGET_SENTINEL = 9_999_999   # means "no upper limit" for the backend

def _render_budget():
    _progress_bar(1)
    _step_label(1)
    _heading("What's your budget?", "We'll only show flats you can actually afford.")

    # ── flexible toggle ───────────────────────────────────────────────────────
    saved = st.session_state.get("pref_budget")
    flexible_default = saved == _NO_BUDGET_SENTINEL
    flexible = st.checkbox(
        "I'm flexible — show me everything",
        value=flexible_default,
        key="_bgt_flexible",
    )

    if flexible:
        st.markdown(
            "<div style='text-align:center;padding:1.4rem 0 1rem;'>"
            "<div style='font-size:2.8rem;margin-bottom:0.5rem;'>🔓</div>"
            "<div style='font-family:\"DM Sans\",sans-serif;font-size:1rem;"
            "font-weight:700;color:#0b132d;margin-bottom:0.3rem;'>"
            "No budget limit set</div>"
            "<div style='font-size:0.82rem;color:#94a3b8;font-weight:500;'>"
            "We'll show you all available flats — you can always filter later.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        budget = _NO_BUDGET_SENTINEL

    else:
        # ── seed both widget keys from saved pref on first entry ──────────────
        init = (saved if saved and saved != _NO_BUDGET_SENTINEL else None) or 650_000
        if "_bgt_slider" not in st.session_state or \
                st.session_state._bgt_slider == _NO_BUDGET_SENTINEL:
            st.session_state._bgt_slider = init
        if "_bgt_input" not in st.session_state or \
                st.session_state._bgt_input == _NO_BUDGET_SENTINEL:
            st.session_state._bgt_input = init

        # ── callbacks: each writes into the OTHER widget's key ────────────────
        def _on_slider():
            st.session_state._bgt_input = st.session_state._bgt_slider

        def _on_input():
            val = max(200_000, min(1_500_000,
                  round(st.session_state._bgt_input / 10_000) * 10_000))
            st.session_state._bgt_slider = val
            st.session_state._bgt_input  = val

        # ── big editable figure ───────────────────────────────────────────────
        st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)
        pre, inp, _ = st.columns([0.18, 1, 0.18])
        with pre:
            st.markdown(
                "<div style='font-family:\"DM Sans\",sans-serif;font-size:2rem;"
                "font-weight:800;letter-spacing:-0.04em;color:#0b132d;"
                "padding-top:0.55rem;text-align:right;'>S$</div>",
                unsafe_allow_html=True,
            )
        with inp:
            st.number_input(
                "Budget amount",
                min_value=200_000, max_value=1_500_000,
                step=10_000,
                key="_bgt_input",
                label_visibility="collapsed",
                on_change=_on_input,
            )

        st.slider(
            "Budget",
            min_value=200_000, max_value=1_500_000,
            step=10_000,
            format="S$%d",
            key="_bgt_slider",
            label_visibility="collapsed",
            on_change=_on_slider,
        )
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
        budget = st.session_state._bgt_slider

    if _next_btn(key="budget_next"):
        st.session_state.pref_budget = budget
        for k in ("_bgt_slider", "_bgt_input", "_bgt_flexible"):
            st.session_state.pop(k, None)
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
    Shows the animated completion screen.
    onboarding_complete is only set True when the user clicks the CTA —
    this lets the animation play fully before app.py triggers the search.
    """
    components.html(
        """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{
  width:100%;height:100%;
  font-family:'DM Sans',-apple-system,sans-serif;
  background:#ffffff;
  display:flex;align-items:center;justify-content:center;
  overflow:hidden;
}

@keyframes pop     {from{opacity:0;transform:scale(0.3) rotate(-12deg)}to{opacity:1;transform:scale(1) rotate(0deg)}}
@keyframes ring-in {from{opacity:0;transform:rotate(var(--r)) translateX(92px) scale(0)}
                    to  {opacity:1;transform:rotate(var(--r)) translateX(92px) scale(1)}}
@keyframes up      {from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
@keyframes shine   {0%{background-position:200% center}100%{background-position:-200% center}}
@keyframes pulse   {0%,100%{opacity:0.35}50%{opacity:0.65}}
@keyframes spin-slow{to{transform:rotate(360deg)}}

/* page wrapper — centred column */
.wrap{
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center;
  width:100%;padding:2rem 1.5rem;
}

/* orbital stage — ring + hero sit here */
.stage{
  position:relative;
  width:220px;height:220px;
  flex-shrink:0;
  margin-bottom:1.6rem;
}
/* soft radial glow behind hero */
.glow{
  position:absolute;inset:-20px;border-radius:50%;
  background:radial-gradient(ellipse,rgba(255,68,88,0.14) 0%,transparent 68%);
  animation:pulse 3.5s ease-in-out infinite;
}
/* slow-spin dashed orbit ring */
.ring-track{
  position:absolute;inset:10px;border-radius:50%;
  border:1.5px dashed rgba(255,107,107,0.25);
  animation:spin-slow 20s linear infinite;
}
/* hero emoji — dead centre of stage */
.hero{
  position:absolute;inset:0;
  display:flex;align-items:center;justify-content:center;
  font-size:4rem;line-height:1;
  filter:drop-shadow(0 4px 16px rgba(255,68,88,0.28));
  animation:pop 0.7s cubic-bezier(0.22,1,0.36,1) both;animation-delay:0.08s;
}
/* orbital emoji spots */
.orb{
  position:absolute;
  top:50%;left:50%;
  width:0;height:0;
  font-size:1.35rem;line-height:1;
  /* each orb rotates to its angle then steps outward */
  transform:rotate(var(--r)) translateX(92px) translateY(-50%);
  animation:ring-in 0.45s cubic-bezier(0.22,1,0.36,1) both;
  animation-delay:var(--d);
}

/* text block */
.eyebrow{
  font-size:0.6rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
  color:#FF6B6B;margin-bottom:0.65rem;
  animation:up 0.45s ease both;animation-delay:0.92s;
}
.headline{
  font-size:2.2rem;font-weight:800;letter-spacing:-0.05em;line-height:1.05;
  margin-bottom:0.6rem;
  background:linear-gradient(120deg,#FF6B6B 0%,#FF4458 35%,#FF8C69 65%,#FF6B6B 100%);
  background-size:220% auto;
  -webkit-background-clip:text;background-clip:text;color:transparent;
  animation:up 0.5s ease both,shine 3.5s linear 2s infinite;
  animation-delay:1.05s;animation-fill-mode:both;
}
.sub{
  font-size:0.86rem;color:#64748b;font-weight:500;
  max-width:270px;line-height:1.65;
  animation:up 0.45s ease both;animation-delay:1.2s;
}
</style>
</head>
<body>
<div class="wrap">

  <!-- orbital stage -->
  <div class="stage">
    <div class="glow"></div>
    <div class="ring-track"></div>

    <!-- 8 orbital emojis, 45° apart, staggered in -->
    <span class="orb" style="--r:0deg;   --d:0.30s;">🏠</span>
    <span class="orb" style="--r:45deg;  --d:0.40s;">🔑</span>
    <span class="orb" style="--r:90deg;  --d:0.50s;">💕</span>
    <span class="orb" style="--r:135deg; --d:0.60s;">🌳</span>
    <span class="orb" style="--r:180deg; --d:0.68s;">🛋️</span>
    <span class="orb" style="--r:225deg; --d:0.74s;">🪴</span>
    <span class="orb" style="--r:270deg; --d:0.80s;">✨</span>
    <span class="orb" style="--r:315deg; --d:0.86s;">🌿</span>

    <!-- hero -->
    <div class="hero">🎯</div>
  </div>

  <!-- text -->
  <div class="eyebrow">Preferences saved</div>
  <div class="headline">You're all set!</div>
  <p class="sub">Your personalised flat deck is ready to be built — hit the button below when you're ready.</p>

</div>
</body>
</html>""",
        height=400,
        scrolling=False,
    )

    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("Build my deck →", key="done_cta", type="primary",
                     use_container_width=True):
            st.session_state.done_confirmed = True
            st.rerun()


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
