"""
frontend/components/onboarding.py

Conversational, step-by-step onboarding that collects user preferences.
Each step occupies the full screen — one question at a time, Tinder-style.

New flow:
  0  Welcome screen
  1  Budget
  2  Flat type
  3  Floor area
  4  Minimum remaining lease
  5  Town preference
  6  Priority mode
  7  Preferences quiz
  8  Predicted amenity ranking review / reorder
  9  Anchor postals
 10  Done → triggers search
"""

import streamlit as st
import streamlit.components.v1 as components

from backend.utils.constants import FLAT_TYPES, TOWNS, AMENITY_LABELS
from backend.schemas.inputs import UserInputs

try:
    from streamlit_sortables import sort_items
    HAS_SORTABLES = True
except Exception:
    HAS_SORTABLES = False


TOTAL_STEPS = 10   # steps 1-10, step 0 is welcome

AMENITY_ICONS = {
    "mrt": "🚇",
    "bus": "🚌",
    "healthcare": "🏥",
    "schools": "🏫",
    "hawker": "🍜",
    "retail": "🛍️",
}

FLAT_TYPE_LABELS = {
    "2 ROOM": "2-Room",
    "3 ROOM": "3-Room",
    "4 ROOM": "4-Room",
    "5 ROOM": "5-Room",
    "EXECUTIVE": "Executive",
}

FLAT_ICONS = {
    "2 ROOM": "🏠",
    "3 ROOM": "🏡",
    "4 ROOM": "🏘️",
    "5 ROOM": "🏗️",
    "EXECUTIVE": "🏛️",
}

ACCENT = "#FF4458"
ACCENT_BG = "rgba(255,68,88,0.08)"
ACCENT_BORDER = "#FF4458"


# ── Preferences / lifestyle quiz config ──────────────────────────────────────

LIFESTYLE_QUESTIONS = [
    {
        "id": "evening",
        "title": "Your lifestyle",
        "question": "Which of these feels most like your usual evening?",
        "options": [
            ("Taking the MRT home and grabbing dinner nearby", {"mrt": 3, "hawker": 1}),
            ("Heading somewhere with lots of shops and food options", {"retail": 3, "hawker": 1}),
            ("Keeping things simple at home with easy access to essentials", {"bus": 1, "retail": 1}),
        ],
    },
    {
        "id": "commute_home",
        "title": "Your lifestyle",
        "question": "What makes getting home feel easiest?",
        "options": [
            ("A quick MRT ride", {"mrt": 3, "bus": 1}),
            ("A bus stop close to home", {"bus": 3, "mrt": 1}),
            ("Car / Grab", {"healthcare": 1}),
        ],
    },
    {
        "id": "food_preference",
        "title": "Your lifestyle",
        "question": "How do you prefer to get food?",
        "options": [
            ("Affordable cooked food nearby", {"hawker": 3}),
            ("Food and errands all in one place", {"retail": 3, "hawker": 1}),
            ("I care less about food options than getting around easily", {"mrt": 2, "bus": 2}),
        ],
    },
    {
        "id": "weekday_convenience",
        "title": "Your lifestyle",
        "question": "Which convenience matters to you most?",
        "options": [
            ("Quick access to public transport", {"mrt": 2, "bus": 2}),
            ("A mall nearby for one-stop convenience", {"retail": 3}),
            ("Healthcare nearby for peace of mind", {"healthcare": 3}),
        ],
    },
    {
        "id": "weekend",
        "title": "Your lifestyle",
        "question": "What sounds most like your weekend?",
        "options": [
            ("Buying food nearby and chilling at home", {"hawker": 3, "retail": 1}),
            ("Shopping, cafés, and running errands", {"retail": 3}),
            ("Family-focused plans where nearby schools and amenities matter", {"schools": 3, "healthcare": 1}),
        ],
    },
    {
        "id": "settled_neighbourhood",
        "title": "Your lifestyle",
        "question": "Which would make you feel more settled in a neighbourhood?",
        "options": [
            ("Strong transport connectivity", {"mrt": 2, "bus": 2}),
            ("Good school access for my household", {"schools": 3}),
            ("Healthcare close by", {"healthcare": 3}),
        ],
    },
    {
        "id": "pop_out_quickly",
        "title": "Your lifestyle",
        "question": "If you need to pop out quickly, what would you most want nearby?",
        "options": [
            ("MRT station", {"mrt": 3}),
            ("Bus stop", {"bus": 3}),
            ("Mall with many things in one place", {"retail": 3}),
        ],
    },
    {
        "id": "tradeoff",
        "title": "Your lifestyle",
        "question": "Which trade-off would you choose?",
        "options": [
            ("Near MRT over more food options", {"mrt": 3, "hawker": -1}),
            ("Near hawker over faster transport", {"hawker": 3, "mrt": -1}),
            ("Near schools / healthcare over both", {"schools": 2, "healthcare": 2}),
        ],
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────

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
            if st.session_state.onboarding_step == 8:
                st.session_state.pop("predicted_amenity_rank", None)
                st.session_state.pop("pref_amenity_rank", None)
            st.session_state.onboarding_step -= 1
            st.rerun()


def _default_amenity_order():
    return list(AMENITY_LABELS.keys())


def _compute_predicted_amenity_rank():
    """
    Convert priority mode + lifestyle boosts into a predicted amenity ranking.
    """
    boosts = st.session_state.get("lifestyle_boosts", {}) or {}
    priority_mode = st.session_state.get("pref_priority_mode", "balanced")
    base_order = _default_amenity_order()

    base_scores = {
        "mrt": 1.0,
        "bus": 0.9,
        "healthcare": 0.7,
        "schools": 0.8,
        "hawker": 0.85,
        "retail": 0.75,
    }

    priority_boosts_map = {
        "save_money": {
            "hawker": 2.0,
            "bus": 1.2,
            "mrt": 0.8,
            "retail": -0.3,
        },
        "convenience": {
            "mrt": 2.0,
            "retail": 1.6,
            "bus": 1.2,
            "healthcare": 0.8,
        },
        "balanced": {
            "mrt": 1.0,
            "hawker": 1.0,
            "bus": 1.0,
            "retail": 0.8,
            "healthcare": 0.6,
            "schools": 0.6,
        },
    }

    priority_boosts = priority_boosts_map.get(priority_mode, {})

    scored = []
    for i, key in enumerate(base_order):
        score = (
            base_scores.get(key, 0.5)
            + boosts.get(key, 0)
            + priority_boosts.get(key, 0)
        )
        scored.append((key, score, -i))

    ranked = [k for k, _, _ in sorted(scored, key=lambda x: (x[1], x[2]), reverse=True)]
    return ranked


def _move_item(rank, idx, direction):
    new_rank = rank[:]
    swap_idx = idx + direction
    if 0 <= swap_idx < len(new_rank):
        new_rank[idx], new_rank[swap_idx] = new_rank[swap_idx], new_rank[idx]
    return new_rank


def _render_rank_list_with_buttons(rank):
    st.markdown(
        "<div style='margin:8px 0 12px;font-size:0.78rem;color:#9ca3af;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.07em;'>Your predicted priority order</div>",
        unsafe_allow_html=True,
    )

    for i, key in enumerate(rank):
        pos_col, info_col, up_col, down_col = st.columns([0.7, 5, 1, 1])

        with pos_col:
            st.markdown(
                f"<div style='padding-top:10px;font-weight:800;color:{ACCENT};'>#{i+1}</div>",
                unsafe_allow_html=True,
            )

        with info_col:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
                            background:#f9fafb;border:1px solid #eceff3;border-radius:12px;">
                    <span style="font-size:1.1rem;">{AMENITY_ICONS.get(key, '•')}</span>
                    <span style="font-size:0.92rem;font-weight:600;color:#1a1a2e;">
                        {AMENITY_LABELS.get(key, key)}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with up_col:
            if st.button("↑", key=f"up_{key}", use_container_width=True, disabled=(i == 0)):
                st.session_state.pref_amenity_rank = _move_item(rank, i, -1)
                st.rerun()

        with down_col:
            if st.button("↓", key=f"down_{key}", use_container_width=True, disabled=(i == len(rank) - 1)):
                st.session_state.pref_amenity_rank = _move_item(rank, i, 1)
                st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


def _render_rank_list_sortable(rank):
    st.markdown(
        "<div style='margin:8px 0 12px;font-size:0.78rem;color:#9ca3af;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.07em;'>Drag to reorder</div>",
        unsafe_allow_html=True,
    )

    labels_to_key = {
        f"{AMENITY_ICONS.get(k, '•')} {AMENITY_LABELS.get(k, k)}": k
        for k in rank
    }
    display_items = list(labels_to_key.keys())

    sorted_display = sort_items(
        display_items,
        direction="vertical",
        key="amenity_sortable",
    )

    new_rank = [labels_to_key[label] for label in sorted_display]
    st.session_state.pref_amenity_rank = new_rank


def render_onboarding() -> bool:
    """
    Renders the onboarding flow.
    Returns True when onboarding is complete and inputs are ready.
    """
    step = st.session_state.onboarding_step

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
        _render_priority_mode()
    elif step == 7:
        _render_lifestyle()
    elif step == 8:
        _render_predicted_amenity_ranking()
    elif step == 9:
        _render_anchors()
    elif step == 10:
        _render_done()
        st.markdown("</div>", unsafe_allow_html=True)
        return True

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
@keyframes f1{0%,100%{transform:translate(0,0) rotate(0deg)}25%{transform:translate(14px,-22px) rotate(10deg)}75%{transform:translate(-10px,14px) rotate(-7deg)}}
@keyframes f2{0%,100%{transform:translate(0,0) rotate(0deg)}33%{transform:translate(-18px,16px) rotate(-12deg)}67%{transform:translate(13px,-11px) rotate(8deg)}}
@keyframes f3{0%,100%{transform:translate(0,0) rotate(0deg)}50%{transform:translate(11px,20px) rotate(15deg)}}
@keyframes f4{0%,100%{transform:translate(0,0) rotate(0deg)}40%{transform:translate(-13px,-18px) rotate(-9deg)}80%{transform:translate(9px,9px) rotate(5deg)}}
@keyframes f5{0%,100%{transform:translate(0,0) rotate(0deg)}30%{transform:translate(17px,11px) rotate(13deg)}70%{transform:translate(-15px,-13px) rotate(-8deg)}}
@keyframes f6{0%,100%{transform:translate(0,0) rotate(0deg)}50%{transform:translate(-9px,22px) rotate(-14deg)}}
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
  <div class="centre">
    <div class="hero-emoji">🔑</div>
    <div class="eyebrow">HomeRun · Singapore</div>
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

def _render_budget():
    _progress_bar(1)
    _step_label(1)
    _heading("What's your budget?", "We'll only show flats you can actually afford.")

    if "pref_budget" not in st.session_state or st.session_state.pref_budget is None:
        st.session_state.pref_budget = 650000

    if "budget_slider_value" not in st.session_state or st.session_state.budget_slider_value is None:
        st.session_state.budget_slider_value = st.session_state.pref_budget

    if "budget_display_text" not in st.session_state or not st.session_state.budget_display_text:
        st.session_state.budget_display_text = f"S${st.session_state.pref_budget:,.0f}"

    flexible = st.checkbox(
        "I have a flexible budget / prefer not to set one now",
        value=st.session_state.get("pref_budget_flexible", False),
        key="budget_flexible_checkbox",
    )

    if flexible:
        st.session_state.pref_budget_flexible = True
        st.markdown(
            "<div style='text-align:center;font-size:2rem;font-weight:800;color:#0b132d;"
            "margin:1.2rem 0 1.6rem;'>Flexible budget</div>",
            unsafe_allow_html=True,
        )
        if _next_btn(key="budget_next_flexible"):
            st.session_state.pref_budget = None
            st.session_state.onboarding_step = 2
            st.rerun()

    else:
        st.session_state.pref_budget_flexible = False

        def _sync_from_slider():
            val = int(st.session_state.budget_slider_value)
            st.session_state.pref_budget = val
            st.session_state.budget_display_text = f"S${val:,.0f}"

        def _sync_from_display():
            raw = str(st.session_state.budget_display_text).strip()
            digits = "".join(ch for ch in raw if ch.isdigit())

            if not digits:
                val = st.session_state.pref_budget or 650000
            else:
                val = int(digits)

            val = max(200000, min(1500000, val))
            val = round(val / 10000) * 10000

            st.session_state.pref_budget = val
            st.session_state.budget_slider_value = val
            st.session_state.budget_display_text = f"S${val:,.0f}"

        # hide the ugly small helper text / labels and style big editable display
        st.markdown(
            """
            <style>
            div[data-testid="stTextInput"] label {
                display: none !important;
            }

            div[data-testid="stTextInput"] input {
                text-align: center !important;
                font-family: "DM Sans", sans-serif !important;
                font-size: 2.4rem !important;
                font-weight: 800 !important;
                letter-spacing: -0.05em !important;
                color: #0b132d !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding-top: 0.15rem !important;
                padding-bottom: 0.15rem !important;
            }

            div[data-testid="stTextInput"] > div {
                border: none !important;
                background: transparent !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextInput"] > div > div {
                border: none !important;
                background: transparent !important;
                box-shadow: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.slider(
            "Budget",
            min_value=200000,
            max_value=1500000,
            step=10000,
            key="budget_slider_value",
            on_change=_sync_from_slider,
            label_visibility="collapsed",
        )

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.text_input(
                "Budget display",
                key="budget_display_text",
                on_change=_sync_from_display,
                label_visibility="collapsed",
            )

        if _next_btn(key="budget_next"):
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
        min_value=35,
        max_value=160,
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
    _heading(
        "What is your preferred minimum remaining lease of the flat?",
        "HDB flats have 99-year leases. How many years must be left?"
    )

    lease = st.slider(
        "Remaining lease",
        min_value=20,
        max_value=95,
        value=st.session_state.get("pref_remaining_lease") or 60,
        step=1,
        format="%d years",
        label_visibility="collapsed",
    )

    if lease >= 80:
        hint = "Near-new flat"
    elif lease >= 60:
        hint = "Plenty of lease left"
    elif lease >= 40:
        hint = "Moderate — check CPF rules"
    else:
        hint = "Short lease — financing may be limited"

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
    _heading("Do you have any preferred town in mind?", "Skip to let us recommend the best match.")

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

    st.markdown(
        "<div style='margin:10px 0 6px;font-size:0.8rem;color:#9ca3af;font-weight:600;'>OR PICK A TOWN</div>",
        unsafe_allow_html=True
    )

    sorted_towns = sorted(TOWNS)
    town_choice = st.selectbox(
        "Town",
        ["— select —"] + sorted_towns,
        index=0 if current is None else (sorted_towns.index(current) + 1 if current in TOWNS else 0),
        label_visibility="collapsed",
    )
    if town_choice != "— select —" and town_choice != current:
        st.session_state.pref_town = town_choice
        st.rerun()

    if _next_btn(key="town_next"):
        st.session_state.onboarding_step = 6
        st.rerun()
    _back_btn("town_back")


# ── Step 6: Priority mode ────────────────────────────────────────────────────

def _render_priority_mode():
    _progress_bar(6)
    _step_label(6)
    _heading(
        "What matters most to you?",
        "We'll use this to shape your recommendations before learning more about your lifestyle."
    )

    current = st.session_state.get("pref_priority_mode", "balanced")

    options = [
        ("save_money", "Save money 💵", "Prioritise affordability and value"),
        ("convenience", "Convenience 🚶⏱️", "Prioritise ease, accessibility, and daily convenience"),
        ("balanced", "Balanced 🎯⚖️", "A mix of affordability and convenience"),
    ]

    for key, label, desc in options:
        selected = current == key
        if st.button(
            label,
            key=f"priority_mode_{key}",
            use_container_width=True,
            type="primary" if selected else "secondary",
        ):
            st.session_state.pref_priority_mode = key
            st.rerun()

        st.markdown(
            f"<div style='font-size:0.84rem;color:#64748b;margin:-0.35rem 0 0.8rem 0.2rem;'>{desc}</div>",
            unsafe_allow_html=True,
        )

    if _next_btn(key="priority_mode_next"):
        if "pref_priority_mode" not in st.session_state:
            st.session_state.pref_priority_mode = "balanced"
        st.session_state.onboarding_step = 7
        st.rerun()

    _back_btn("priority_mode_back")


# ── Step 7: Preferences quiz ─────────────────────────────────────────────────

def _render_lifestyle():
    _progress_bar(7)
    _step_label(7)

    q_idx = st.session_state.get("lifestyle_q", 0)
    answers = st.session_state.get("lifestyle_answers", {})

    if q_idx < len(LIFESTYLE_QUESTIONS):
        q_conf = LIFESTYLE_QUESTIONS[q_idx]
        q_id = q_conf["id"]
        q = q_conf["question"]
        opts = q_conf["options"]

        _heading(q_conf["title"], q)

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
                    answers[q_id] = {
                        "label": label,
                        "score": score,
                    }
                    st.session_state["lifestyle_answers"] = answers
                    st.session_state["lifestyle_q"] = q_idx + 1

                    boosts = {}
                    for ans in answers.values():
                        for k, v in ans["score"].items():
                            boosts[k] = boosts.get(k, 0) + v
                    st.session_state["lifestyle_boosts"] = boosts
                    st.rerun()

        if q_idx > 0:
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
            if st.button("← Previous question", key=f"ls_back_{q_idx}"):
                prev_q_id = LIFESTYLE_QUESTIONS[q_idx - 1]["id"]
                answers.pop(prev_q_id, None)
                st.session_state["lifestyle_answers"] = answers
                st.session_state["lifestyle_q"] = q_idx - 1

                boosts = {}
                for ans in answers.values():
                    for k, v in ans["score"].items():
                        boosts[k] = boosts.get(k, 0) + v
                st.session_state["lifestyle_boosts"] = boosts
                st.rerun()

    else:
        _heading(
            "Preferences captured ✓",
            "We’ve predicted your amenity priorities. You can reorder them in the next step."
        )

        boosts = st.session_state.get("lifestyle_boosts", {})
        if boosts:
            top = sorted(boosts.items(), key=lambda x: -x[1])
            summary_parts = []
            for k, _ in top[:3]:
                summary_parts.append(f"{AMENITY_ICONS.get(k, '')} {AMENITY_LABELS.get(k, k)}")

            st.markdown(
                f"<p style='font-size:0.88rem;color:#64748b;text-align:center;"
                f"margin-bottom:1.4rem;'>Predicted from your answers: "
                f"<strong style='color:#0b132d;'>{' · '.join(summary_parts)}</strong></p>",
                unsafe_allow_html=True,
            )

        if _next_btn("See my predicted priorities →", key="lifestyle_next"):
            predicted = _compute_predicted_amenity_rank()
            st.session_state["predicted_amenity_rank"] = predicted
            st.session_state["pref_amenity_rank"] = predicted[:]
            st.session_state["lifestyle_q"] = 0
            st.session_state.onboarding_step = 8
            st.rerun()

    _back_btn("lifestyle_step_back")


# ── Step 8: Predicted amenity ranking ────────────────────────────────────────

def _render_predicted_amenity_ranking():
    _progress_bar(8)
    _step_label(8)
    _heading(
        "What matters most to you?",
        "We’ve predicted your amenity priorities based on your lifestyle. Reorder them if needed."
    )

    if "predicted_amenity_rank" not in st.session_state:
        predicted = _compute_predicted_amenity_rank()
        st.session_state["predicted_amenity_rank"] = predicted
        st.session_state["pref_amenity_rank"] = predicted[:]

    rank = st.session_state.get("pref_amenity_rank") or st.session_state["predicted_amenity_rank"]

    st.markdown(
        "<div style='padding:12px 14px;background:#fff5f6;border:1px solid #ffd4db;border-radius:12px;"
        "margin-bottom:1rem;font-size:0.88rem;color:#7f1d1d;'>"
        "Tip: we’ve pre-filled this for the user, so they only need to adjust it if it feels off."
        "</div>",
        unsafe_allow_html=True,
    )

    if HAS_SORTABLES:
        _render_rank_list_sortable(rank)
    else:
        _render_rank_list_with_buttons(rank)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Reset to predicted order", key="amenity_reset", use_container_width=True):
            st.session_state.pref_amenity_rank = st.session_state["predicted_amenity_rank"][:]
            st.rerun()
    with cols[1]:
        if st.button("Continue →", key="amenity_next", type="primary", use_container_width=True):
            st.session_state.onboarding_step = 9
            st.rerun()

    _back_btn("amenity_back")


# ── Step 9: Anchors (optional) ───────────────────────────────────────────────

def _render_anchors():
    _progress_bar(9)
    _step_label(9)
    _heading(
        "Any anchor locations?",
        "Optional: add up to 2 postal codes (workplace, parents, etc.) so we can factor proximity into your deck."
    )

    p1, p2 = st.columns(2)
    existing = st.session_state.get("pref_landmark_postals") or []

    with p1:
        v1 = st.text_input(
            "Postal code 1",
            value=existing[0] if len(existing) > 0 else "",
            placeholder="e.g. 119077",
            key="anchor_1"
        )
    with p2:
        v2 = st.text_input(
            "Postal code 2",
            value=existing[1] if len(existing) > 1 else "",
            placeholder="e.g. 560215",
            key="anchor_2"
        )

    postals = [p.strip() for p in [v1, v2] if p.strip()]
    has_any_postal = len(postals) > 0

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Skip this step", key="anchor_skip", use_container_width=True):
            st.session_state.pref_landmark_postals = []
            st.session_state.onboarding_step = 10
            st.rerun()

    with cols[1]:
        if st.button(
            "Save & continue →",
            key="anchor_next",
            type="primary",
            use_container_width=True,
            disabled=not has_any_postal,
        ):
            st.session_state.pref_landmark_postals = postals
            st.session_state.onboarding_step = 10
            st.rerun()

    if not has_any_postal:
        st.markdown(
            "<p style='font-size:0.82rem;color:#9ca3af;margin-top:0.6rem;'>"
            "Enter at least 1 postal code to save and continue, or skip this step."
            "</p>",
            unsafe_allow_html=True,
        )

    _back_btn("anchor_back")


# ── Step 10: Done / trigger search ───────────────────────────────────────────

def _render_done():
    st.session_state.onboarding_complete = True


# ── Build UserInputs from session state ──────────────────────────────────────

def build_inputs_from_prefs() -> UserInputs:
    """Convert stored onboarding prefs into a UserInputs dataclass."""
    rank = st.session_state.get("pref_amenity_rank") or list(AMENITY_LABELS.keys())
    n = len(rank)

    raw_weights = {key: (n - i) for i, key in enumerate(rank)}
    total = sum(raw_weights.values())
    amenity_weights = {k: v / total for k, v in raw_weights.items()}

    for key in AMENITY_LABELS:
        if key not in amenity_weights:
            amenity_weights[key] = 0.0

    return UserInputs(
        budget=st.session_state.get("pref_budget") if not st.session_state.get("pref_budget_flexible") else None,
        flat_type=st.session_state.get("pref_flat_type") or "4 ROOM",
        floor_area_sqm=float(st.session_state.get("pref_floor_area") or 95),
        remaining_lease_years=st.session_state.get("pref_remaining_lease") or 60,
        town=st.session_state.get("pref_town"),
        school_scope=st.session_state.get("pref_school_scope", "Any"),
        amenity_weights=amenity_weights,
        amenity_rank=rank,
        landmark_postals=st.session_state.get("pref_landmark_postals") or [],
    )


def get_preferences_display() -> dict:
    rank = st.session_state.get("pref_amenity_rank") or []
    budget_val = st.session_state.get("pref_budget")
    budget_display = "Flexible / not set" if st.session_state.get("pref_budget_flexible") else f"S${(budget_val or 0):,}"

    return {
        "Budget": budget_display,
        "Flat type": FLAT_TYPE_LABELS.get(st.session_state.get("pref_flat_type") or "", "—"),
        "Floor area": f"{st.session_state.get('pref_floor_area') or '—'} sqm",
        "Min. lease": f"{st.session_state.get('pref_remaining_lease') or '—'} years remaining",
        "Town": st.session_state.get("pref_town") or "Recommendation mode",
        "Priority": {
            "save_money": "Save money 💵",
            "convenience": "Convenience 🚶⏱️",
            "balanced": "Balanced 🎯⚖️",
        }.get(st.session_state.get("pref_priority_mode"), "Balanced 🎯⚖️"),
        "Amenity ranking": " → ".join(
            f"{AMENITY_ICONS.get(k, '')} {AMENITY_LABELS.get(k, k)}" for k in rank
        ) or "—",
        "Anchors": ", ".join(st.session_state.get("pref_landmark_postals") or []) or "None",
    }