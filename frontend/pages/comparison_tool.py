import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from backend.schemas.inputs import UserInputs
from backend.utils.formatters import fmt_sgd
from backend.services.recommender import _amenity_score, RANKING_ALPHA


# =========================================================
# Helpers
# =========================================================
def _safe_numeric(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)

def _sqm_to_sqft(val):
    try:
        if pd.isna(val):
            return None
        return round(float(val) * 10.7639)
    except Exception:
        return None

def _comparison_value_score(value_delta_pct: float, clip: float = 0.20) -> float:
    pct = value_delta_pct / 100.0
    clipped = float(np.clip(pct, -clip, clip))
    return round((clipped + clip) / (2 * clip), 4)


def _resolve_alpha(inputs: UserInputs) -> float:
    alpha = getattr(inputs, "alpha", None)
    if alpha is not None:
        try:
            return float(alpha)
        except Exception:
            pass

    profile = getattr(inputs, "ranking_profile", None) or getattr(inputs, "profile", None)
    if profile in RANKING_ALPHA:
        return RANKING_ALPHA[profile]

    return RANKING_ALPHA["balanced"]


def _flat_letter_label(idx: int) -> str:
    return f"Flat {chr(65 + idx)}"


def _get_flat_label_map(selected_df: pd.DataFrame) -> dict:
    return {
        row.get("listing_id"): _flat_letter_label(i)
        for i, (_, row) in enumerate(selected_df.iterrows())
    }


def _prepare_comparison_scores(df: pd.DataFrame, inputs: UserInputs) -> pd.DataFrame:
    df = df.copy()

    for col in [
        "asking_price",
        "predicted_price",
        "valuation_pct",
        "amenity_score",
        "value_score",
        "final_score",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    amenity_weights = getattr(inputs, "amenity_weights", None) or {}
    amenity_ranking = list(amenity_weights.keys())
    alpha = _resolve_alpha(inputs)

    accessibility_scores = []
    value_scores = []
    overall_scores = []

    for _, row in df.iterrows():
        row_amenity = row.get("amenity_score", np.nan)

        if pd.notna(row_amenity):
            a_score = float(row_amenity)
        else:
            a_score, _ = _amenity_score(
                listing=row,
                amenity_ranking=amenity_ranking,
                scoring_weights=amenity_weights,
            )

        valuation_pct = row.get("valuation_pct", np.nan)

        if pd.isna(valuation_pct):
            asking_price = row.get("asking_price", np.nan)
            predicted_price = row.get("predicted_price", np.nan)

            if pd.notna(asking_price) and pd.notna(predicted_price) and predicted_price != 0:
                valuation_pct = (asking_price - predicted_price) / predicted_price * 100
            else:
                valuation_pct = 0.0

        v_score = _comparison_value_score(-valuation_pct, clip=0.20)
        o_score = round(alpha * a_score + (1 - alpha) * v_score, 4)

        accessibility_scores.append(round(a_score * 100, 1))
        value_scores.append(round(v_score * 100, 1))
        overall_scores.append(round(o_score * 100, 1))

    df["accessibility_score"] = accessibility_scores
    df["value_score"] = value_scores
    df["overall_score"] = overall_scores

    return df


def _format_listing_label(row):
    listing_id = row.get("listing_id", "")
    town = row.get("town", "Unknown")
    flat_type = row.get("flat_type", "Flat")

    base = f"{str(flat_type).title()} at {str(town).title()}"
    return f"{listing_id} · {base}" if listing_id else base


def _comparison_card_title(i, row):
    return f"Flat {chr(65 + i)}"


def _comparison_card_subtitle(row):
    address = str(row.get("address", "")).strip()

    if not address or address.lower() == "nan":
        address = "Address unavailable"

    return address


def _render_empty_compare_state():
    st.components.v1.html(
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
.glow{
  position:absolute;top:38%;left:50%;transform:translate(-50%,-50%);
  width:320px;height:200px;
  background:radial-gradient(ellipse,rgba(255,68,88,0.10) 0%,transparent 65%);
  animation:pulse 4s ease-in-out infinite;pointer-events:none;
}
.ghost{position:absolute;line-height:1;filter:grayscale(0.3);}
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
  <span class="ghost" style="top:8%;left:6%;font-size:2rem;opacity:0.12;animation:drift1 9s ease-in-out infinite;">⚖️</span>
  <span class="ghost" style="top:10%;right:8%;font-size:1.7rem;opacity:0.10;animation:drift2 11s ease-in-out infinite;animation-delay:-3s;">📊</span>
  <span class="ghost" style="top:55%;left:4%;font-size:1.3rem;opacity:0.09;animation:drift3 13s ease-in-out infinite;animation-delay:-5s;">🏠</span>
  <span class="ghost" style="top:58%;right:5%;font-size:1.4rem;opacity:0.09;animation:drift1 10s ease-in-out infinite;animation-delay:-7s;">🔎</span>
  <span class="ghost" style="bottom:10%;left:22%;font-size:1.1rem;opacity:0.08;animation:drift2 14s ease-in-out infinite;animation-delay:-2s;">✨</span>
  <span class="ghost" style="bottom:12%;right:24%;font-size:1.0rem;opacity:0.08;animation:drift3 12s ease-in-out infinite;animation-delay:-9s;">💫</span>

  <div class="centre">
    <div class="hero-wrap">⚖️</div>
    <div class="title">Nothing to compare yet</div>
    <div class="hint">Pick flats from <strong>Saved</strong> to see them side by side here.</div>
    <div class="pill">↙ Head to Saved to choose flats</div>
  </div>
</div>
</body>
</html>""",
        height=350,
        scrolling=False,
    )


# =========================================================
# Render sections
# =========================================================
def _render_listing_score_cards(selected_df):
    st.markdown("### Side-by-Side Listing Comparison")

    max_compare = 5
    selected_df = selected_df.head(max_compare).copy()

    num_cards = len(selected_df)
    cols = st.columns(num_cards)

    for global_idx, (_, row) in enumerate(selected_df.iterrows()):
        lid = row.get("listing_id")
        row_uid = f"{row.get('listing_id', '')}_{row.get('session_id', 'na')}_{global_idx}"

        card_title = _comparison_card_title(global_idx, row)
        card_subtitle = _comparison_card_subtitle(row)

        with cols[global_idx]:
            with st.container(border=True):
                title_col, close_col = st.columns([8, 1])

                with title_col:
                    st.markdown(f"#### {card_title}")
                    st.markdown(
                        f"<div style='font-size:0.82rem;color:#6b7280;line-height:1.55;margin-top:-0.25rem;margin-bottom:0.45rem;word-break:break-word;'>{card_subtitle}</div>",
                        unsafe_allow_html=True,
                    )

                with close_col:
                    if st.button("×", key=f"remove_compare_{row_uid}", help="Remove from comparison"):
                        if str(lid).startswith("HYP-"):
                            st.session_state.custom_compare_rows = [
                                r for r in st.session_state.get("custom_compare_rows", [])
                                if r.get("listing_id") != lid
                            ]
                        else:
                            st.session_state.compare_selected_ids = [
                                x for x in st.session_state.get("compare_selected_ids", [])
                                if x != lid
                            ]
                        st.rerun()

                st.write(f"**Town:** {row.get('town', '—')}")


                st.divider()

                value_score = row.get("value_score", np.nan)
                value_score = 70.0 if pd.isna(value_score) else float(value_score)
                value_score = max(0.0, min(value_score, 100.0))
                st.write(f"**Value-for-money score:** {value_score:.1f}/100")
                st.progress(value_score / 100)

                amenity_score = row.get("accessibility_score", np.nan)
                amenity_score = 70.0 if pd.isna(amenity_score) else float(amenity_score)
                amenity_score = max(0.0, min(amenity_score, 100.0))
                st.write(f"**Amenity score:** {amenity_score:.1f}/100")
                st.progress(amenity_score / 100)

                overall_score = row.get("overall_score", np.nan)
                overall_score = 70.0 if pd.isna(overall_score) else float(overall_score)
                overall_score = max(0.0, min(overall_score, 100.0))
                st.write(f"**Overall score:** {overall_score:.1f}/100")
                st.progress(overall_score / 100)

    st.caption("For price and flat details, refer to the Detailed Breakdown below.")

def _render_metric_bar_chart(selected_df, metric_col, chart_title):
    chart_df = selected_df.copy()
    chart_df[metric_col] = pd.to_numeric(chart_df[metric_col], errors="coerce").fillna(0)
    chart_df["flat_label"] = [_flat_letter_label(i) for i in range(len(chart_df))]

    flat_order = [_flat_letter_label(i) for i in range(len(chart_df))]
    chart_df["score_label"] = chart_df[metric_col].map(lambda x: f"{x:.1f}")

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{metric_col}:Q",
                title="Score",
                scale=alt.Scale(domain=[0, 100])
            ),
            y=alt.Y(
                "flat_label:N",
                sort=flat_order,
                title="Flat"
            ),
            tooltip=[
                alt.Tooltip("flat_label:N", title="Flat"),
                alt.Tooltip("listing_id:N", title="Listing ID"),
                alt.Tooltip("town:N", title="Town"),
                alt.Tooltip("flat_type:N", title="Flat type"),
                alt.Tooltip(f"{metric_col}:Q", title="Score", format=".1f"),
            ],
        )
    )

    text = (
        alt.Chart(chart_df)
        .mark_text(align="left", dx=6)
        .encode(
            x=alt.X(f"{metric_col}:Q"),
            y=alt.Y("flat_label:N", sort=flat_order),
            text=alt.Text("score_label:N"),
        )
    )

    chart = (
        (bars + text)
        .properties(
            height=max(240, 45 * len(chart_df)),
            title=chart_title
        )
    )

    st.altair_chart(chart, use_container_width=True)


def _render_comparison_insights(selected_df):
    flat_map = _get_flat_label_map(selected_df)

    best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
    best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]
    best_overall = selected_df.sort_values("overall_score", ascending=False).iloc[0]

    best_value_label = flat_map.get(best_value["listing_id"], best_value["listing_id"])
    best_access_label = flat_map.get(best_access["listing_id"], best_access["listing_id"])
    best_overall_label = flat_map.get(best_overall["listing_id"], best_overall["listing_id"])

    st.markdown("### Comparison Insights")

    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container(border=True):
            st.markdown("#### 💰 Best value")
            st.write(f"**{best_value_label}** offers the strongest value-for-money among the selected flats.")

            if "asking_price" in best_value and pd.notna(best_value["asking_price"]):
                st.write(f"**Asking price:** {fmt_sgd(best_value['asking_price'])}")

            if "valuation_pct" in best_value and pd.notna(best_value["valuation_pct"]):
                gap = best_value["valuation_pct"]
                if gap < 0:
                    st.write(f"**Fair value gap:** {abs(gap):.1f}% below predicted price")
                else:
                    st.write(f"**Fair value gap:** {gap:.1f}% above predicted price")

    with c2:
        with st.container(border=True):
            st.markdown("#### 🏘️ Best amenities")
            st.write(f"**{best_access_label}** has the strongest amenity score among the selected flats.")
            st.write(
                "This means it performs best on access to the amenities that matter most to the user."
            )

    with c3:
        with st.container(border=True):
            st.markdown("#### ⭐ Best overall")
            st.write(f"**{best_overall_label}** performs best overall across the comparison scoring system.")
            st.write(
                "It offers the strongest balance between amenity access and value-for-money."
            )


def _render_metric_comparison_tabs(selected_df):
    st.markdown("### Score Comparison")

    flat_map = _get_flat_label_map(selected_df)

    tab1, tab2 = st.tabs([
        "💰 Value-for-money",
        "🏘️ Amenity score",
    ])

    with tab1:
        _render_metric_bar_chart(
            selected_df,
            "value_score",
            "Value-for-money comparison across selected flats",
        )
        best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
        best_value_label = flat_map.get(best_value["listing_id"], best_value["listing_id"])
        st.write(
            f"**{best_value_label}** currently has the strongest value-for-money score among the selected flats."
        )

    with tab2:
        _render_metric_bar_chart(
            selected_df,
            "accessibility_score",
            "Amenity score comparison across selected flats",
        )
        best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]
        best_access_label = flat_map.get(best_access["listing_id"], best_access["listing_id"])
        st.write(
            f"**{best_access_label}** currently has the strongest amenity score among the selected flats."
        )


def _render_recommendation_summary(selected_df):
    flat_map = _get_flat_label_map(selected_df)

    best_overall = selected_df.sort_values("overall_score", ascending=False).iloc[0]
    best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
    best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]

    best_overall_label = flat_map.get(best_overall["listing_id"], best_overall["listing_id"])
    best_value_label = flat_map.get(best_value["listing_id"], best_value["listing_id"])
    best_access_label = flat_map.get(best_access["listing_id"], best_access["listing_id"])

    st.markdown("### Recommendation Summary")
    st.write(f"**Recommended all-round option: {best_overall_label}**")
    st.write(
        "This flat performs best overall across amenity access and value-for-money, making it the strongest balanced option among the selected flats."
    )

    st.markdown(
        f"""
- **Best overall score:** {best_overall['overall_score']:.1f}/100  
- **Predicted Price:** {fmt_sgd(best_overall['predicted_price']) if pd.notna(best_overall.get('predicted_price')) else '—'}  
- **Why it stands out:** Stronger overall balance between amenity access and value-for-money.
        """
    )

    st.write(
        f"If affordability is your main concern, **{best_value_label}** may be the better choice. "
        f"If nearby amenities matter most, **{best_access_label}** may be more suitable."
    )


def _render_detailed_breakdown(selected_df):
    st.markdown("### Detailed Breakdown")

    disp = selected_df.copy()
    disp["flat_label"] = [_flat_letter_label(i) for i in range(len(disp))]

    if "asking_price" in disp.columns:
        disp["price"] = disp["asking_price"].map(lambda x: fmt_sgd(x) if pd.notna(x) else "—")
    else:
        disp["price"] = "—"

    amenity_cols = {
        "nearest_mrt_m": "MRT Walk (m)",
        "nearest_hawker_m": "Hawker Walk (m)",
        "nearest_park_m": "Park Walk (m)",
        "nearest_school_m": "School Walk (m)",
    }

    if "floor_area_sqm" in disp.columns:
        disp["floor_area_sqft_display"] = disp["floor_area_sqm"].apply(
            lambda x: f"{_sqm_to_sqft(x):,}" if _sqm_to_sqft(x) is not None else "—"
        )

    display_cols = {
        "flat_label": "Flat",
        "comparison_source": "Source",
        "price": "Price",
        "town": "Town",
        "postal_code": "Postal Code",
        "flat_type": "Flat Type",
        "floor_area_sqft_display": "Floor Area (sqft)",
        "remaining_lease_years": "Remaining Lease (years)",
        "value_score": "Value-for-money",
        "accessibility_score": "Amenity score",
        "overall_score": "Overall Score",
    }

    for raw_col, label in amenity_cols.items():
        if raw_col in disp.columns:
            display_cols[raw_col] = label

    available_cols = [c for c in display_cols if c in disp.columns]
    table_df = disp[available_cols].rename(columns=display_cols)

    st.dataframe(table_df, use_container_width=True, hide_index=True)


def _render_score_interpretation():
    with st.expander("How to interpret these scores"):
        st.markdown(
            """
- **Value-for-money score** reflects how attractive the asking price is relative to the predicted price.
- **Amenity score** reflects how well the flat performs on access to nearby amenities based on the user’s ranked priorities and walking times to those amenities.
- **Overall score** reflects the flat’s overall balance between amenity access and value-for-money, based on the user’s selected preference profile.
            """
        )


# =========================================================
# Main page
# =========================================================
def render_comparison_page(inputs, listings_df: pd.DataFrame):
    top_left, top_right = st.columns([1, 5])

    with top_left:
        if st.button("← Saved", use_container_width=True):
            st.session_state.active_page = "Saved"
            st.rerun()

    with top_right:
        st.markdown("## Comparison tool")

    st.session_state.setdefault("custom_compare_rows", [])

    if listings_df is None:
        listings_df = pd.DataFrame()

    custom_df = pd.DataFrame(st.session_state.get("custom_compare_rows", []))

    if listings_df.empty and custom_df.empty:
        _render_empty_compare_state()
        return

    frames = []

    if not listings_df.empty:
        real_df = listings_df.copy()
        if "comparison_source" not in real_df.columns:
            real_df["comparison_source"] = "Discover"
        else:
            real_df["comparison_source"] = real_df["comparison_source"].fillna("Discover")
        frames.append(real_df)

    if not custom_df.empty:
        frames.append(custom_df.copy())

    selected_df = pd.concat(frames, ignore_index=True)

    if "comparison_source" not in selected_df.columns:
        selected_df["comparison_source"] = "Discover"
    else:
        selected_df["comparison_source"] = selected_df["comparison_source"].fillna("Discover")

    selected_df = selected_df[selected_df["comparison_source"] != "Explore"].copy()
    st.session_state.compare_selected_ids = [
        lid for lid in st.session_state.get("compare_selected_ids", [])
        if lid in set(selected_df.get("listing_id", pd.Series(dtype=str)).astype(str))
    ]

    if selected_df.empty:
        _render_empty_compare_state()
        return

    selected_df = _prepare_comparison_scores(selected_df, inputs)
    selected_df = selected_df.sort_values("overall_score", ascending=False).reset_index(drop=True)

    if len(selected_df) > 5:
        st.info("You selected more than 5 flats. Showing the top 5 flats in the side-by-side comparison.")

    selected_df = selected_df.head(5).copy()

    if len(selected_df) < 2:
        st.warning("Select at least 2 flats for a more meaningful comparison.")

    _render_listing_score_cards(selected_df)
    st.markdown("---")

    _render_comparison_insights(selected_df)
    st.markdown("---")

    _render_metric_comparison_tabs(selected_df)
    st.markdown("---")

    _render_recommendation_summary(selected_df)
    st.markdown("---")

    _render_detailed_breakdown(selected_df)
    st.markdown("---")

    _render_score_interpretation()
