"""
Flow:
  0  Welcome screen
  1  Budget
  2  Flat type
  3  Floor area
  4  Minimum remaining lease
  5  Town preference
  6  Priority mode
  7  Lifestyle quiz
  8  Predicted amenity ranking review / reorder
  9  Done → triggers search
"""

import streamlit as st
import streamlit.components.v1 as components

from backend.utils.constants import FLAT_TYPES, TOWNS, AMENITY_LABELS
from backend.services.quiz import render_quiz, reset_quiz
from backend.schemas.inputs import UserInputs

try:
    from streamlit_sortables import sort_items
    HAS_SORTABLES = True
except Exception:
    HAS_SORTABLES = False


TOTAL_STEPS = 9

AMENITY_ICONS = {
    "mrt": "🚇",
    "bus": "🚌",
    "healthcare": "🏥",
    "schools": "🏫",
    "hawker": "🍜",
    "retail": "🛍️",
}

FRONTEND_AMENITY_LABELS = {
    "mrt": "MRT stations",
    "bus": "Bus stops",
    "hawker": "Hawker centres",
    "retail": "Shopping malls",
    "healthcare": "Hospitals / Polyclinics",
    "schools": "Schools",
}

FLAT_TYPE_LABELS = {
    "1 ROOM": "1-Room",
    "2 ROOM": "2-Room",
    "3 ROOM": "3-Room",
    "4 ROOM": "4-Room",
    "5 ROOM": "5-Room",
    "EXECUTIVE": "Executive",
    "MULTI-GENERATION": "Multi-Generation",
}

FLAT_ICONS = {
    "1 ROOM": "🏢",
    "2 ROOM": "🏠",
    "3 ROOM": "🏡",
    "4 ROOM": "🏘️",
    "5 ROOM": "🏗️",
    "EXECUTIVE": "🏛️",
    "MULTI-GENERATION": "🏠👨‍👩‍👧‍👦",
}

ACCENT = "#FF4458"
ACCENT_BG = "rgba(255,68,88,0.08)"
ACCENT_BORDER = "#FF4458"

AMENITY_KEY_MAP = {
    "train": "mrt",
    "bus": "bus",
    "hawker": "hawker",
    "mall": "retail",
    "supermarket": "retail",
    "polyclinic": "healthcare",
    "primary_school": "schools",
}


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
                st.session_state.pop("pref_quiz_scores", None)
                st.session_state.pop("pref_amenity_rank", None)
                st.session_state.pop("pref_amenity_weights", None)
                st.session_state.onboarding_step = 7
                st.session_state["quiz_step"] = "tiebreak"
                st.rerun()
            else:
                st.session_state.onboarding_step -= 1
                st.rerun()


def _default_amenity_order():
    return list(FRONTEND_AMENITY_LABELS.keys())


def _map_quiz_ranking(quiz_ranking: list[str]) -> list[str]:
    mapped = []
    for key in quiz_ranking:
        new_key = AMENITY_KEY_MAP.get(key)
        if new_key and new_key not in mapped:
            mapped.append(new_key)

    for key in FRONTEND_AMENITY_LABELS.keys():
        if key not in mapped:
            mapped.append(key)

    return mapped


def _map_quiz_weights(quiz_weights: dict[str, float]) -> dict[str, float]:
    mapped = {k: 0.0 for k in FRONTEND_AMENITY_LABELS.keys()}
    for old_key, weight in quiz_weights.items():
        new_key = AMENITY_KEY_MAP.get(old_key)
        if new_key:
            mapped[new_key] += float(weight)

    total = sum(mapped.values())
    if total > 0:
        mapped = {k: v / total for k, v in mapped.items()}

    return mapped


def _priority_explainer(rank: list[str]) -> str:
    if not rank:
        return "We’ve estimated what matters most to you based on your responses."

    top = rank[:3]
    labels = [FRONTEND_AMENITY_LABELS.get(k, k) for k in top]

    if len(labels) == 1:
        joined = labels[0]
    elif len(labels) == 2:
        joined = f"{labels[0]} and {labels[1]}"
    else:
        joined = f"{labels[0]}, {labels[1]}, and {labels[2]}"

    return f"Based on your answers, we think {joined} are likely to matter most to you."


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
                        {FRONTEND_AMENITY_LABELS.get(key, key)}
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
        FRONTEND_AMENITY_LABELS.get(k, k): k
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
        done = _render_done()
        st.markdown("</div>", unsafe_allow_html=True)
        return done

    st.markdown("</div>", unsafe_allow_html=True)
    return False


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
            reset_quiz()
            st.session_state.onboarding_step = 1
            st.rerun()


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

        st.markdown(
            """
            <style>
            div[data-testid="stTextInput"] label { display: none !important; }
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
            div[data-testid="stTextInput"] > div,
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


def _render_flat_type():
    _progress_bar(2)
    _step_label(2)
    _heading("What type of flat?", "Pick one or more — tap to select, tap again to deselect.")

    # Multi-select: stored as a list in pref_flat_types
    selected_types: list = list(st.session_state.get("pref_flat_types") or ["4 ROOM"])

    cols = st.columns(len(FLAT_TYPES))
    for i, ft in enumerate(FLAT_TYPES):
        is_selected = ft in selected_types
        with cols[i]:
            if st.button(
                f"{FLAT_ICONS[ft]} {FLAT_TYPE_LABELS[ft]}",
                key=f"ft_{ft}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                if is_selected and len(selected_types) > 1:
                    selected_types.remove(ft)
                elif not is_selected:
                    selected_types.append(ft)
                st.session_state.pref_flat_types = selected_types
                # Reset the floor area manual flag so it re-auto-populates
                st.session_state.pref_floor_area_sqft_manual = False
                st.rerun()

    # Live selection summary
    n = len(selected_types)
    # Sort pills in FLAT_TYPES order
    ordered = [ft for ft in FLAT_TYPES if ft in selected_types]
    pills_html = "".join(
        f"<span style='display:inline-block;background:#e0e7ff;color:#3730a3;"
        f"font-size:0.78rem;font-weight:600;border-radius:999px;"
        f"padding:3px 12px;margin:3px 4px;'>"
        f"{FLAT_ICONS[ft]} {FLAT_TYPE_LABELS[ft]}</span>"
        for ft in ordered
    )
    count_label = f"{n} selected" if n > 1 else "1 selected"
    st.markdown(
        f"<div style='text-align:center;margin:0.8rem 0 0.4rem;'>"
        f"<span style='font-size:0.75rem;color:#6b7280;margin-right:6px;'>{count_label}:</span>"
        f"{pills_html}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    if _next_btn(key="ft_next"):
        if not st.session_state.get("pref_flat_types"):
            st.session_state.pref_flat_types = ["4 ROOM"]
        st.session_state.onboarding_step = 3
        st.rerun()
    _back_btn("ft_back")



# Minimum floor area by flat type (sqft) — used to auto-populate the slider
_FLAT_TYPE_MIN_SQFT = {
    "1 ROOM":          300,
    "2 ROOM":          380,
    "3 ROOM":          600,
    "4 ROOM":          900,
    "5 ROOM":         1100,
    "EXECUTIVE":      1300,
    "MULTI-GENERATION": 1100,
}
_SQFT_TO_SQM = 0.092903   # 1 sqft = 0.092903 sqm


def _sqft_to_sqm(sqft: int) -> float:
    return round(sqft * _SQFT_TO_SQM, 1)


def _render_floor_area():
    _progress_bar(3)
    _step_label(3)
    _heading("What's your minimum floor area?")

    # Determine auto-populated default from the *smallest* flat type chosen in step 2
    selected_flat_types = st.session_state.get("pref_flat_types") or ["4 ROOM"]
    # "smallest" = lowest minimum sqft
    smallest_flat_type = min(
        selected_flat_types,
        key=lambda ft: _FLAT_TYPE_MIN_SQFT.get(ft, 900),
    )
    auto_min_sqft = _FLAT_TYPE_MIN_SQFT.get(smallest_flat_type, 900)

    # "No requirement" toggle — stored as pref_floor_area_skip
    no_req = st.checkbox(
        "No minimum requirement — show me all sizes",
        value=st.session_state.get("pref_floor_area_skip", False),
        key="floor_area_skip_toggle",
    )
    st.session_state.pref_floor_area_skip = no_req

    if no_req:
        st.markdown(
            "<div style='text-align:center;font-size:2rem;font-weight:800;color:#0b132d;"
            "margin:1.2rem 0 1.6rem;'>All floor areas</div>",
            unsafe_allow_html=True,
        )
        area_sqft = None
    else:
        # Show the auto-populate note only when the value hasn't been manually changed yet
        manually_set = st.session_state.get("pref_floor_area_sqft_manual", False)
        if not manually_set:
            st.markdown(
                f"<div style='font-size:0.78rem;color:#2563eb;background:#eff6ff;"
                f"border:1px solid #bfdbfe;border-radius:8px;padding:6px 12px;"
                f"margin-bottom:0.6rem;'>✨ Auto-populated based on your flat type "
                f"(roughly {auto_min_sqft:,} sqft for a {smallest_flat_type}). "
                f"Adjust freely.</div>",
                unsafe_allow_html=True,
            )

        # Current slider value in sqft — default to auto_min_sqft
        current_sqft = st.session_state.get("pref_floor_area_sqft") or auto_min_sqft

        area_sqft = st.slider(
            "Minimum floor area (sqft)",
            min_value=200,
            max_value=2500,
            value=int(current_sqft),
            step=50,
            format="%d sqft",
            label_visibility="collapsed",
        )

        # Mark as manually set once the user moves the slider away from the default
        if area_sqft != auto_min_sqft:
            st.session_state.pref_floor_area_sqft_manual = True

        sqm_equiv = _sqft_to_sqm(area_sqft)
        st.markdown(
            f"<div style='text-align:center;font-size:2.2rem;font-weight:800;"
            f"letter-spacing:-0.04em;color:#0f172a;margin:0.4rem 0 0.2rem;'>"
            f"{area_sqft:,} sqft</div>"
            f"<div style='text-align:center;font-size:0.85rem;color:#9ca3af;"
            f"margin-bottom:1.6rem;'>≈ {sqm_equiv} sqm</div>",
            unsafe_allow_html=True,
        )

    if _next_btn(key="area_next"):
        st.session_state.pref_floor_area_sqft = area_sqft
        # Store in sqm for the backend (None = no filter)
        st.session_state.pref_floor_area = (
            _sqft_to_sqm(area_sqft) if area_sqft is not None else None
        )
        st.session_state.onboarding_step = 4
        st.rerun()
    _back_btn("area_back")


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
        f"<span style='font-size:2.2rem;font-weight:800;letter-spacing:-0.04em;color:#0f172a;'>{lease} years</span></div>"
        f"<div style='text-align:center;font-size:0.82rem;color:#9ca3af;margin-bottom:1.6rem;'>{hint}</div>",
        unsafe_allow_html=True,
    )

    if _next_btn(key="lease_next"):
        st.session_state.pref_remaining_lease = lease
        st.session_state.onboarding_step = 5
        st.rerun()
    _back_btn("lease_back")


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


def _render_lifestyle():
    _progress_bar(7)
    _step_label(7)
    _heading(
        "Your lifestyle",
        "Answer a few quick questions so we can personalise your recommendations."
    )

    scoring_weights, final_ranking, normalised_weights = render_quiz()

    if not final_ranking:
        return

    mapped_ranking = _map_quiz_ranking(final_ranking)
    mapped_weights = _map_quiz_weights(scoring_weights)
    mapped_quiz_scores = _map_quiz_weights(normalised_weights)

    st.session_state["pref_amenity_rank"] = mapped_ranking
    st.session_state["pref_amenity_weights"] = mapped_weights
    st.session_state["pref_quiz_scores"] = mapped_quiz_scores
    st.session_state.onboarding_step = 8
    st.rerun()


def _render_predicted_amenity_ranking():
    _progress_bar(8)
    _step_label(8)
    _heading(
        "Your predicted priorities",
        "We’ve inferred what matters most to you from your answers. You can adjust the order if needed."
    )

    rank = st.session_state.get("pref_amenity_rank")
    if not rank:
        rank = list(FRONTEND_AMENITY_LABELS.keys())
        st.session_state.pref_amenity_rank = rank

    st.markdown(
        f"<div style='padding:12px 14px;background:#fff7ed;border:1px solid #fed7aa;"
        f"border-radius:12px;margin-bottom:1rem;font-size:0.9rem;color:#9a3412;'>"
        f"{_priority_explainer(rank)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if HAS_SORTABLES:
        labels_to_key = {FRONTEND_AMENITY_LABELS.get(k, k): k for k in rank}
        display_rank = [FRONTEND_AMENITY_LABELS.get(k, k) for k in rank]
        sorted_display = sort_items(display_rank, direction="vertical", key="amenity_sortable")
        st.session_state.pref_amenity_rank = [labels_to_key[label] for label in sorted_display]
    else:
        _render_rank_list_with_buttons(rank)

    with st.expander("Why these priorities?"):
        st.markdown(
            "We estimated these priorities from your quiz responses. "
            "The percentages below show how strongly each amenity came through in your answers."
        )

        quiz_scores = st.session_state.get("pref_quiz_scores", {})

        if rank:
            for key in rank:
                label = FRONTEND_AMENITY_LABELS.get(key, key)
                quiz_pct = quiz_scores.get(key, 0.0) * 100

                st.markdown(
                    f"**{label}** — Inferred score: `{quiz_pct:.1f}%`"
                )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])

    with c1:
        if st.button("↺ Start over", key="amenity_start_over", use_container_width=True):
            st.session_state.pop("pref_quiz_scores", None)
            st.session_state.pop("pref_amenity_rank", None)
            st.session_state.pop("pref_amenity_weights", None)
            reset_quiz()
            st.session_state.onboarding_step = 7
            st.rerun()

    with c2:
        if st.button("Looks good →", key="amenity_rank_next", type="primary", use_container_width=True):
            final_rank = st.session_state.get("pref_amenity_rank") or list(FRONTEND_AMENITY_LABELS.keys())
            n = len(final_rank)
            raw_weights = {k: (n - i) for i, k in enumerate(final_rank)}
            total = sum(raw_weights.values())
            weights = {k: v / total for k, v in raw_weights.items()}
            st.session_state["pref_amenity_weights"] = weights
            st.session_state.onboarding_step = 9
            st.rerun()

    _back_btn("amenity_rank_back")


def _render_done() -> bool:
    """Completion splash — returns True when the user clicks the CTA."""
    components.html(
        """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;font-family:'DM Sans',-apple-system,sans-serif;background:transparent;overflow:hidden;}

/* ambient float */
@keyframes f1{0%,100%{transform:translate(0,0) rotate(0deg)}25%{transform:translate(14px,-22px) rotate(10deg)}75%{transform:translate(-10px,14px) rotate(-7deg)}}
@keyframes f2{0%,100%{transform:translate(0,0) rotate(0deg)}33%{transform:translate(-18px,16px) rotate(-12deg)}67%{transform:translate(13px,-11px) rotate(8deg)}}
@keyframes f3{0%,100%{transform:translate(0,0) rotate(0deg)}50%{transform:translate(11px,20px) rotate(15deg)}}
@keyframes f4{0%,100%{transform:translate(0,0) rotate(0deg)}40%{transform:translate(-13px,-18px) rotate(-9deg)}80%{transform:translate(9px,9px) rotate(5deg)}}
@keyframes f5{0%,100%{transform:translate(0,0) rotate(0deg)}30%{transform:translate(17px,11px) rotate(13deg)}70%{transform:translate(-15px,-13px) rotate(-8deg)}}
@keyframes f6{0%,100%{transform:translate(0,0) rotate(0deg)}50%{transform:translate(-9px,22px) rotate(-14deg)}}
@keyframes glowPulse{0%,100%{opacity:0.2;transform:translate(-50%,-50%) scale(1)}50%{opacity:0.5;transform:translate(-50%,-50%) scale(1.1)}}

/* single shared entrance — every element uses this, only delay differs */
@keyframes fadeUp{
  from{opacity:0;transform:translateY(20px)}
  to  {opacity:1;transform:translateY(0)}
}

/* gradient shine */
@keyframes shine{0%{background-position:200% center}100%{background-position:-200% center}}

/* scene */
.scene{
  position:relative;width:100%;height:420px;overflow:hidden;
  background:#ffffff;border-radius:24px;
}
.glow{
  position:absolute;top:40%;left:50%;
  width:560px;height:320px;
  background:radial-gradient(ellipse,rgba(255,68,88,0.11) 0%,rgba(255,179,71,0.05) 50%,transparent 70%);
  animation:glowPulse 5s ease-in-out infinite;pointer-events:none;
}
.p{position:absolute;line-height:1;}
.centre{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  z-index:10;padding:2rem 2.5rem;text-align:center;
}

/* green check badge */
.badge{
  display:inline-flex;align-items:center;gap:6px;
  background:#f0fdf4;border:1px solid #bbf7d0;
  color:#16a34a;font-size:0.72rem;font-weight:700;
  letter-spacing:0.08em;text-transform:uppercase;
  border-radius:999px;padding:4px 14px;
  margin-bottom:1.6rem;
  opacity:0;animation:fadeUp 1.1s cubic-bezier(0.25,1,0.5,1) 0.3s forwards;
}

/* small intro line */
.intro{
  font-size:0.95rem;font-weight:500;color:#6b7280;
  margin-bottom:0.3rem;
  opacity:0;animation:fadeUp 1.1s cubic-bezier(0.25,1,0.5,1) 0.65s forwards;
}

/* big dark heading */
.big{
  font-size:clamp(2.4rem,6.5vw,3.4rem);font-weight:800;letter-spacing:-0.05em;
  color:#0b132d;line-height:1.0;margin-bottom:0.1rem;
  opacity:0;animation:fadeUp 1.1s cubic-bezier(0.25,1,0.5,1) 1.05s forwards;
}

/* big gradient line + shine after it appears */
.big-grad{
  font-size:clamp(2.4rem,6.5vw,3.4rem);font-weight:800;letter-spacing:-0.05em;
  line-height:1.0;margin-bottom:1.6rem;
  background:linear-gradient(120deg,#FF6B6B 0%,#FF4458 25%,#FFB347 55%,#FF8C69 80%,#FF6B6B 100%);
  background-size:260% auto;
  -webkit-background-clip:text;background-clip:text;color:transparent;
  opacity:0;
  animation:fadeUp 1.1s cubic-bezier(0.25,1,0.5,1) 1.45s forwards,
            shine 4s linear 2.8s infinite;
}

/* sub */
.sub{
  font-size:0.84rem;color:#9ca3af;max-width:270px;
  line-height:1.75;font-weight:400;
  opacity:0;animation:fadeUp 1.1s cubic-bezier(0.25,1,0.5,1) 2.05s forwards;
}
</style>
</head>
<body>
<div class="scene">
  <div class="glow"></div>
  <span class="p" style="top:7%;left:7%;font-size:2.4rem;opacity:0.45;animation:f1 7s ease-in-out infinite;">&#127968;</span>
  <span class="p" style="top:19%;left:16%;font-size:1.3rem;opacity:0.28;animation:f3 10s ease-in-out infinite;animation-delay:-2.5s;">&#127795;</span>
  <span class="p" style="top:5%;left:30%;font-size:1rem;opacity:0.16;animation:f2 12s ease-in-out infinite;animation-delay:-5s;">&#10024;</span>
  <span class="p" style="top:6%;right:9%;font-size:2.2rem;opacity:0.40;animation:f2 8.5s ease-in-out infinite;animation-delay:-1s;">&#127969;</span>
  <span class="p" style="top:21%;right:18%;font-size:1.25rem;opacity:0.28;animation:f4 10.5s ease-in-out infinite;animation-delay:-3.5s;">&#128273;</span>
  <span class="p" style="top:9%;right:33%;font-size:0.95rem;opacity:0.14;animation:f1 13s ease-in-out infinite;animation-delay:-7s;">&#128171;</span>
  <span class="p" style="top:43%;left:5%;font-size:1.8rem;opacity:0.35;animation:f5 9s ease-in-out infinite;animation-delay:-2s;">&#128106;</span>
  <span class="p" style="top:63%;left:11%;font-size:1.1rem;opacity:0.22;animation:f3 13.5s ease-in-out infinite;animation-delay:-6s;">&#129716;</span>
  <span class="p" style="top:41%;right:5%;font-size:1.9rem;opacity:0.32;animation:f4 8s ease-in-out infinite;animation-delay:-4s;">&#128715;</span>
  <span class="p" style="top:63%;right:13%;font-size:1.05rem;opacity:0.20;animation:f6 11.5s ease-in-out infinite;animation-delay:-8s;">&#128149;</span>
  <span class="p" style="bottom:14%;left:8%;font-size:1.5rem;opacity:0.30;animation:f2 9s ease-in-out infinite;animation-delay:-1.8s;">&#127960;</span>
  <span class="p" style="bottom:12%;right:10%;font-size:1.6rem;opacity:0.28;animation:f1 7.5s ease-in-out infinite;animation-delay:-4.5s;">&#127807;</span>
  <span class="p" style="bottom:25%;left:25%;font-size:0.85rem;opacity:0.12;animation:f5 15s ease-in-out infinite;animation-delay:-9s;">&#10024;</span>
  <span class="p" style="bottom:22%;right:27%;font-size:0.85rem;opacity:0.12;animation:f3 12.5s ease-in-out infinite;animation-delay:-10s;">&#128171;</span>
  <span class="p" style="bottom:8%;left:42%;font-size:1rem;opacity:0.16;animation:f6 10s ease-in-out infinite;animation-delay:-3s;">&#128716;</span>
  <div class="centre">
    <div class="badge">&#10003;&nbsp;&nbsp;All set</div>
    <div class="intro">You've told us everything we need.</div>
    <div class="big">Your flat</div>
    <div class="big-grad">is waiting.</div>
    <p class="sub">We're matching every active listing to your priorities right now.</p>
  </div>
</div>
</body>
</html>""",
        height=435,
        scrolling=False,
    )
    # Button fades in last — same fadeUp, fires after sub finishes (~3.6s)
    st.markdown(
        """
        <style>
        @keyframes _btnFadeUp {
            from { opacity: 0; transform: translateY(14px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        div[data-testid="stButton"] button[kind="primary"] {
            opacity: 0;
            animation: _btnFadeUp 1.1s cubic-bezier(0.25,1,0.5,1) 3.0s forwards;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("Show me my flats →", key="done_cta", type="primary", use_container_width=True):
            return True
    return False


def build_inputs_from_prefs() -> UserInputs:
    rank = st.session_state.get("pref_amenity_rank") or list(FRONTEND_AMENITY_LABELS.keys())
    amenity_weights = st.session_state.get("pref_amenity_weights")

    if not amenity_weights:
        n = len(rank)
        raw_weights = {key: (n - i) for i, key in enumerate(rank)}
        total = sum(raw_weights.values())
        amenity_weights = {k: v / total for k, v in raw_weights.items()}

    for key in FRONTEND_AMENITY_LABELS:
        if key not in amenity_weights:
            amenity_weights[key] = 0.0

    # floor_area_sqm: stored in sqm by _render_floor_area; None = no minimum filter
    raw_sqm = st.session_state.get("pref_floor_area")
    floor_area_sqm = float(raw_sqm) if raw_sqm is not None else None

    priority_mode = st.session_state.get("pref_priority_mode", "balanced")

    priority_to_ranking_profile = {
        "save_money": "value-first",
        "convenience": "amenity-first",
        "balanced": "balanced",
    }

    ranking_profile = priority_to_ranking_profile.get(priority_mode, "balanced")

    return UserInputs(
        budget=st.session_state.get("pref_budget") if not st.session_state.get("pref_budget_flexible") else None,
        flat_types=st.session_state.get("pref_flat_types") or ["4 ROOM"],
        floor_area_sqm=floor_area_sqm,
        remaining_lease_years=st.session_state.get("pref_remaining_lease") or 60,
        town=st.session_state.get("pref_town"),
        school_scope=st.session_state.get("pref_school_scope", "Any"),
        amenity_weights=amenity_weights,
        amenity_rank=rank,
        landmark_postals=[],
        ranking_profile=ranking_profile,
    )


def get_preferences_display() -> dict:
    rank = st.session_state.get("pref_amenity_rank") or []
    budget_val = st.session_state.get("pref_budget")
    budget_display = "Flexible / not set" if st.session_state.get("pref_budget_flexible") else f"S${(budget_val or 0):,}"

    return {
        "Budget": budget_display,
        "Flat type": ", ".join(
            FLAT_TYPE_LABELS.get(ft, ft)
            for ft in (st.session_state.get("pref_flat_types") or [])
        ) or "—",
        "Floor area": (
            f"{st.session_state.get('pref_floor_area_sqft') or '—'} sqft"
            if not st.session_state.get("pref_floor_area_skip")
            else "No requirement"
        ),
        "Min. lease": f"{st.session_state.get('pref_remaining_lease') or '—'} years remaining",
        "Town": st.session_state.get("pref_town") or "Recommendation mode",
        "Priority": {
            "save_money": "Save money 💵",
            "convenience": "Convenience 🚶⏱️",
            "balanced": "Balanced 🎯⚖️",
        }.get(st.session_state.get("pref_priority_mode"), "Balanced 🎯⚖️"),
        "Amenity ranking": " → ".join(
            f"{AMENITY_ICONS.get(k, '')} {FRONTEND_AMENITY_LABELS.get(k, k)}" for k in rank
        ) or "—",
    }