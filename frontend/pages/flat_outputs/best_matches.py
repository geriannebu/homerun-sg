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
    return "#dc2626"


def _why_match(row, inputs) -> str:
    rank = getattr(inputs, "amenity_rank", [])
    top_amenities = rank[:2] if rank else []
    reasons = []

    diff = float(row.get("valuation_pct", 0))
    if diff <= -5:
        reasons.append("priced below model estimate")
    elif diff <= 3:
        reasons.append("fairly priced")

    for amen in top_amenities:
        score = float(row.get(f"walk_acc_{amen}", 0))
        if score >= 0.6:
            label = {
                "train": "strong MRT access",
                "bus": "good bus connectivity",
                "primary_school": "schools nearby",
                "hawker": "hawker food nearby",
                "mall": "shopping nearby",
                "polyclinic": "healthcare nearby",
                "supermarket": "supermarkets nearby",
            }.get(amen, amen)
            reasons.append(label)

    return " • ".join(reasons) if reasons else "Good overall fit"

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


def _serialize_card(row, inputs, budget=None) -> dict:
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
        "why": _why_match(row, inputs),
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

    if "final_score" in df.columns:
        df = df.sort_values("final_score", ascending=False)

    return df


def render_listing_tab(listings_df: pd.DataFrame):
    if listings_df is None or listings_df.empty:
        st.info("No listings available. Run a search first.")
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
    current_card = _serialize_card(current_row, inputs, budget=budget)

    st.markdown(
        """
        <div style="
            padding: 18px 18px 16px 18px;
            margin-bottom: 12px;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(255,68,88,0.12) 0%, rgba(255,107,107,0.10) 45%, rgba(255,240,244,0.95) 100%);
            border: 1px solid rgba(255,68,88,0.20);
            box-shadow: 0 10px 24px rgba(255,68,88,0.10);
        ">
            <div style="
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: #FF4458;
                margin-bottom: 6px;
            ">
                HomeRun recommendations
            </div>
            <div style="
                font-size: 1.85rem;
                font-weight: 800;
                letter-spacing: -0.04em;
                color: #7f1d3f;
                line-height: 1.05;
                margin-bottom: 6px;
            ">
                Your top-matched flats
            </div>
            <div style="
                font-size: 0.94rem;
                color: #9f1239;
                font-weight: 500;
                line-height: 1.5;
            ">
                Ranked to best match your budget, lifestyle, and amenity priorities using our in-house model.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render ONLY the current card so visuals and details stay synced
    html = _build_single_card_html(json.dumps(current_card))
    components.html(html, height=445, scrolling=False)

    score = current_card["final_score"]
    color = "#059E87" if score >= 75 else "#d97706" if score >= 50 else "#FF4458"

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
        border = "#059E87" if val >= 60 else "#cbd5e1"
        label = AMENITY_LABELS.get(amen, amen)
        badges += (
            f'<span style="display:inline-flex;align-items:center;gap:6px;'
            f'padding:6px 10px;border-radius:999px;border:1px solid {border};'
            f'font-size:0.76rem;font-weight:600;color:#334155;background:#fff;">'
            f'{icon} {label}</span>'
        )

    st.caption(
        "Overall nearby access to each amenity type, not just the nearest amenity: "
    )

    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 14px 0;">{badges}</div>',
        unsafe_allow_html=True,
    )

    _render_swipe_controls(session["session_id"], current_card["listing_id"])

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if st.button("View listing details", key=f"deck_detail_{current_card['listing_id']}", use_container_width=True):
            show_listing_detail(current_card["listing_id"])

    total = len(listings_df)
    seen = len(liked_ids) + len(passed_ids)
    st.markdown(
        f"<p style='text-align:center;font-size:0.8rem;color:#94a3b8;margin-top:0.5rem;'>"
        f"{seen} of {total} seen · {len(liked_ids)} saved · {len(passed_ids)} passed</p>",
        unsafe_allow_html=True,
    )


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
    storey = card.get("storey") or "-"
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
                            <div class="match-text">{card["why"]}</div>
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