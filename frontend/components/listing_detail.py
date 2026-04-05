import math
from typing import Any, Dict

import numpy as np
import pandas as pd
import streamlit as st

from backend.utils.formatters import fmt_sgd
from frontend.state.session import record_swipe


def _map_iframe(lat, lon, height: int = 220) -> str:
    if lat is None or lon is None:
        return ""
    src = (
        f"https://www.openstreetmap.org/export/embed.html"
        f"?bbox={lon-0.01},{lat-0.006},{lon+0.01},{lat+0.006}"
        f"&layer=mapnik&marker={lat},{lon}"
    )
    return f'<iframe src="{src}" width="100%" height="{height}" style="border:none;border-radius:12px;"></iframe>'


def _proximity_label(dist):
    if dist is None:
        return "Very far"
    try:
        if math.isnan(float(dist)) or float(dist) > 1500:
            return "Very far"
    except Exception:
        return "Very far"

    if dist > 1000:
        return "Far"
    if dist > 600:
        return "Moderate"
    if dist > 300:
        return "Close"
    return "Very close"


def _format_distance(dist):
    if dist is None:
        return "N/A"
    try:
        if math.isnan(float(dist)):
            return "N/A"
        return f"{int(round(float(dist))):,} m"
    except Exception:
        return "N/A"


def _val_style(diff):
    if diff <= -5:
        return "Great Deal", "#059E87"
    if diff <= 3:
        return "Fair Value", "#2563eb"
    if diff <= 10:
        return "Slightly High", "#d97706"
    return "Overpriced", "#dc2626"


def _find_listing_row(listing_id):
    target_id = str(listing_id)

    for s in st.session_state.get("search_sessions", []):
        df = s["bundle"]["listings_df"].copy()
        if "listing_id" not in df.columns:
            continue

        match = df[df["listing_id"].astype(str) == target_id]
        if not match.empty:
            return match.iloc[0], s

    return None, None


def _sqm_to_sqft(area_sqm) -> int:
    try:
        return int(round(float(area_sqm) * 10.7639))
    except Exception:
        return 0


def _score_color(score: float) -> str:
    if score >= 75:
        return "#059669"
    if score >= 50:
        return "#d97706"
    return "#dc2626"


def _proximity_bg(dist) -> tuple[str, str]:
    label = _proximity_label(dist)
    if label == "Very close":
        return "#ecfdf5", "#059669"
    if label == "Close":
        return "#eff6ff", "#2563eb"
    if label == "Moderate":
        return "#fff7ed", "#d97706"
    return "#fef2f2", "#dc2626"


def _score_badge_html(score: float) -> str:
    color = _score_color(score)
    bg = {
        "#059669": "#ecfdf5",
        "#d97706": "#fff7ed",
        "#dc2626": "#fef2f2",
    }.get(color, "#f8fafc")
    return (
        f"<span style='display:inline-block;padding:5px 10px;border-radius:999px;"
        f"background:{bg};color:{color};font-weight:800;font-size:0.78rem;"
        f"border:1px solid rgba(15,23,42,0.06);'>{score:.0f}/100</span>"
    )


def _proximity_badge_html(dist) -> str:
    bg, color = _proximity_bg(dist)
    label = _proximity_label(dist)
    return (
        f"<span style='display:inline-block;padding:5px 10px;border-radius:999px;"
        f"background:{bg};color:{color};font-weight:700;font-size:0.78rem;"
        f"border:1px solid rgba(15,23,42,0.06);'>{label}</span>"
    )


def _apply_swipe_local(session_id: str, listing_id: str, direction: str):
    listing_id = str(listing_id)

    for s in st.session_state.get("search_sessions", []):
        if s.get("session_id") != session_id:
            continue

        liked_ids = [str(x) for x in s.get("liked_ids", [])]
        passed_ids = [str(x) for x in s.get("passed_ids", [])]
        unseen_ids = [str(x) for x in s.get("unseen_ids", [])]

        if direction == "right":
            if listing_id not in liked_ids:
                liked_ids.append(listing_id)
            passed_ids = [x for x in passed_ids if x != listing_id]
        elif direction == "left":
            if listing_id not in passed_ids:
                passed_ids.append(listing_id)
            liked_ids = [x for x in liked_ids if x != listing_id]

        unseen_ids = [x for x in unseen_ids if x != listing_id]

        s["liked_ids"] = liked_ids
        s["passed_ids"] = passed_ids
        s["unseen_ids"] = unseen_ids
        break


def _safe_numeric(value):
    try:
        if value is None or pd.isna(value):
            return np.nan
        return float(value)
    except Exception:
        return np.nan
    
def _format_walk_minutes(mins):
    if mins is None:
        return "N/A"
    try:
        mins = float(mins)
        if math.isnan(mins):
            return "N/A"
        return f"{mins:.0f} min"
    except Exception:
        return "N/A"


def show_listing_detail(payload: Dict[str, Any] | str | int, show_actions: bool = True):
    import json

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass

    if isinstance(payload, dict):
        listing_id = payload.get("listing_id") or payload.get("id")
        row = payload
    elif isinstance(payload, (int, str)):
        listing_id = payload
        row = None
    else:
        st.error("Invalid payload type")
        return

    if listing_id is None:
        st.error("Listing ID missing")
        return

    db_row, session_data = _find_listing_row(listing_id)

    if db_row is not None:
        row = db_row
        listing_id = str(db_row.get("listing_id", listing_id))

    if row is None:
        st.error("Listing not found.")
        return

    dialog_title = f"Listing Details · {listing_id}"

    @st.dialog(dialog_title, width="large")
    def _render_dialog():
        asking = int(float(row.get("asking_price", 0) or 0))
        predicted = int(float(row.get("predicted_price", 0) or 0))

        diff_raw = row.get("asking_vs_predicted_pct", row.get("valuation_pct", 0))
        diff = float(diff_raw) if diff_raw is not None and not pd.isna(diff_raw) else 0.0

        ci_low = row.get("predicted_price_lower")
        ci_high = row.get("predicted_price_upper")
        try:
            ci_low = int(ci_low) if ci_low is not None and not math.isnan(float(ci_low)) else None
            ci_high = int(ci_high) if ci_high is not None and not math.isnan(float(ci_high)) else None
        except (TypeError, ValueError):
            ci_low = ci_high = None

        town = str(row.get("town", ""))
        flat_type = str(row.get("flat_type", ""))
        area_sqm = float(row.get("floor_area_sqm", 0) or 0)
        area_sqft = _sqm_to_sqft(area_sqm)
        storey = row.get("storey_range", row.get("storey_midpoint", ""))
        address = str(row.get("address", row.get("full_address", "")))
        lat = row.get("lat")
        lon = row.get("lon")
        remaining = row.get("remaining_lease", row.get("remaining_lease_years"))

        train_dist = row.get("train_1_dist_m")
        bus_dist = row.get("bus_1_dist_m")
        school_dist = row.get("school_1_dist_m")
        hawker_dist = row.get("hawker_1_dist_m")
        mall_dist = row.get("mall_1_dist_m")
        health_dist = row.get("polyclinic_1_dist_m")
        supermarket_dist = row.get("supermarket_1_dist_m")

        train_walk = row.get("walk_train_min1")
        bus_walk = row.get("walk_bus_min1")
        school_walk = row.get("walk_primary_school_min1")
        hawker_walk = row.get("walk_hawker_min1")
        mall_walk = row.get("walk_mall_min1")
        health_walk = row.get("walk_polyclinic_min1")
        supermarket_walk = row.get("walk_supermarket_min1")

        amenity_score = _safe_numeric(row.get("amenity_score"))
        value_score = _safe_numeric(row.get("value_score"))
        final_score = _safe_numeric(row.get("final_score"))

        if pd.notna(amenity_score):
            amenity_score *= 100
        if pd.notna(value_score):
            value_score *= 100
        if pd.notna(final_score):
            final_score *= 100

        has_score_breakdown = (
            pd.notna(amenity_score)
            or pd.notna(value_score)
            or pd.notna(final_score)
        )

        amenity_color = _score_color(amenity_score) if pd.notna(amenity_score) else "#94a3b8"
        value_color = _score_color(value_score) if pd.notna(value_score) else "#94a3b8"
        final_color = _score_color(final_score) if pd.notna(final_score) else "#94a3b8"

        val_label, val_color = _val_style(diff)
        sign = "+" if diff >= 0 else ""

        if show_actions:
            liked_ids = [str(x) for x in session_data.get("liked_ids", [])] if session_data else []
            passed_ids = [str(x) for x in session_data.get("passed_ids", [])] if session_data else []
            listing_id_str = str(listing_id)

            is_saved = listing_id_str in liked_ids
            is_passed = listing_id_str in passed_ids

            col1, col2 = st.columns(2)
            with col1:
                if not is_passed:
                    if st.button("✕ Pass", use_container_width=True, key=f"detail_pass_{listing_id_str}"):
                        if session_data:
                            _apply_swipe_local(session_data["session_id"], listing_id_str, "left")
                            record_swipe(session_data["session_id"], listing_id_str, "left")
                        st.rerun()
                else:
                    st.success("Passed")

            with col2:
                if not is_saved:
                    if st.button("♥ Save", use_container_width=True, type="primary", key=f"detail_save_{listing_id_str}"):
                        if session_data:
                            _apply_swipe_local(session_data["session_id"], listing_id_str, "right")
                            record_swipe(session_data["session_id"], listing_id_str, "right")
                        st.rerun()
                else:
                    st.success("Saved ♥")

        st.markdown(f"## {town} · {flat_type}")
        st.caption(address or "Address unavailable")

        st.markdown(
            f"""
            <div style="
                margin: 8px 0 16px 0;
                display:inline-block;
                padding:7px 13px;
                border-radius:999px;
                background:{val_color};
                color:white;
                font-weight:700;
                font-size:0.82rem;">
                {val_label}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style="
                border:1px solid #e2e8f0;
                border-radius:20px;
                padding:18px 18px 14px 18px;
                background:linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                box-shadow:0 10px 24px rgba(15,23,42,0.06);
                margin-bottom:14px;">
                <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;
                            letter-spacing:0.08em;color:#94a3b8;margin-bottom:10px;">
                    Price snapshot
                </div>
                <div style="display:flex;gap:14px;flex-wrap:wrap;">
                    <div style="flex:1;min-width:160px;">
                        <div style="font-size:0.76rem;color:#64748b;font-weight:700;">Asking price</div>
                        <div style="font-size:1.45rem;font-weight:800;color:#0f172a;margin-top:4px;">
                            {fmt_sgd(asking)}
                        </div>
                    </div>
                    <div style="flex:1;min-width:160px;">
                        <div style="font-size:0.76rem;color:#64748b;font-weight:700;">Predicted fair value</div>
                        <div style="font-size:1.45rem;font-weight:800;color:#0f172a;margin-top:4px;">
                            {fmt_sgd(predicted)}
                        </div>
                    </div>
                    <div style="flex:1;min-width:160px;">
                        <div style="font-size:0.76rem;color:#64748b;font-weight:700;">Value gap</div>
                        <div style="font-size:1.45rem;font-weight:800;color:{val_color};margin-top:4px;">
                            {sign}{diff:.1f}%
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if ci_low is not None and ci_high is not None:
            st.markdown(
                f"""
                <div style="
                    margin:0 0 14px 0;
                    padding:12px 14px;
                    border-radius:14px;
                    background:#eff6ff;
                    border:1px solid #bfdbfe;
                    color:#1d4ed8;
                    font-size:0.9rem;
                    font-weight:600;">
                    95% predicted price range: {fmt_sgd(ci_low)} – {fmt_sgd(ci_high)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        if has_score_breakdown:
            st.markdown(
                f"""
                <div style="
                    border:1px solid #e2e8f0;
                    border-radius:20px;
                    padding:18px 18px 14px 18px;
                    background:#ffffff;
                    box-shadow:0 10px 24px rgba(15,23,42,0.05);
                    margin-bottom:14px;">
                    <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;
                                letter-spacing:0.08em;color:#94a3b8;margin-bottom:10px;">
                        Score breakdown
                    </div>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <div style="flex:1;min-width:150px;padding:14px;border-radius:16px;background:#f8fafc;border:1px solid #e2e8f0;">
                            <div style="font-size:0.74rem;color:#64748b;font-weight:700;">Amenity score</div>
                            <div style="font-size:1.35rem;font-weight:800;color:{amenity_color};margin-top:5px;">
                                {amenity_score:.1f}/100
                            </div>
                        </div>
                        <div style="flex:1;min-width:150px;padding:14px;border-radius:16px;background:#f8fafc;border:1px solid #e2e8f0;">
                            <div style="font-size:0.74rem;color:#64748b;font-weight:700;">Value score</div>
                            <div style="font-size:1.35rem;font-weight:800;color:{value_color};margin-top:5px;">
                                {value_score:.1f}/100
                            </div>
                        </div>
                        <div style="flex:1;min-width:150px;padding:14px;border-radius:16px;background:#f8fafc;border:1px solid #e2e8f0;">
                            <div style="font-size:0.74rem;color:#64748b;font-weight:700;">Match score</div>
                            <div style="font-size:1.35rem;font-weight:800;color:{final_color};margin-top:5px;">
                                {final_score:.1f}/100
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div style="
                border:1px solid #e2e8f0;
                border-radius:20px;
                padding:18px 18px 14px 18px;
                background:#ffffff;
                box-shadow:0 10px 24px rgba(15,23,42,0.05);
                margin-bottom:14px;">
                <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;
                            letter-spacing:0.08em;color:#94a3b8;margin-bottom:10px;">
                    Flat details
                </div>
                <div style="display:flex;gap:14px;flex-wrap:wrap;">
                    <div style="flex:1;min-width:160px;">
                        <div style="font-size:0.76rem;color:#64748b;font-weight:700;">Floor area</div>
                        <div style="font-size:1.05rem;font-weight:800;color:#0f172a;margin-top:4px;">
                            {area_sqft} sqft
                        </div>
                    </div>
                    <div style="flex:1;min-width:160px;">
                        <div style="font-size:0.76rem;color:#64748b;font-weight:700;">Storey</div>
                        <div style="font-size:1.05rem;font-weight:800;color:#0f172a;margin-top:4px;">
                            {str(storey) if storey else "-"}
                        </div>
                    </div>
                    <div style="flex:1;min-width:160px;">
                        <div style="font-size:0.76rem;color:#64748b;font-weight:700;">Remaining lease</div>
                        <div style="font-size:1.05rem;font-weight:800;color:#0f172a;margin-top:4px;">
                            {str(remaining) if remaining else "-"}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        def _pct(x):
            return x * 100 if pd.notna(x) else x

        train_score = _pct(_safe_numeric(row.get("walk_acc_train")))
        bus_score = _pct(_safe_numeric(row.get("walk_acc_bus")))
        school_score = _pct(_safe_numeric(row.get("walk_acc_primary_school")))
        hawker_score = _pct(_safe_numeric(row.get("walk_acc_hawker")))
        mall_score = _pct(_safe_numeric(row.get("walk_acc_mall")))
        health_score = _pct(_safe_numeric(row.get("walk_acc_polyclinic")))
        supermarket_score = _pct(_safe_numeric(row.get("walk_acc_supermarket")))

        amenities = [
            ("🚇 MRT", train_dist, train_walk, train_score),
            ("🚌 Bus", bus_dist, bus_walk, bus_score),
            ("🏫 Schools", school_dist, school_walk, school_score),
            ("🍜 Hawker", hawker_dist, hawker_walk, hawker_score),
            ("🛍️ Mall", mall_dist, mall_walk, mall_score),
            ("🏥 Healthcare", health_dist, health_walk, health_score),
            ("🛒 Supermarket", supermarket_dist, supermarket_walk, supermarket_score),
        ]

        has_amenity_scores = any(pd.notna(score) for _, _, _, score in amenities)
        
        if has_amenity_scores:
            header_html = """
<div style="
    display:grid;
    grid-template-columns:1.2fr 1fr 0.9fr 0.9fr 0.9fr;
    gap:10px;
    align-items:center;
    padding:0 0 10px 0;
    color:#94a3b8;
    font-size:0.72rem;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:0.06em;
    font-family: Inter, system-ui, -apple-system, sans-serif;">
    <div>Amenity</div>
    <div>
    <div>Proximity</div>
    <div style="font-size:0.62rem;font-weight:600;text-transform:none;letter-spacing:0;color:#cbd5e1;">
        to nearest amenity
    </div>
</div>
<div>
    <div>Distance</div>
    <div style="font-size:0.62rem;font-weight:600;text-transform:none;letter-spacing:0;color:#cbd5e1;">
        to nearest amenity
    </div>
</div>
<div>
    <div>Route walk time</div>
    <div style="font-size:0.62rem;font-weight:600;text-transform:none;letter-spacing:0;color:#cbd5e1;">
        to nearest amenity
    </div>
</div>
    <div>
    <div>Overall access score</div>
    <div style="font-size:0.62rem;font-weight:600;text-transform:none;letter-spacing:0;color:#cbd5e1;">
        based on nearby options
    </div>
</div>
</div>
"""
        else:
            header_html = """
<div style="
    display:grid;
    grid-template-columns:1.4fr 1fr 1fr 1fr;
    gap:10px;
    align-items:center;
    padding:0 0 10px 0;
    color:#94a3b8;
    font-size:0.72rem;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:0.06em;
    font-family: Inter, system-ui, -apple-system, sans-serif;">
    <div>Amenity</div>
    <div>Proximity</div>
    <div>Distance</div>
    <div>Actual Walk Time</div>
</div>
"""

        rows_html = ""
        for i, (label, dist, walk, score) in enumerate(amenities):
            row_bg = "#ffffff" if i % 2 == 0 else "#fcfcfd"

            if has_amenity_scores:
                grid_cols = "1.2fr 1fr 0.9fr 0.9fr 0.9fr"
                score_html = _score_badge_html(score) if pd.notna(score) else ""
                last_col = f"<div style='display:flex;justify-content:flex-start;'>{score_html}</div>"
            else:
                grid_cols = "1.4fr 1fr 1fr 1fr"
                last_col = ""

            rows_html += f"""
<div style="
    display:grid;
    grid-template-columns:{grid_cols};
    gap:10px;
    align-items:center;
    padding:12px 14px;
    margin-bottom:8px;
    border:1px solid #f1f5f9;
    border-radius:14px;
    background:{row_bg};
    font-family: Inter, system-ui, -apple-system, sans-serif;">
    <div style="font-weight:700;color:#0f172a;">{label}</div>
    <div>{_proximity_badge_html(dist)}</div>
    <div style="font-weight:600;color:#334155;">{_format_distance(dist)}</div>
    <div style="font-weight:600;color:#334155;">{_format_walk_minutes(walk)}</div>
    {last_col}
</div>
"""

        st.markdown(
            f"""
<div style="
    border:1px solid #e2e8f0;
    border-radius:20px;
    padding:18px 18px 12px 18px;
    background:#ffffff;
    box-shadow:0 10px 24px rgba(15,23,42,0.05);
    margin-bottom:14px;
    font-family: Inter, system-ui, -apple-system, sans-serif;">
    <div style="
        font-size:0.72rem;
        font-weight:800;
        text-transform:uppercase;
        letter-spacing:0.08em;
        color:#94a3b8;
        margin-bottom:10px;">
        Nearby amenities
    </div>

    {header_html}

    {rows_html}
</div>
""",
            unsafe_allow_html=True,
        )

        if lat is not None and lon is not None:
            st.markdown("### Location")
            st.markdown(_map_iframe(lat, lon), unsafe_allow_html=True)

    _render_dialog()