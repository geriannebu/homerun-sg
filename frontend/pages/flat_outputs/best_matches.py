# frontend/pages/flat_outputs/best_matches.py

import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from backend.utils.formatters import fmt_sgd
from backend.utils.constants import TOWN_COORDS
from frontend.state.session import get_active_session, record_swipe
from frontend.components.listing_detail import show_listing_detail

DEFAULT_COORD = (1.3521, 103.8198)

AMENITY_LABELS = {
    "train": "MRT access",
    "bus": "Bus stops",
    "primary_school": "Schools",
    "hawker": "Hawker food",
    "mall": "Shopping malls",
    "polyclinic": "Healthcare",
    "supermarket": "Supermarkets",
}

AMENITY_ICONS = {
    "train": "🚇",
    "bus": "🚌",
    "primary_school": "🏫",
    "hawker": "🍜",
    "mall": "🛍️",
    "polyclinic": "🏥",
    "supermarket": "🛒",
}


def _map_url(town: str) -> str:
    lat, lon = TOWN_COORDS.get(town, DEFAULT_COORD)
    return (
        f"https://www.openstreetmap.org/export/embed.html"
        f"?bbox={lon-0.012},{lat-0.008},{lon+0.012},{lat+0.008}"
        f"&layer=mapnik&marker={lat},{lon}"
    )


def _val_color(label: str) -> str:
    if "Steal" in label or "Great Deal" in label:
        return "#059E87"
    if "Fair" in label:
        return "#2563eb"
    if "Slight" in label:
        return "#d97706"
    return "#64748b"


def _capitalize_first(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _why_match(row, inputs, deck_df: pd.DataFrame | None = None) -> tuple[str, str]:
    rank = list(getattr(inputs, "amenity_rank", []) or [])
    top_amenities = rank[:3] if rank else []

    diff = pd.to_numeric(row.get("valuation_pct"), errors="coerce")
    town_pref = getattr(inputs, "town", None)
    min_lease = getattr(inputs, "remaining_lease_years", None)
    min_area = getattr(inputs, "floor_area_sqm", None)

    flat_town = str(row.get("town", "")).strip().upper()
    pref_town = str(town_pref).strip().upper() if town_pref else None

    lease_val = pd.to_numeric(
        row.get("remaining_lease_years", row.get("remaining_lease")),
        errors="coerce"
    )
    area_val = pd.to_numeric(row.get("floor_area_sqm"), errors="coerce")

    amenity_phrases = {
        "train": {
            "elite": "Best MRT access among your top matches",
            "strong": "Strong MRT access",
            "good": "Close to MRT stations",
        },
        "bus": {
            "elite": "Best bus connectivity in this deck",
            "strong": "Strong bus connectivity",
            "good": "Close to bus stops",
        },
        "primary_school": {
            "elite": "Closest to schools in this shortlist",
            "strong": "Strong school access",
            "good": "Schools nearby",
        },
        "hawker": {
            "elite": "Best hawker access in this deck",
            "strong": "Strong hawker access",
            "good": "Hawker food nearby",
        },
        "mall": {
            "elite": "Closest to shopping malls in this deck",
            "strong": "Strong shopping access",
            "good": "Shopping nearby",
        },
        "polyclinic": {
            "elite": "Best healthcare access among your top matches",
            "strong": "Strong healthcare access",
            "good": "Healthcare nearby",
        },
        "supermarket": {
            "elite": "Best supermarket access in this deck",
            "strong": "Strong supermarket access",
            "good": "Convenient grocery access",
        },
    }

    # ---------- 1) Primary line: standout amenity relative to deck ----------
    primary = None
    amenity_candidates = []

    for idx, amen in enumerate(top_amenities):
        score_col = f"walk_acc_{amen}"
        score = pd.to_numeric(row.get(score_col), errors="coerce")
        if pd.isna(score):
            continue

        relative_bonus = 0
        pct_rank = 0

        if deck_df is not None and score_col in deck_df.columns:
            deck_scores = pd.to_numeric(deck_df[score_col], errors="coerce").dropna()
            if len(deck_scores) > 0:
                pct_rank = (deck_scores < float(score)).mean()
                if pct_rank >= 0.85:
                    relative_bonus = 20
                elif pct_rank >= 0.65:
                    relative_bonus = 10
                elif pct_rank >= 0.45:
                    relative_bonus = 4

        priority_bonus = max(0, 18 - 5 * idx)
        base_score = float(score) * 100 + relative_bonus + priority_bonus

        # bus is common, so downweight it a lot
        if amen == "bus":
            base_score -= 20

        amenity_candidates.append({
            "amenity": amen,
            "score": base_score,
            "pct_rank": pct_rank,
            "raw_score": float(score),
        })

    amenity_candidates = sorted(amenity_candidates, key=lambda x: x["score"], reverse=True)

    if amenity_candidates:
        best = amenity_candidates[0]
        amen = best["amenity"]
        phrases = amenity_phrases.get(amen, {})

        if best["pct_rank"] >= 0.85:
            primary = phrases.get("elite", amen)
        elif best["raw_score"] >= 0.78:
            primary = phrases.get("strong", amen)
        else:
            primary = phrases.get("good", amen)
            
    # ---------- 2) Secondary line: supporting reason ----------
    secondary_candidates = []

    if pd.notna(diff):
        if deck_df is not None and "valuation_pct" in deck_df.columns:
            deck_diffs = pd.to_numeric(deck_df["valuation_pct"], errors="coerce").dropna()
            if len(deck_diffs) > 0:
                pct_better_than = (deck_diffs > float(diff)).mean()

                if diff <= -5 and pct_better_than >= 0.75:
                    secondary_candidates.append(("priced below model estimate", 78))
                elif -2 <= diff <= 2 and pct_better_than >= 0.60:
                    secondary_candidates.append(("fairly priced for this deck", 54))
        else:
            if diff <= -8:
                secondary_candidates.append(("priced below model estimate", 72))

    if pd.notna(min_lease) and pd.notna(lease_val):
        lease_bonus = lease_val - float(min_lease)
        if lease_bonus >= 12:
            secondary_candidates.append(("long remaining lease", 72 + min(10, lease_bonus)))

    if pd.notna(min_area) and pd.notna(area_val):
        area_bonus = area_val - float(min_area)
        if area_bonus >= 8:
            secondary_candidates.append(("larger floor area than your minimum", 70 + min(8, area_bonus)))

    if pref_town and flat_town == pref_town:
        if deck_df is not None and "town" in deck_df.columns:
            deck_towns = deck_df["town"].fillna("").astype(str).str.upper()
            share_in_pref_town = (deck_towns == pref_town).mean()
            if share_in_pref_town < 0.75:
                secondary_candidates.append(("in your preferred town", 64))
        else:
            secondary_candidates.append(("in your preferred town", 64))

    secondary_candidates = sorted(secondary_candidates, key=lambda x: x[1], reverse=True)
    secondary = secondary_candidates[0][0] if secondary_candidates else "balanced overall match"

    # avoid exact duplicate meaning
    if primary and secondary and primary.lower() == secondary.lower():
        secondary = "balanced overall match"

    if primary is None:
        primary = secondary
        secondary = ""

    return _capitalize_first(primary), _capitalize_first(secondary)

def _sqm_to_sqft(area_sqm) -> int:
    try:
        return int(round(float(area_sqm) * 10.7639))
    except Exception:
        return 0
    
def _format_remaining_lease(value):
    try:
        if value is None or pd.isna(value):
            return "-"
        value = float(value)
        if value <= 0:
            return "-"
        return f"{int(round(value))} yrs"
    except Exception:
        return "-"


def _serialize_card(row, inputs, budget=None, deck_df: pd.DataFrame | None = None) -> dict:
    diff = float(row.get("valuation_pct", 0))
    if diff <= -5:
        label = "Great Deal"
    elif diff <= 3:
        label = "Fair Value"
    elif diff <= 10:
        label = "Slightly High"
    else:
        label = "Overpriced"    
        
    town = str(row.get("town", ""))

    budget_val = budget if budget is not None else getattr(inputs, "budget", None)

    budget_gap = None
    budget_gap_pct = None
    is_within_budget = None

    asking = int(row.get("asking_price", 0))
    predicted = int(row.get("predicted_price", 0))

    ci_low = row.get("confidence_low", row.get("predicted_price_lower"))
    ci_high = row.get("confidence_high", row.get("predicted_price_upper"))

    try:
        ci_low = int(ci_low) if ci_low is not None else None
    except (TypeError, ValueError):
        ci_low = None

    try:
        ci_high = int(ci_high) if ci_high is not None else None
    except (TypeError, ValueError):
        ci_high = None

    if budget_val is not None and asking:
        budget_gap = int(budget_val - asking)
        budget_gap_pct = round((budget_gap / asking) * 100, 1)
        is_within_budget = budget_gap >= 0

    primary_why, secondary_why = _why_match(row, inputs, deck_df=deck_df)
    card = {
        "id": str(row.get("listing_id", "")),
        "listing_id": str(row.get("listing_id", "")),
        "town": town,
        "address": str(row.get("address", row.get("full_address", ""))),
        "flat_type": str(row.get("flat_type", "")),
        "area_sqft": _sqm_to_sqft(row.get("floor_area_sqm", 0)),
        "storey": str(row.get("storey_range", row.get("storey_midpoint", ""))),
        "asking": int(row.get("asking_price", 0)),
        "predicted": int(row.get("predicted_price", 0)),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "diff_pct": round(diff, 1),
        "label": label,
        "label_color": _val_color(label),
        "map_url": _map_url(town),
        "why_primary": primary_why,
        "why_secondary": secondary_why,
        "final_score": float(row.get("final_score", 0)) * 100,
        "budget": budget_val,
        "budget_gap": budget_gap,
        "budget_gap_pct": budget_gap_pct,
        "is_within_budget": is_within_budget,
        "remaining_lease": _format_remaining_lease(
            row.get("remaining_lease", row.get("remaining_lease_years"))
        ),
    }

    for amen in AMENITY_ICONS:
        card[amen] = float(row.get(f"walk_acc_{amen}", 0)) * 100

    return card


def _get_ranked_unseen_df(listings_df: pd.DataFrame, unseen_ids: list) -> pd.DataFrame:
    unseen_ids = [str(x) for x in unseen_ids]
    df = listings_df.copy()
    df["listing_id"] = df["listing_id"].astype(str)
    df = df[df["listing_id"].isin(unseen_ids)]

    # Preserve the scrambled order from unseen_ids (set by recommender's top.sample)
    id_order = {lid: i for i, lid in enumerate(unseen_ids)}
    df = df.sort_values("listing_id", key=lambda s: s.map(id_order))

    return df


def render_listing_tab(listings_df: pd.DataFrame):
    if listings_df is None or listings_df.empty:
        st.info("No listings available. Run a new search!")
        return

    session = get_active_session()
    if session is None:
        st.info("No active search session found.")
        return

    inputs = session["inputs"]

    if session.get("unseen_ids") is None:
        session["unseen_ids"] = list(listings_df["listing_id"].astype(str))
    else:
        session["unseen_ids"] = [str(x) for x in session["unseen_ids"]]

    if session.get("liked_ids") is None:
        session["liked_ids"] = []
    else:
        session["liked_ids"] = [str(x) for x in session["liked_ids"]]

    if session.get("passed_ids") is None:
        session["passed_ids"] = []
    else:
        session["passed_ids"] = [str(x) for x in session["passed_ids"]]


    unseen_ids = session["unseen_ids"]
    liked_ids = session["liked_ids"]
    passed_ids = session["passed_ids"]

    if not unseen_ids:
        _render_deck_done(session, listings_df)
        return

    ranked_unseen = _get_ranked_unseen_df(listings_df, unseen_ids)
    if ranked_unseen.empty:
        st.info("No unseen listings remain.")
        return

    current_row = ranked_unseen.iloc[0]
    budget = getattr(inputs, "budget", None)

    deck_context_df = ranked_unseen.head(12).copy()

    current_card = _serialize_card(
        current_row,
        inputs,
        budget=budget,
        deck_df=deck_context_df,
    )

    st.markdown(
        """
        <div style="
            padding: 18px 18px 16px 18px;
            margin-bottom: 12px;
            border-radius: 22px;
            background: linear-gradient(135deg, #fff7f9 0%, #fdf2f6 45%, #fae8f0 100%);
            border: 1px solid rgba(136,19,55,0.12);
            box-shadow: 0 10px 24px rgba(88,28,61,0.08);
        ">
            <div style="
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: #9f1239;
                margin-bottom: 6px;
            ">
                HomeRun recommendations
            </div>
            <div style="
                font-size: 1.85rem;
                font-weight: 800;
                letter-spacing: -0.04em;
                color: #581c3d;
                line-height: 1.05;
                margin-bottom: 6px;
            ">
                Your top-matched flats
            </div>
            <div style="
                font-size: 0.94rem;
                color: #6b7280;
                font-weight: 500;
                line-height: 1.5;
            ">
                Ranked to best match your budget, lifestyle, and amenity priorities.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Render ONLY the current card so visuals and details stay synced
    html = _build_single_card_html(json.dumps(current_card))
    components.html(html, height=510, scrolling=False)

    score = current_card["final_score"]
    color = "#059E87" if score >= 70 else "#d97706" if score >= 50 else "#64748b"

    st.markdown(
        f"""
        <div style='margin:10px 0 12px;'>
            <div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;
                 letter-spacing:0.08em;color:#94a3b8;margin-bottom:6px;'>🎯 Match Score</div>
            <div style='display:flex;align-items:center;gap:10px;'>
                <div style='flex:1;height:8px;border-radius:999px;background:#e2e8f0;overflow:hidden;'>
                    <div style='width:{score}%;height:100%;background:{color};border-radius:999px;'></div>
                </div>
                <span style='font-weight:800;color:{color};font-size:0.92rem;'>{score:.0f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    badges = ""
    for amen, icon in AMENITY_ICONS.items():
        val = current_card.get(amen, 0)

        border = "#cbd5e1"
        bg = "#f8fafc"
        text = "#64748b"

        if val >= 65:
            border = "#059669"
            bg = "#ecfdf5"
            text = "#059669"
        elif val >= 40:
            border = "#d97706"
            bg = "#fff7ed"
            text = "#d97706"

        label = AMENITY_LABELS.get(amen, amen)
        badges += (
            f'<span style="display:inline-flex;align-items:center;gap:6px;'
            f'padding:6px 10px;border-radius:999px;border:1px solid {border};'
            f'font-size:0.76rem;font-weight:700;color:{text};background:{bg};">'
            f'{icon} {label}</span>'
        )

    st.caption(
        "Overall nearby access to each amenity type, not just the nearest amenity: "
    )

    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 14px 0;">{badges}</div>',
        unsafe_allow_html=True,
    )


    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("✕ Pass", key=f"pass_{current_card['listing_id']}", use_container_width=True):
            record_swipe(session["session_id"], str(current_card["listing_id"]), "left")
            st.rerun()

    with c2:
        if st.button("View details", key=f"deck_detail_{current_card['listing_id']}", use_container_width=True):
            show_listing_detail(current_card["listing_id"])

    with c3:
        if st.button("♥ Save", key=f"save_{current_card['listing_id']}", type="primary", use_container_width=True):
            record_swipe(session["session_id"], str(current_card["listing_id"]), "right")
            st.rerun()


def _render_swipe_controls(session_id: str, listing_id: str | None):
    if not listing_id:
        return

    _, col1, col2, _ = st.columns([1.2, 1, 1, 1.2])
    with col1:
        if st.button("✕ Pass", key=f"pass_{listing_id}", use_container_width=True):
            record_swipe(session_id, str(listing_id), "left")
            st.rerun()
    with col2:
        if st.button("♥ Save", key=f"save_{listing_id}", type="primary", use_container_width=True):
            record_swipe(session_id, str(listing_id), "right")
            st.rerun()


def _render_deck_done(session: dict, listings_df: pd.DataFrame):
    liked = session["liked_ids"]
    passed = session["passed_ids"]

    st.markdown(
        f"""
        <div style="text-align:center;padding:2rem 1rem;">
            <div style="font-size:3rem;margin-bottom:0.8rem;">🎉</div>
            <h2 style="font-size:1.6rem;font-weight:800;color:#0f172a;margin-bottom:0.4rem;">
            You've seen them all</h2>
            <p style="font-size:0.88rem;color:#9ca3af;margin-bottom:1.6rem;">
            Head to the <strong>Saved</strong> tab to review your picks.</p>
            <div style="display:flex;gap:24px;justify-content:center;margin-bottom:1.8rem;">
                <div>
                    <div style="font-size:2rem;font-weight:800;color:#059E87;">{len(liked)}</div>
                    <div style="font-size:0.72rem;color:#9ca3af;font-weight:600;">Saved</div>
                </div>
                <div>
                    <div style="font-size:2rem;font-weight:800;color:#9ca3af;">{len(passed)}</div>
                    <div style="font-size:0.72rem;color:#9ca3af;font-weight:600;">Passed</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Review saved →", type="primary", use_container_width=True):
            st.session_state.active_page = "Saved"
            st.rerun()
    with c2:
        if st.button("Restart deck", use_container_width=True):
            for s in st.session_state.search_sessions:
                if s["session_id"] == session["session_id"]:
                    s["unseen_ids"] = list(listings_df["listing_id"].astype(str).values)
                    s["liked_ids"] = []
                    s["passed_ids"] = []
                    s["extra_saved_rows"] = []

            st.session_state["compare_selected_ids"] = []
            st.session_state["selected_shortlist_for_compare"] = []
            st.session_state["custom_compare_rows"] = []

            st.rerun()


def _build_single_card_html(card_json: str) -> str:
    card = json.loads(card_json)

    budget = card.get("budget")
    if budget is not None:
        budget_text = f"${budget:,}"
    else:
        budget_text = "Not set"

    budget_gap = card.get("budget_gap")
    if budget_gap is not None:
        budget_gap_text = f"{budget_gap:+,}"
        budget_gap_color = "#059E87" if budget_gap >= 0 else "#dc2626"
    else:
        budget_gap_text = "N/A"
        budget_gap_color = "#64748b"

    area_sqft = card.get("area_sqft", 0)
    storey = ("Level " + card.get("storey")) if card.get("storey") else "-"
    remaining_lease = card.get("remaining_lease") or "-"
    diff_pct = float(card.get("diff_pct", 0))

    return f"""
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: Inter, system-ui, -apple-system, sans-serif;
        }}

        .wrap {{
            max-width: 920px;
            margin: 0 auto;
            padding: 0;
            background: transparent;
        }}

        .card {{
            border-radius: 28px;
            background:
                radial-gradient(circle at top right, rgba(59,130,246,0.10), transparent 28%),
                linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(226,232,240,0.95);
            box-shadow: 0 20px 45px rgba(15,23,42,0.10);
            padding: 20px;
            color: #0f172a;
        }}

        .topbar {{
            display:flex;
            justify-content:space-between;
            align-items:flex-start;
            gap:10px;
            margin-bottom:14px;
        }}

        .title {{
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.02em;
        }}

        .sub {{
            margin-top: 6px;
            color: #64748b;
            font-size: 0.88rem;
            line-height: 1.45;
        }}

        .tag {{
            padding: 7px 12px;
            border-radius: 999px;
            color: white;
            font-weight: 700;
            font-size: 0.74rem;
            white-space: nowrap;
        }}

        .card-grid {{
            display: grid;
            grid-template-columns: 1.35fr 0.95fr;
            gap: 16px;
            align-items: start;
            margin-top: 14px;
        }}

        .pricebox {{
            background: rgba(255,255,255,0.9);
            border: 1px solid #e2e8f0;
            border-radius: 20px;
            padding: 16px;
        }}

        .price {{
            font-size: 1.55rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        .fair {{
            margin-top: 4px;
            color: #64748b;
            font-size: 0.9rem;
        }}

        .budgetbox {{
            margin-top: 12px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 14px;
        }}

        .budget-title {{
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #64748b;
            margin-bottom: 8px;
        }}

        .budget-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            color: #334155;
            margin-top: 6px;
        }}

        .meta {{
            display:flex;
            gap:8px;
            flex-wrap:wrap;
            margin-top:12px;
        }}

        .pill {{
            display:inline-flex;
            align-items:center;
            gap:6px;
            padding:7px 11px;
            border-radius:999px;
            border:1px solid #e2e8f0;
            background:#fff;
            color:#334155;
            font-size:0.76rem;
            font-weight:600;
        }}

        .match {{
            margin-top:14px;
            background: linear-gradient(180deg, #fff7ed 0%, #fffbeb 100%);
            border:1px solid #fed7aa;
            border-radius:18px;
            padding:14px;
        }}

        .match-title {{
            font-size:0.72rem;
            font-weight:800;
            color:#c2410c;
            text-transform:uppercase;
            letter-spacing:0.08em;
            margin-bottom:6px;
        }}

        .match-text {{
            font-size:0.85rem;
            line-height:1.5;
            color:#7c2d12;
        }}

        .map {{
            border-radius:18px;
            overflow:hidden;
            border:1px solid #e2e8f0;
            min-height:240px;
            background:#e2e8f0;
        }}

        .map iframe {{
            width:100%;
            height:240px;
            border:0;
        }}

        .footer {{
            margin-top:12px;
            text-align:center;
            color:#94a3b8;
            font-size:0.78rem;
            font-weight:600;
        }}

        @media (max-width: 640px) {{
            .wrap {{
                max-width: 390px;
            }}

            .card-grid {{
                grid-template-columns: 1fr;
            }}

            .map iframe {{
                height:180px;
            }}
        }}
    </style>
    </head>
    <body>
        <div class="wrap">
            <div class="card">
                <div class="topbar">
                    <div>
                        <div class="title">{card["town"]} · {card["flat_type"]}</div>
                        <div class="sub">{card["address"] or "Address unavailable"}</div>
                    </div>
                    <div class="tag" style="background:{card["label_color"]};">
                        {card["label"]}
                    </div>
                </div>

                <div class="card-grid">
                    <div>
                        <div class="pricebox">
                            <div class="price">${card["asking"]:,}</div>
                            <div class="fair">Predicted fair value: ${card["predicted"]:,}</div>
                        </div>

                        <div class="budgetbox">
                            <div class="budget-title">Budget check</div>
                            <div class="budget-row">
                                <span>Your budget</span>
                                <strong>{budget_text}</strong>
                            </div>
                            <div class="budget-row">
                                <span>Headroom</span>
                                <strong style="color:{budget_gap_color};">{budget_gap_text}</strong>
                            </div>
                        </div>

                        <div class="meta">
                            <div class="pill">📐 {area_sqft} sqft</div>
                            <div class="pill">🏢 {storey}</div>
                            <div class="pill">⏳ {remaining_lease}</div>
                            <div class="pill">💹 {diff_pct:+.1f}% vs model</div>
                        </div>

                        <div class="match">
                            <div class="match-title">Why it matches</div>
                            <ul style="margin:6px 0 0 18px;padding:0;color:#7c2d12;font-size:0.82rem;line-height:1.4;font-weight:700;">
                                <li>{card["why_primary"]}</li>
                                {f'<li>{card["why_secondary"]}</li>' if card.get("why_secondary") else ""}
                            </ul>
                        </div>
                    </div>

                    <div>
                        <div class="map">
                            <iframe src="{card["map_url"]}" loading="lazy"></iframe>
                        </div>
                    </div>
                </div>

                <div class="footer">Use the Pass / Save buttons below</div>
            </div>
        </div>
    </body>
    </html>
    """