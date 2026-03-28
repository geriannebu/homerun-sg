"""
frontend/components/listing_detail.py

Shared listing detail dialog — call show_listing_detail(listing_id) from any page.
Shows price analysis, flat details, per-amenity scores, match scores, and actions.
"""

import hashlib
import streamlit as st

from backend.utils.formatters import fmt_sgd
from frontend.state.session import record_swipe

AMENITY_ICONS = {
    "mrt": "🚇", "bus": "🚌", "healthcare": "🏥",
    "schools": "🏫", "hawker": "🍜", "retail": "🛍️",
}
AMENITY_LABELS_FULL = {
    "mrt": "MRT Access", "bus": "Bus Connectivity", "healthcare": "Healthcare",
    "schools": "Schools", "hawker": "Hawker Centres", "retail": "Retail & Shops",
}


def _val_style(val_label: str) -> tuple[str, str]:
    """Return (color, bg) for a valuation label."""
    if "Steal" in val_label:  return "#059E87", "rgba(5,150,105,0.08)"
    if "Fair"  in val_label:  return "#2563eb", "rgba(37,99,235,0.08)"
    if "Slight" in val_label: return "#d97706", "rgba(217,119,6,0.08)"
    return "#dc2626", "rgba(220,38,38,0.08)"


def _score_bar_html(label: str, score: float, icon: str = "") -> str:
    s = max(0.0, min(100.0, float(score)))
    color = "#059E87" if s >= 70 else "#d97706" if s >= 45 else "#e11d48"
    return f"""
    <div style="margin-bottom:9px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
            <span style="font-size:0.76rem;font-weight:600;color:#374151;">{icon} {label}</span>
            <span style="font-size:0.76rem;font-weight:800;color:{color};">{s:.0f}</span>
        </div>
        <div style="height:5px;border-radius:3px;background:#f1f5f9;overflow:hidden;">
            <div style="width:{s:.1f}%;height:100%;background:{color};border-radius:3px;"></div>
        </div>
    </div>"""


def _per_amenity_score(listing_id: str, key: str, base_score: float, rank: list) -> float:
    """Generate a deterministic per-amenity score using a hash of listing_id + key."""
    h = int(hashlib.md5(f"{listing_id}{key}".encode()).hexdigest(), 16)
    variation = (h % 27) - 13
    priority_bonus = 14 if rank and key == rank[0] else 7 if rank and key in rank[:2] else 0
    return max(0.0, min(100.0, base_score + priority_bonus + variation))


@st.dialog("Listing Details", width="large")
def show_listing_detail(listing_id: str):
    """Full-detail dialog for a listing. Call with the listing ID."""

    # ── Locate listing across sessions ────────────────────────────────────────
    row_data = None
    session_data = None
    for s in st.session_state.get("search_sessions", []):
        if s.get("bundle") is None:
            continue
        df = s["bundle"]["listings_df"]
        match = df[df["listing_id"] == listing_id]
        if not match.empty:
            row_data = match.iloc[0].to_dict()
            session_data = s
            break

    if row_data is None:
        st.error("Listing not found.")
        return

    # ── Derived values ─────────────────────────────────────────────────────
    diff      = float(row_data.get("asking_vs_predicted_pct", 0))
    val_label = str(row_data.get("valuation_label", ""))
    val_color, val_bg = _val_style(val_label)
    sign      = "+" if diff >= 0 else ""

    asking    = int(row_data.get("asking_price", 0))
    predicted = int(row_data.get("predicted_price", 0))

    # Scores
    overall  = float(row_data.get("overall_value_score", 0))
    amenity  = float(row_data.get("amenity_score", 65))
    value    = float(row_data.get("value_score", 0))
    final    = float(row_data.get("final_score", overall))
    budget_s = float(row_data.get("budget_score", 0))

    rank = []
    if session_data:
        rank = getattr(session_data["inputs"], "amenity_rank", [])

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-start;
                    padding-bottom:1rem;margin-bottom:1rem;border-bottom:1px solid #f0f4f8;">
            <div>
                <h2 style="font-size:1.35rem;font-weight:800;color:#0f172a;
                           letter-spacing:-0.03em;margin:0 0 4px;">{row_data.get('town','')}</h2>
                <p style="font-size:0.82rem;color:#6b7280;margin:0;">
                    {row_data.get('flat_type','')} &nbsp;·&nbsp;
                    {row_data.get('floor_area_sqm','')} sqm &nbsp;·&nbsp;
                    Storey {row_data.get('storey_range','')} &nbsp;·&nbsp;
                    <span style="color:#b0b0c0;">ID {listing_id}</span>
                </p>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.3rem;font-weight:800;color:#0f172a;letter-spacing:-0.025em;">
                    {fmt_sgd(asking)}</div>
                <div style="font-size:0.76rem;color:#9ca3af;margin-top:2px;">
                    est. {fmt_sgd(predicted)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_r = st.columns([1.15, 1])

    # ── Left column: price + match scores ────────────────────────────────────
    with col_l:
        # Price analysis card
        st.markdown(
            "<p style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.1em;color:#94a3b8;margin-bottom:6px;'>Price Analysis</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="background:{val_bg};border:1px solid {val_color}33;
                        border-radius:14px;padding:14px 16px;margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;padding:5px 0;
                            border-bottom:1px solid {val_color}1a;">
                    <span style="font-size:0.8rem;color:#6b7280;">Asking price</span>
                    <span style="font-size:0.85rem;font-weight:700;color:#0f172a;">{fmt_sgd(asking)}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:5px 0;
                            border-bottom:1px solid {val_color}1a;">
                    <span style="font-size:0.8rem;color:#6b7280;">Model estimate</span>
                    <span style="font-size:0.85rem;font-weight:700;color:#0f172a;">{fmt_sgd(predicted)}</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:5px 0;
                            border-bottom:1px solid {val_color}1a;">
                    <span style="font-size:0.8rem;color:#6b7280;">vs estimate</span>
                    <span style="font-size:0.85rem;font-weight:800;color:{val_color};">{sign}{diff:.1f}%</span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:6px 0 0;">
                    <span style="font-size:0.8rem;color:#6b7280;">Valuation</span>
                    <span style="font-size:0.78rem;font-weight:700;color:{val_color};
                          background:{val_bg};padding:3px 10px;border-radius:999px;
                          border:1.5px solid {val_color}55;">{val_label}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Match score breakdown
        st.markdown(
            "<p style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.1em;color:#94a3b8;margin-bottom:8px;'>Match Scores</p>",
            unsafe_allow_html=True,
        )
        bars = (
            _score_bar_html("Overall Match", final, "🎯") +
            _score_bar_html("Value Score", value, "💰") +
            _score_bar_html("Amenity Score", amenity, "📍") +
            _score_bar_html("Budget Fit", budget_s, "💼")
        )
        st.markdown(bars, unsafe_allow_html=True)

    # ── Right column: flat details + amenity breakdown ────────────────────────
    with col_r:
        st.markdown(
            "<p style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.1em;color:#94a3b8;margin-bottom:6px;'>Flat Details</p>",
            unsafe_allow_html=True,
        )
        details = [
            ("Flat type",   row_data.get("flat_type", "")),
            ("Floor area",  f"{row_data.get('floor_area_sqm', '')} sqm"),
            ("Storey",      str(row_data.get("storey_range", ""))),
        ]
        rows_html = ""
        for k, v in details:
            rows_html += (
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:6px 0;border-bottom:1px solid #f4f6f8;'>"
                f"<span style='font-size:0.79rem;color:#6b7280;'>{k}</span>"
                f"<span style='font-size:0.8rem;font-weight:700;color:#0f172a;'>{v}</span>"
                f"</div>"
            )
        st.markdown(
            f"<div style='background:#f8fafc;border-radius:12px;padding:10px 14px;"
            f"margin-bottom:14px;'>{rows_html}</div>",
            unsafe_allow_html=True,
        )

        # Per-amenity scores
        st.markdown(
            "<p style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.1em;color:#94a3b8;margin-bottom:8px;'>Amenity Scoring</p>",
            unsafe_allow_html=True,
        )
        amenity_html = ""
        for key in ["mrt", "bus", "healthcare", "schools", "hawker", "retail"]:
            icon  = AMENITY_ICONS[key]
            label = AMENITY_LABELS_FULL[key]
            score = _per_amenity_score(listing_id, key, amenity, rank)
            color = "#059E87" if score >= 70 else "#d97706" if score >= 45 else "#e11d48"
            priority_star = " ⭐" if rank and key == rank[0] else ""
            amenity_html += f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span style="font-size:1rem;width:20px;text-align:center;flex-shrink:0;">{icon}</span>
                <div style="flex:1;min-width:0;">
                    <div style="font-size:0.73rem;font-weight:600;color:#374151;margin-bottom:2px;">
                        {label}{priority_star}</div>
                    <div style="height:5px;border-radius:3px;background:#f1f5f9;overflow:hidden;">
                        <div style="width:{score:.0f}%;height:100%;background:{color};border-radius:3px;"></div>
                    </div>
                </div>
                <span style="font-size:0.73rem;font-weight:800;color:{color};
                      min-width:24px;text-align:right;flex-shrink:0;">{score:.0f}</span>
            </div>"""
        st.markdown(amenity_html, unsafe_allow_html=True)

    # ── Actions ──────────────────────────────────────────────────────────────
    st.markdown(
        "<hr style='border:none;border-top:1px solid #f0f4f8;margin:1rem 0 0.9rem;'>",
        unsafe_allow_html=True,
    )

    is_saved   = session_data and listing_id in session_data.get("liked_ids", [])
    is_super   = session_data and listing_id in session_data.get("super_ids", [])
    is_compare = listing_id in st.session_state.get("compare_selected_ids", [])

    c1, c2, c3 = st.columns(3)
    with c1:
        if not is_saved:
            if st.button("♥  Save", key=f"detail_save_{listing_id}",
                         use_container_width=True, type="primary"):
                if session_data:
                    record_swipe(session_data["session_id"], listing_id, "right")
                    st.rerun()
        else:
            st.markdown(
                "<div style='text-align:center;padding:8px 0;font-size:0.82rem;"
                "font-weight:700;color:#059E87;'>♥ Saved</div>",
                unsafe_allow_html=True,
            )
    with c2:
        if not is_super:
            if st.button("⭐  Super-save", key=f"detail_super_{listing_id}",
                         use_container_width=True):
                if session_data:
                    record_swipe(session_data["session_id"], listing_id, "up")
                    st.rerun()
        else:
            st.markdown(
                "<div style='text-align:center;padding:8px 0;font-size:0.82rem;"
                "font-weight:700;color:#d97706;'>⭐ Super-saved</div>",
                unsafe_allow_html=True,
            )
    with c3:
        compare_label = "✓ In compare" if is_compare else "⚖️  Compare"
        if st.button(compare_label, key=f"detail_compare_{listing_id}",
                     use_container_width=True):
            cur = st.session_state.get("compare_selected_ids", [])
            if is_compare:
                st.session_state.compare_selected_ids = [x for x in cur if x != listing_id]
            else:
                st.session_state.compare_selected_ids = cur + [listing_id]
            st.rerun()
