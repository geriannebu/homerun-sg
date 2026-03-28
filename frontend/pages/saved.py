"""
frontend/pages/saved.py

Shows all liked flats across all search sessions.
Flats are grouped by session. Super-saved flats are highlighted.
Users can click "View details" for full amenity/score breakdown,
select flats for comparison, or remove them.
"""

import pandas as pd
import streamlit as st

from backend.utils.formatters import fmt_sgd, valuation_tag_html
from frontend.state.session import get_liked_df
from frontend.components.listing_detail import show_listing_detail


def render_saved_page():
    st.markdown(
        "<h2 style='font-size:1.65rem;font-weight:800;letter-spacing:-0.03em;"
        "color:#0f172a;margin-bottom:0.3rem;'>Saved flats</h2>"
        "<p style='font-size:0.88rem;color:#9ca3af;margin-bottom:1.4rem;'>"
        "Flats you've liked or super-saved, organised by search session.</p>",
        unsafe_allow_html=True,
    )

    liked_df = get_liked_df()

    if liked_df.empty:
        st.markdown(
            """
            <div style="text-align:center;padding:3rem 1rem;">
                <div style="font-size:2.5rem;margin-bottom:0.8rem;">💾</div>
                <div style="font-size:1.1rem;font-weight:700;color:#0f172a;margin-bottom:0.4rem;">
                    Nothing saved yet</div>
                <div style="font-size:0.88rem;color:#9ca3af;">
                    Swipe right on flats in the <strong>Discover</strong> tab
                    to save them here.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── Compare CTA ──────────────────────────────────────────────────────────
    selected_ids = st.session_state.get("compare_selected_ids", [])
    all_ids      = list(liked_df["listing_id"].values)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown(
            f"<p style='font-size:0.82rem;color:#4b5563;padding-top:0.5rem;'>"
            f"<strong>{len(liked_df)}</strong> saved · "
            f"<strong>{len(selected_ids)}</strong> selected for comparison</p>",
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("Select all", use_container_width=True):
            st.session_state.compare_selected_ids = all_ids
            st.rerun()
    with c3:
        if st.button("Compare selected →", type="primary", use_container_width=True,
                     disabled=len(selected_ids) < 2):
            st.session_state.active_page = "Compare"
            st.rerun()

    st.markdown("---")

    # ── Group by session ─────────────────────────────────────────────────────
    sessions_in_saved = (
        liked_df["session_label"].unique()
        if "session_label" in liked_df.columns
        else ["All"]
    )

    for session_label in sessions_in_saved:
        if "session_label" in liked_df.columns:
            session_df = liked_df[liked_df["session_label"] == session_label]
        else:
            session_df = liked_df

        super_count = int(session_df["is_super"].sum()) if "is_super" in session_df.columns else 0
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin:1rem 0 0.7rem;'>"
            f"<div style='font-size:0.82rem;font-weight:700;color:#0f172a;'>{session_label}</div>"
            f"<div style='font-size:0.72rem;color:#9ca3af;background:#f7f8fa;"
            f"border:1px solid #e4e7ed;border-radius:999px;padding:2px 8px;'>"
            f"{len(session_df)} saved · {super_count} ⭐</div></div>",
            unsafe_allow_html=True,
        )

        for _, row in session_df.iterrows():
            lid      = str(row["listing_id"])
            is_super = bool(row.get("is_super", False))
            is_sel   = lid in selected_ids
            tag      = valuation_tag_html(row.get("valuation_label", ""))
            diff     = float(row.get("asking_vs_predicted_pct", 0))
            badge     = "⭐ Super" if is_super else "♥ Saved"
            badge_col = "#d97706" if is_super else "#059E87"

            border = "2px solid #059E87" if is_sel else "1px solid #e4e7ed"
            bg     = "#f0fdf9" if is_sel else "rgba(255,255,255,0.96)"

            st.markdown(
                f"""
                <div class="nw-listing" style="border:{border};background:{bg};">
                    <div class="nw-listing-header">
                        <div>
                            <div class="nw-listing-id">{row['listing_id']} · {row['town']}</div>
                            <div class="nw-listing-meta">
                                {row['flat_type']} · {row.get('floor_area_sqm','')} sqm
                                · Storey {row.get('storey_range','')}
                            </div>
                        </div>
                        <div>
                            <div class="nw-listing-asking">{fmt_sgd(row['asking_price'])}</div>
                            <div class="nw-listing-predicted">
                                Predicted: {fmt_sgd(row['predicted_price'])}
                            </div>
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:8px;
                                margin-top:8px;flex-wrap:wrap;">
                        {tag}
                        <span style="font-size:0.76rem;color:#9ca3af;">{diff:+.1f}% vs model</span>
                        <span style="font-size:0.72rem;font-weight:700;
                              color:{badge_col};margin-left:auto;">{badge}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            btn_a, btn_b, btn_c = st.columns([1.3, 1, 1])
            with btn_a:
                if st.button("View details →", key=f"detail_{lid}",
                             use_container_width=True, type="primary"):
                    show_listing_detail(lid)
            with btn_b:
                sel_label = "✓ Selected" if is_sel else "Select"
                if st.button(sel_label, key=f"sel_{lid}", use_container_width=True):
                    cur = st.session_state.compare_selected_ids
                    if is_sel:
                        st.session_state.compare_selected_ids = [x for x in cur if x != lid]
                    else:
                        st.session_state.compare_selected_ids = cur + [lid]
                    st.rerun()
            with btn_c:
                if st.button("Remove", key=f"rm_{lid}", use_container_width=True):
                    for s in st.session_state.search_sessions:
                        if lid in s["liked_ids"]:
                            s["liked_ids"].remove(lid)
                        if lid in s.get("super_ids", []):
                            s["super_ids"].remove(lid)
                    st.session_state.compare_selected_ids = [
                        x for x in selected_ids if x != lid
                    ]
                    st.rerun()
