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
        import streamlit.components.v1 as components
        components.html(
            """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;font-family:'DM Sans',-apple-system,sans-serif;background:transparent;overflow:hidden;}

@keyframes bob   {0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
@keyframes fadein{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse {0%,100%{opacity:0.30}50%{opacity:0.60}}
@keyframes drift1{0%,100%{transform:translate(0,0)}40%{transform:translate(8px,-12px)}80%{transform:translate(-6px,8px)}}
@keyframes drift2{0%,100%{transform:translate(0,0)}35%{transform:translate(-10px,9px)}70%{transform:translate(7px,-7px)}}
@keyframes drift3{0%,100%{transform:translate(0,0)}50%{transform:translate(6px,14px)}}

.scene{
  position:relative;width:100%;height:340px;overflow:hidden;
  background:#fafafa;border-radius:20px;
  border:1.5px solid rgba(255,68,88,0.10);
}
/* soft coral glow behind hero */
.glow{
  position:absolute;top:38%;left:50%;transform:translate(-50%,-50%);
  width:320px;height:200px;
  background:radial-gradient(ellipse,rgba(255,68,88,0.10) 0%,transparent 65%);
  animation:pulse 4s ease-in-out infinite;pointer-events:none;
}
/* ghost emojis — background depth */
.ghost{position:absolute;line-height:1;filter:grayscale(0.3);}

/* centre column */
.centre{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;z-index:5;
}
.hero-wrap{
  font-size:3.8rem;line-height:1;margin-bottom:1.1rem;
  filter:drop-shadow(0 6px 18px rgba(255,68,88,0.22));
  animation:bob 3.2s ease-in-out infinite,fadein 0.6s ease both;
  animation-delay:0s,0.1s;
}
.title{
  font-size:1.25rem;font-weight:800;letter-spacing:-0.03em;
  color:#0f172a;margin-bottom:0.4rem;
  animation:fadein 0.55s ease both;animation-delay:0.25s;
}
.hint{
  font-size:0.85rem;font-weight:500;color:#94a3b8;max-width:280px;
  text-align:center;line-height:1.6;
  animation:fadein 0.55s ease both;animation-delay:0.4s;
}
.hint strong{color:#FF6B6B;font-weight:700;}
.pill{
  margin-top:1.1rem;display:inline-flex;align-items:center;gap:6px;
  padding:7px 16px;border-radius:999px;
  background:rgba(255,68,88,0.07);border:1px solid rgba(255,68,88,0.18);
  font-size:0.78rem;font-weight:700;color:#FF4458;
  animation:fadein 0.55s ease both;animation-delay:0.55s;
}
</style>
</head>
<body>
<div class="scene">
  <div class="glow"></div>

  <!-- ghost emojis — subtle depth layer -->
  <span class="ghost" style="top:8%;left:6%;font-size:2rem;opacity:0.12;animation:drift1 9s ease-in-out infinite;">🏠</span>
  <span class="ghost" style="top:10%;right:8%;font-size:1.7rem;opacity:0.10;animation:drift2 11s ease-in-out infinite;animation-delay:-3s;">🏡</span>
  <span class="ghost" style="top:55%;left:4%;font-size:1.3rem;opacity:0.09;animation:drift3 13s ease-in-out infinite;animation-delay:-5s;">🔑</span>
  <span class="ghost" style="top:58%;right:5%;font-size:1.4rem;opacity:0.09;animation:drift1 10s ease-in-out infinite;animation-delay:-7s;">🌳</span>
  <span class="ghost" style="bottom:10%;left:22%;font-size:1.1rem;opacity:0.08;animation:drift2 14s ease-in-out infinite;animation-delay:-2s;">✨</span>
  <span class="ghost" style="bottom:12%;right:24%;font-size:1.0rem;opacity:0.08;animation:drift3 12s ease-in-out infinite;animation-delay:-9s;">💫</span>

  <!-- centre -->
  <div class="centre">
    <div class="hero-wrap">💾</div>
    <div class="title">Nothing saved yet</div>
    <div class="hint">Swipe right on flats in <strong>Discover</strong> to save them here.</div>
    <div class="pill">↙ Head to Discover to start swiping</div>
  </div>
</div>
</body>
</html>""",
            height=350,
            scrolling=False,
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
