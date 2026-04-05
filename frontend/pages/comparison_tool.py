import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from backend.schemas.inputs import UserInputs
from backend.utils.formatters import fmt_sgd
from backend.services.recommender import _amenity_score, _value_score, RANKING_ALPHA


# =========================================================
# Helpers
# =========================================================
def _safe_numeric(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


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

    for col in ["asking_price", "predicted_price", "valuation_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    amenity_weights = getattr(inputs, "amenity_weights", None) or {}
    amenity_ranking = list(amenity_weights.keys())
    alpha = _resolve_alpha(inputs)

    accessibility_scores = []
    value_scores = []
    overall_scores = []

    for _, row in df.iterrows():
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

        # Relaxed clipping for comparison tool only
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




# =========================================================
# Render sections
# =========================================================
def _render_summary_cards(selected_df):
    flat_map = _get_flat_label_map(selected_df)

    best_overall = selected_df.sort_values("overall_score", ascending=False).iloc[0]
    best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
    best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]

    best_overall_label = flat_map.get(best_overall["listing_id"], best_overall["listing_id"])
    best_value_label = flat_map.get(best_value["listing_id"], best_value["listing_id"])
    best_access_label = flat_map.get(best_access["listing_id"], best_access["listing_id"])

    st.markdown("### Summary of results")

    c1, c2, c3 = st.columns(3)
    c1.metric("Best overall", best_overall_label, f"{best_overall['overall_score']:.1f}/100")
    c2.metric("Best value", best_value_label, f"{best_value['value_score']:.1f}/100")
    c3.metric("Best accessibility", best_access_label, f"{best_access['accessibility_score']:.1f}/100")

    st.info(
        f"{best_overall_label} is the strongest overall option among your selected flats. "
        f"{best_value_label} offers the best value-for-money, "
        f"and {best_access_label} leads on accessibility."
    )


def _render_listing_score_cards(selected_df):
    st.markdown("### Side-by-Side Listing Comparison")

    cols = st.columns(len(selected_df))

    for i, (_, row) in enumerate(selected_df.iterrows()):
        lid = row.get("listing_id")
        row_uid = f"{row.get('listing_id', '')}_{row.get('session_id', 'na')}_{i}"

        card_title = _comparison_card_title(i, row)
        card_subtitle = _comparison_card_subtitle(row)

        with cols[i]:
            with st.container(border=True):
                title_col, close_col = st.columns([8, 0.9])

                with title_col:
                    st.markdown(f"#### {card_title}")
                    st.markdown(
                        f"<div style='font-size:0.82rem;color:#6b7280;line-height:1.5;margin-top:-0.35rem;margin-bottom:0.35rem;'>{card_subtitle}</div>",
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

                if "postal_code" in row and pd.notna(row.get("postal_code")) and str(row.get("postal_code")).strip():
                    st.write(f"**Postal Code:** {row.get('postal_code')}")

                predicted_price = row.get("predicted_price", np.nan)
                pred_text = fmt_sgd(predicted_price) if pd.notna(predicted_price) else "—"
                st.write(f"**Predicted Price:** {pred_text}")

                asking_price = row.get("asking_price", np.nan)
                ask_text = fmt_sgd(asking_price) if pd.notna(asking_price) else "—"
                st.write(f"**Asking Price:** {ask_text}")

                st.write(f"**Flat Type:** {row.get('flat_type', '—')}")
                st.write(f"**Floor Area:** {row.get('floor_area_sqm', '—')} sqm")

                floor_level = row.get("storey_range", np.nan)
                if pd.notna(floor_level) and str(floor_level).strip() and str(floor_level).lower() != "nan":
                    st.write(f"**Floor Level:** {floor_level}")

                if "remaining_lease_years" in row and pd.notna(row.get("remaining_lease_years")):
                    st.write(f"**Remaining Lease:** {row.get('remaining_lease_years')} years")

                if "comparison_source" in row:
                    source = row.get("comparison_source", "Discover")
                    st.write(f"**Source:** {source}")

                st.divider()

                value_score = row.get("value_score", np.nan)
                value_score = 70.0 if pd.isna(value_score) else float(value_score)
                value_score = max(0.0, min(value_score, 100.0))
                st.write(f"**Value-for-money score:** {value_score:.0f}/100")
                st.progress(value_score / 100)

                if value_score == float(selected_df["value_score"].max()):
                    st.caption("Best value among selected options")
                elif value_score >= float(selected_df["value_score"].median()):
                    st.caption("Reasonably priced with some trade-offs")
                else:
                    st.caption("Priced at a premium relative to comparable options")

                access_score = row.get("accessibility_score", np.nan)
                access_score = 70.0 if pd.isna(access_score) else float(access_score)
                access_score = max(0.0, min(access_score, 100.0))
                st.write(f"**Accessibility score:** {access_score:.0f}/100")
                st.progress(access_score / 100)

                if access_score == float(selected_df["accessibility_score"].max()):
                    st.caption("Strongest accessibility among selected flats")
                elif access_score >= float(selected_df["accessibility_score"].median()):
                    st.caption("Good day-to-day convenience for key amenities")
                else:
                    st.caption("More limited convenience for daily amenities")

                overall_score = row.get("overall_score", np.nan)
                overall_score = 70.0 if pd.isna(overall_score) else float(overall_score)
                overall_score = max(0.0, min(overall_score, 100.0))
                st.write(f"**Overall score:** {overall_score:.0f}/100")
                st.progress(overall_score / 100)

                if overall_score == float(selected_df["overall_score"].max()):
                    st.caption("Strongest overall balance of value and accessibility")
                elif overall_score >= float(selected_df["overall_score"].median()):
                    st.caption("Performs well overall across the backend scoring criteria")
                else:
                    st.caption("Less competitive overall relative to the selected options")


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


def _render_metric_comparison_tabs(selected_df):
    st.markdown("### Score Comparison")

    flat_map = _get_flat_label_map(selected_df)

    tab1, tab2 = st.tabs([
        "💰 Value-for-money",
        "🚆 Accessibility",
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
            "Accessibility comparison across selected flats",
        )
        best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]
        best_access_label = flat_map.get(best_access["listing_id"], best_access["listing_id"])
        st.write(
            f"**{best_access_label}** currently has the strongest accessibility score among the selected flats."
        )


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
                    st.write(f"**Fair value gap:** {abs(gap):.1f}% below modelled fair value")
                else:
                    st.write(f"**Fair value gap:** {gap:.1f}% above modelled fair value")

    with c2:
        with st.container(border=True):
            st.markdown("#### 🚆 Best accessibility")
            st.write(f"**{best_access_label}** has the strongest accessibility score among the selected flats.")
            st.write(
                "This means it performs best on proximity to the amenities that matter most to the user."
            )

    with c3:
        with st.container(border=True):
            st.markdown("#### ⭐ Best overall")
            st.write(f"**{best_overall_label}** performs best overall across the comparison scoring system.")
            st.write(
                "It gives the strongest balance between value-for-money and accessibility."
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

    display_cols = {
        "flat_label": "Flat",
        "comparison_source": "Source",
        "price": "Price",
        "town": "Town",
        "postal_code": "Postal Code",
        "flat_type": "Flat Type",
        "floor_area_sqm": "Floor Area (sqm)",
        "remaining_lease_years": "Remaining Lease (years)",
        "value_score": "Value-for-money",
        "accessibility_score": "Accessibility",
        "overall_score": "Overall Score",
    }

    for raw_col, label in amenity_cols.items():
        if raw_col in disp.columns:
            display_cols[raw_col] = label

    available_cols = [c for c in display_cols if c in disp.columns]
    table_df = disp[available_cols].rename(columns=display_cols)

    st.dataframe(table_df, use_container_width=True, hide_index=True)


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
        "This listing performs best overall across value-for-money and accessibility, using the same backend scoring logic as the recommender."
    )

    st.markdown(
        f"""
- **Best overall score:** {best_overall['overall_score']:.1f}/100  
- **Predicted Price:** {fmt_sgd(best_overall['predicted_price']) if pd.notna(best_overall.get('predicted_price')) else '—'}  
- **Why it stands out:** Stronger overall balance between accessibility and value-for-money.
        """
    )

    st.write(
        f"If affordability is your main concern, **{best_value_label}** may be the better choice. "
        f"If daily convenience matters most, **{best_access_label}** may be more suitable."
    )


def _render_score_interpretation():
    with st.expander("How to interpret these scores"):
        st.markdown(
            """
- **Value-for-money score** reflects how attractive the asking price is relative to modelled fair value.
- **Accessibility score** reflects proximity to amenities such as transport, schools, and other daily needs, weighted by the user’s amenity priorities.
- **Overall score** reflects the backend recommender trade-off between accessibility and value-for-money based on the user's preferrences.
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
        st.info("No flats selected yet. Go to Saved to pick flats.")
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

    selected_df = _prepare_comparison_scores(selected_df, inputs)
    selected_df = selected_df.sort_values("overall_score", ascending=False).reset_index(drop=True)

    if len(selected_df) < 2:
        st.warning("Select at least 2 flats for a more meaningful comparison.")

    _render_listing_score_cards(selected_df)
    st.markdown("---")

    _render_summary_cards(selected_df)
    st.markdown("---")

    _render_metric_comparison_tabs(selected_df)
    st.markdown("---")

    _render_comparison_insights(selected_df)
    st.markdown("---")

    _render_detailed_breakdown(selected_df)
    st.markdown("---")

    _render_recommendation_summary(selected_df)
    st.markdown("---")

    _render_score_interpretation()