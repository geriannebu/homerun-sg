import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from backend.schemas import inputs
from backend.utils.scoring import compute_listing_scores
from backend.utils.formatters import fmt_sgd
from backend.services.predictor_service import get_prediction_bundle
from backend.schemas.inputs import UserInputs


# =========================================================
# Helpers
# =========================================================
def _safe_numeric(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _minmax_score(series, higher_is_better=True, neutral=70.0):
    s = pd.to_numeric(series, errors="coerce")
    if s.isna().all():
        return pd.Series([neutral] * len(series), index=series.index)

    s_min, s_max = s.min(), s.max()
    if pd.isna(s_min) or pd.isna(s_max) or s_min == s_max:
        return pd.Series([neutral] * len(series), index=series.index)

    scaled = (s - s_min) / (s_max - s_min) * 100
    return scaled if higher_is_better else (100 - scaled)


def _extract_room_num(flat_type):
    if not isinstance(flat_type, str):
        return None
    digits = "".join(ch for ch in flat_type if ch.isdigit())
    return int(digits) if digits else None


def _type_fit_score(target_type, candidate_type):
    if not target_type or not candidate_type:
        return 70.0
    if target_type == candidate_type:
        return 100.0

    t = _extract_room_num(target_type)
    c = _extract_room_num(candidate_type)
    if t is None or c is None:
        return 60.0

    diff = abs(t - c)
    if diff == 1:
        return 75.0
    if diff == 2:
        return 55.0
    return 35.0


def _budget_fit_score(asking_price, budget):
    if budget is None or budget <= 0 or pd.isna(asking_price):
        return 70.0

    gap_pct = (asking_price - budget) / budget * 100

    if gap_pct <= 0:
        return max(70.0, 100 - abs(gap_pct) * 1.5)
    return max(0.0, 100 - gap_pct * 6)


def _size_fit_score(area, target_area):
    if pd.isna(area) or target_area is None or target_area <= 0:
        return 70.0
    diff_pct = abs(area - target_area) / target_area * 100
    return max(0.0, 100 - diff_pct * 2.5)


def _lease_fit_score(lease_year, target_lease_year):
    if pd.isna(lease_year) or target_lease_year is None:
        return 70.0
    diff = abs(float(lease_year) - float(target_lease_year))
    return max(0.0, 100 - diff * 3)


def _town_fit_score(selected_town, candidate_town, fallback=70.0):
    if not selected_town or selected_town == "Recommendation mode":
        return fallback
    if not candidate_town:
        return 60.0
    return 100.0 if str(selected_town).strip().lower() == str(candidate_town).strip().lower() else 45.0


def _compute_accessibility_score(df, amenity_weights):
    col_map = {
        "mrt_stations": ["mrt_score", "mrt_access_score", "nearest_mrt_m"],
        "bus_stops": ["bus_score", "bus_access_score", "nearest_bus_stop_m"],
        "schools": ["school_score", "school_access_score", "nearest_school_m"],
        "hawker_centres": ["hawker_score", "hawker_access_score", "nearest_hawker_m"],
        "shopping_malls": ["mall_score", "shopping_score", "nearest_mall_m"],
        "hospitals_polyclinics": ["health_score", "hospital_score", "nearest_hospital_m"],
    }

    weighted_parts = []
    total_weight = 0
    amenity_weights = amenity_weights or {}

    for amenity, weight in amenity_weights.items():
        if weight is None:
            continue

        matched_col = None
        for c in col_map.get(amenity, []):
            if c in df.columns:
                matched_col = c
                break

        if matched_col is None:
            continue

        vals = _safe_numeric(df[matched_col], np.nan)

        if matched_col.endswith("_m"):
            amenity_score = _minmax_score(vals, higher_is_better=False)
        else:
            max_val = vals.max()
            if pd.notna(max_val) and max_val <= 100:
                amenity_score = vals.fillna(70)
            else:
                amenity_score = _minmax_score(vals, higher_is_better=True)

        weighted_parts.append(amenity_score * float(weight))
        total_weight += float(weight)

    if weighted_parts and total_weight > 0:
        return (sum(weighted_parts) / total_weight).round(1)

    if "score" in df.columns:
        score_vals = _safe_numeric(df["score"], 70.0)
        max_val = score_vals.max()
        if pd.notna(max_val) and max_val <= 100:
            return score_vals.round(1)
        return _minmax_score(score_vals, higher_is_better=True).round(1)

    return pd.Series([70.0] * len(df), index=df.index)


def _prepare_comparison_scores(df, inputs):
    df = df.copy()

    for col in [
        "asking_price",
        "predicted_price",
        "recent_median_transacted",
        "floor_area_sqm",
        "lease_commence_year",
        "asking_vs_predicted_pct",
        "score",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "asking_vs_predicted_pct" not in df.columns and {"asking_price", "predicted_price"}.issubset(df.columns):
        df["asking_vs_predicted_pct"] = (
            (df["asking_price"] - df["predicted_price"]) / df["predicted_price"] * 100
        )

    if "asking_vs_predicted_pct" in df.columns:
        df["value_score"] = _minmax_score(df["asking_vs_predicted_pct"], higher_is_better=False).round(1)
    else:
        df["value_score"] = 70.0

    df["accessibility_score"] = _compute_accessibility_score(df, inputs.amenity_weights)

    if "asking_price" in df.columns:
        budget_fit = df["asking_price"].apply(lambda x: _budget_fit_score(x, inputs.budget))
    else:
        budget_fit = pd.Series([70.0] * len(df), index=df.index)

    if "floor_area_sqm" in df.columns:
        size_fit = df["floor_area_sqm"].apply(lambda x: _size_fit_score(x, inputs.floor_area_sqm))
    else:
        size_fit = pd.Series([70.0] * len(df), index=df.index)

    if "flat_type" in df.columns:
        type_fit = df["flat_type"].apply(lambda x: _type_fit_score(inputs.flat_type, x))
    else:
        type_fit = pd.Series([70.0] * len(df), index=df.index)

    if "lease_commence_year" in df.columns:
        lease_fit = df["lease_commence_year"].apply(lambda x: _lease_fit_score(x, inputs.lease_commence_year))
    else:
        lease_fit = pd.Series([70.0] * len(df), index=df.index)

    if "town" in df.columns:
        fallback = df["score"] if "score" in df.columns else pd.Series([70.0] * len(df), index=df.index)
        fallback = pd.to_numeric(fallback, errors="coerce").fillna(70.0)

        df["town_fit_score"] = [
            _town_fit_score(inputs.town, town, fallback=float(fallback.iloc[i]))
            for i, town in enumerate(df["town"])
        ]
    else:
        df["town_fit_score"] = 70.0

    df["fit_score"] = (
        0.35 * budget_fit
        + 0.20 * size_fit
        + 0.15 * type_fit
        + 0.10 * lease_fit
        + 0.20 * df["town_fit_score"]
    ).round(1)

    df["overall_score"] = (
        0.35 * df["value_score"]
        + 0.25 * df["accessibility_score"]
        + 0.40 * df["fit_score"]
    ).round(1)

    df["value_score"] = pd.to_numeric(df["value_score"], errors="coerce").fillna(70.0)
    df["accessibility_score"] = pd.to_numeric(df["accessibility_score"], errors="coerce").fillna(70.0)
    df["fit_score"] = pd.to_numeric(df["fit_score"], errors="coerce").fillna(70.0)
    df["overall_score"] = pd.to_numeric(df["overall_score"], errors="coerce").fillna(70.0)

    return df


def _format_listing_label(row):
    listing_id = row.get("listing_id", "")
    town = row.get("town", "Unknown")
    flat_type = row.get("flat_type", "Flat")

    base = f"{str(flat_type).title()} at {str(town).title()}"
    return f"{listing_id} · {base}" if listing_id else base

# =========================================================
# Styling
# =========================================================
def _render_card_styles():
    st.markdown(
        """
        <style>
        .nw-card {
            background: white;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 20px;
            padding: 1.2rem 1.2rem 1rem 1.2rem;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            min-height: 560px;
            margin-bottom: 1rem;
        }

        .nw-card h4 {
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            line-height: 1.3;
            color: #0f172a;
        }

        .nw-card-row {
            margin-bottom: 0.65rem;
            color: #334155;
            font-size: 0.98rem;
        }

        .nw-card-label {
            font-weight: 700;
            color: #1e293b;
        }

        .nw-card-divider {
            border-top: 1px solid rgba(15, 23, 42, 0.08);
            margin: 1rem 0 0.9rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# Postal sector mapping (first 2 digits of SG postal code)
# Values are lists so we can show a selectbox when a sector
# maps to multiple possible towns / areas.
# =========================================================
SECTOR_TO_TOWNS = {
    "01": ["Raffles Place", "Marina", "People's Park"],
    "02": ["Raffles Place", "Marina", "People's Park"],
    "03": ["Raffles Place", "Marina", "People's Park"],
    "04": ["Raffles Place", "Marina", "People's Park"],
    "05": ["Raffles Place", "Marina", "People's Park"],
    "06": ["Raffles Place", "Marina", "People's Park"],
    "07": ["Tanjong Pagar", "Anson"],
    "08": ["Tanjong Pagar", "Anson"],
    "09": ["Telok Blangah", "Harbourfront"],
    "10": ["Telok Blangah", "Harbourfront"],
    "11": ["Pasir Panjang", "Clementi"],
    "12": ["Pasir Panjang", "Clementi"],
    "13": ["Pasir Panjang", "Clementi"],
    "14": ["Queenstown", "Tiong Bahru"],
    "15": ["Queenstown", "Tiong Bahru"],
    "16": ["Queenstown", "Tiong Bahru"],
    "17": ["Beach Road", "High Street"],
    "18": ["Middle Road", "Golden Mile"],
    "19": ["Middle Road", "Golden Mile"],
    "20": ["Little India"],
    "21": ["Little India"],
    "22": ["Orchard", "River Valley"],
    "23": ["Orchard", "River Valley"],
    "24": ["Bukit Timah", "Tanglin"],
    "25": ["Bukit Timah", "Tanglin"],
    "26": ["Bukit Timah", "Tanglin"],
    "27": ["Bukit Timah", "Tanglin"],
    "28": ["Novena", "Thomson"],
    "29": ["Novena", "Thomson"],
    "30": ["Novena", "Thomson"],
    "31": ["Balestier", "Toa Payoh", "Serangoon"],
    "32": ["Balestier", "Toa Payoh", "Serangoon"],
    "33": ["Balestier", "Toa Payoh", "Serangoon"],
    "34": ["Macpherson", "Braddell"],
    "35": ["Macpherson", "Braddell"],
    "36": ["Macpherson", "Braddell"],
    "37": ["Macpherson", "Braddell"],
    "38": ["Geylang", "Eunos"],
    "39": ["Geylang", "Eunos"],
    "40": ["Geylang", "Eunos"],
    "41": ["Geylang", "Eunos"],
    "42": ["Katong", "Joo Chiat"],
    "43": ["Katong", "Joo Chiat"],
    "44": ["Katong", "Joo Chiat"],
    "45": ["Katong", "Joo Chiat"],
    "46": ["Bedok", "Upper East Coast"],
    "47": ["Bedok", "Upper East Coast"],
    "48": ["Bedok", "Upper East Coast"],
    "49": ["Loyang", "Changi"],
    "50": ["Loyang", "Changi"],
    "51": ["Tampines", "Pasir Ris"],
    "52": ["Tampines", "Pasir Ris"],
    "53": ["Hougang", "Punggol", "Serangoon Garden"],
    "54": ["Hougang", "Punggol", "Serangoon Garden"],
    "55": ["Hougang", "Punggol", "Serangoon Garden"],
    "56": ["Bishan", "Ang Mo Kio"],
    "57": ["Bishan", "Ang Mo Kio"],
    "58": ["Upper Bukit Timah", "Clementi Park", "Ulu Pandan"],
    "59": ["Upper Bukit Timah", "Clementi Park", "Ulu Pandan"],
    "60": ["Jurong"],
    "61": ["Jurong"],
    "62": ["Jurong"],
    "63": ["Jurong"],
    "64": ["Jurong"],
    "65": ["Hillview", "Dairy Farm", "Bukit Panjang", "Choa Chu Kang"],
    "66": ["Hillview", "Dairy Farm", "Bukit Panjang", "Choa Chu Kang"],
    "67": ["Hillview", "Dairy Farm", "Bukit Panjang", "Choa Chu Kang"],
    "68": ["Hillview", "Dairy Farm", "Bukit Panjang", "Choa Chu Kang"],
    "69": ["Lim Chu Kang", "Tengah"],
    "70": ["Lim Chu Kang", "Tengah"],
    "71": ["Lim Chu Kang", "Tengah"],
    "72": ["Kranji", "Woodgrove"],
    "73": ["Kranji", "Woodgrove"],
    "75": ["Yishun", "Sembawang"],
    "76": ["Yishun", "Sembawang"],
    "77": ["Upper Thomson", "Springleaf"],
    "78": ["Upper Thomson", "Springleaf"],
    "79": ["Seletar"],
    "80": ["Seletar"],
    "81": ["Loyang", "Changi"],
    "82": ["Hougang", "Punggol", "Serangoon Garden"],
}



# =========================================================
# Render sections
# =========================================================
def _render_summary_cards(selected_df):
    best_overall = selected_df.sort_values("overall_score", ascending=False).iloc[0]
    best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
    best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]
    best_fit = selected_df.sort_values("fit_score", ascending=False).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Best overall", best_overall["listing_id"], f"{best_overall['overall_score']:.1f}/100")
    c2.metric("Best value", best_value["listing_id"], f"{best_value['value_score']:.1f}/100")
    c3.metric("Best accessibility", best_access["listing_id"], f"{best_access['accessibility_score']:.1f}/100")
    c4.metric("Best fit", best_fit["listing_id"], f"{best_fit['fit_score']:.1f}/100")

    st.info(
        f"{best_overall['listing_id']} is the strongest overall option among your saved flats. "
        f"{best_value['listing_id']} offers the best value-for-money, "
        f"{best_access['listing_id']} leads on accessibility, "
        f"and {best_fit['listing_id']} best matches your search profile."
    )

def _source_legend_label(row):
    source = row.get("comparison_source", "Saved flat")
    flat_type = row.get("flat_type", "Flat")
    town = row.get("town", "Unknown")
    return f"{source} ({flat_type} at {town})"

def _render_listing_score_cards(selected_df):
    st.markdown("### Side-by-Side Listing Comparison")

    cols = st.columns(len(selected_df))

    for i, (_, row) in enumerate(selected_df.iterrows()):
        lid = row.get("listing_id")
        row_uid = f"{row.get('listing_id', '')}_{row.get('session_id', 'na')}_{i}"

        with cols[i]:
            with st.container(border=True):
                title_col, close_col = st.columns([8, 0.9])

                with title_col:
                    st.markdown(f"#### {row.get('listing_id', '')}")
                    st.caption(f"{str(row.get('flat_type', 'Flat')).title()} at {str(row.get('town', 'Unknown')).title()}")

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
                    source = row.get("comparison_source", "Saved flat")
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

                fit_score = row.get("fit_score", np.nan)
                fit_score = 70.0 if pd.isna(fit_score) else float(fit_score)
                fit_score = max(0.0, min(fit_score, 100.0))
                st.write(f"**Fit score:** {fit_score:.0f}/100")
                st.progress(fit_score / 100)

                if fit_score == float(selected_df["fit_score"].max()):
                    st.caption("Best match to the stated user preferences")
                elif fit_score >= float(selected_df["fit_score"].median()):
                    st.caption("Generally aligns well with the user's priorities")
                else:
                    st.caption("Suitable, but less aligned with the user's preferred balance of factors")

def _render_metric_bar_chart(selected_df, metric_col, chart_title):
    chart_df = selected_df.copy()
    chart_df[metric_col] = pd.to_numeric(chart_df[metric_col], errors="coerce").fillna(0)
    chart_df["legend_label"] = chart_df.apply(_source_legend_label, axis=1)

    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{metric_col}:Q", title="Score", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("listing_id:N", sort="-x", title="Listing ID"),
            color=alt.Color("legend_label:N", title="Listing type"),
            tooltip=[
                alt.Tooltip("listing_id:N", title="Listing ID"),
                alt.Tooltip("legend_label:N", title="Legend"),
                alt.Tooltip("town:N", title="Town"),
                alt.Tooltip("flat_type:N", title="Flat type"),
                alt.Tooltip(f"{metric_col}:Q", title="Score", format=".1f"),
            ],
        )
        .properties(height=max(240, 45 * len(chart_df)), title=chart_title)
    )

    st.altair_chart(chart, use_container_width=True)


def _render_metric_comparison_tabs(selected_df):
    st.markdown("### Score Comparison")

    tab1, tab2, tab3 = st.tabs([
        "💰 Value-for-money",
        "🚆 Accessibility",
        "🎯 Fit",
    ])

    with tab1:
        _render_metric_bar_chart(
            selected_df,
            "value_score",
            "Value-for-money comparison across selected flats",
        )
        best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
        st.write(
            f"**{best_value['listing_id']}** currently has the strongest value-for-money score among the selected flats."
        )

    with tab2:
        _render_metric_bar_chart(
            selected_df,
            "accessibility_score",
            "Accessibility comparison across selected flats",
        )
        best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]
        st.write(
            f"**{best_access['listing_id']}** currently has the strongest accessibility score among the selected flats."
        )

    with tab3:
        _render_metric_bar_chart(
            selected_df,
            "fit_score",
            "Fit comparison across selected flats",
        )
        best_fit = selected_df.sort_values("fit_score", ascending=False).iloc[0]
        st.write(
            f"**{best_fit['listing_id']}** currently has the strongest fit score among the selected flats."
        )

def _render_comparison_insights(selected_df):
    best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
    best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]
    best_fit = selected_df.sort_values("fit_score", ascending=False).iloc[0]

    left, right = st.columns(2)

    with left:
        st.markdown("### Comparison Insights")
        st.markdown("#### Value-for-Money Comparison")
        st.write(
            f"**{_format_listing_label(best_value)} ({best_value['listing_id']})** appears to offer the best value for money among the selected options."
        )
        if "asking_price" in best_value and pd.notna(best_value["asking_price"]):
            st.write(f"It has an asking price of **{fmt_sgd(best_value['asking_price'])}**.")
        if "asking_vs_predicted_pct" in best_value and pd.notna(best_value["asking_vs_predicted_pct"]):
            gap = best_value["asking_vs_predicted_pct"]
            if gap < 0:
                st.write(f"This is **{abs(gap):.1f}% below** the modelled fair value.")
            else:
                st.write(f"This is **{gap:.1f}% above** the modelled fair value.")

        st.markdown("#### Accessibility Comparison")
        st.write(
            f"**{_format_listing_label(best_access)} ({best_access['listing_id']})** provides the strongest accessibility, making it the most convenient option for day-to-day travel and nearby amenities."
        )

    with right:
        st.markdown("### ")
        st.markdown("#### Fit Comparison")
        st.write(
            f"**{_format_listing_label(best_fit)} ({best_fit['listing_id']})** is the strongest match to the user's stated priorities, based on its balance of affordability, convenience, and flat characteristics."
        )

        st.markdown("#### Trade-off Summary")
        st.write(
            f"While **{best_value['listing_id']}** performs best on value-for-money, "
            f"**{best_access['listing_id']}** is strongest on accessibility, "
            f"and **{best_fit['listing_id']}** leads on overall fit."
        )


def _render_detailed_breakdown(selected_df):
    st.markdown("### Detailed Breakdown")

    disp = selected_df.copy()
    disp["listing"] = disp.apply(_format_listing_label, axis=1)

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
        "listing_id": "Listing ID",
        "listing": "Listing",
        "comparison_source": "Source",
        "price": "Price",
        "town": "Town",
        "postal_code": "Postal Code",
        "flat_type": "Flat Type",
        "floor_area_sqm": "Floor Area (sqm)",
        "remaining_lease_years": "Remaining Lease (years)",
        "value_score": "Value-for-money",
        "accessibility_score": "Accessibility",
        "fit_score": "Fit",
        "overall_score": "Overall Average Score",
    }

    for raw_col, label in amenity_cols.items():
        if raw_col in disp.columns:
            display_cols[raw_col] = label

    available_cols = [c for c in display_cols if c in disp.columns]
    table_df = disp[available_cols].rename(columns=display_cols)

    st.dataframe(table_df, use_container_width=True, hide_index=True)


def _render_recommendation_summary(selected_df):
    best_overall = selected_df.sort_values("overall_score", ascending=False).iloc[0]

    st.markdown("### Recommendation Summary")
    st.write(f"**Recommended all-round option: {_format_listing_label(best_overall)} ({best_overall['listing_id']})**")
    st.write(
        "This listing performs best overall across value-for-money, accessibility, and fit, making it the strongest balanced choice among the selected flats."
    )

    st.markdown(
        f"""
- **Best overall score:** {best_overall['overall_score']:.1f}/100  
- **Predicted Price:** {fmt_sgd(best_overall['predicted_price']) if pd.notna(best_overall.get('predicted_price')) else '—'}  
- **Why it stands out:** Stronger balance across the three comparison dimensions.
        """
    )

    best_value = selected_df.sort_values("value_score", ascending=False).iloc[0]
    best_access = selected_df.sort_values("accessibility_score", ascending=False).iloc[0]

    st.write(
        f"If affordability is your main concern, **{best_value['listing_id']}** may be the better choice. "
        f"If daily convenience matters most, **{best_access['listing_id']}** may be more suitable."
    )


def _render_score_interpretation():
    with st.expander("How to interpret these scores"):
        st.markdown(
            """
- **Value-for-money score** reflects how attractive the asking price is relative to modelled fair value.
- **Accessibility score** reflects proximity to amenities such as transport, schools, and other daily needs.
- **Fit score** reflects how well the listing matches the user's stated preferences and priorities.
- **Overall average score** gives a simple summary of performance across all three dimensions.
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
        st.info("No flats selected yet. Go to Saved to pick flats, or add a hypothetical flat above.")
        return

    frames = []

    if not listings_df.empty:
        real_df = listings_df.copy()
        if "comparison_source" not in real_df.columns:
            real_df["comparison_source"] = "Saved flat"
        else:
            real_df["comparison_source"] = real_df["comparison_source"].fillna("Saved flat")
        frames.append(real_df)

    if not custom_df.empty:
        frames.append(custom_df.copy())

    selected_df = pd.concat(frames, ignore_index=True)
    selected_df = _prepare_comparison_scores(selected_df, inputs)

    if "comparison_source" not in selected_df.columns:
        selected_df["comparison_source"] = "Saved flat"
    else:
        selected_df["comparison_source"] = selected_df["comparison_source"].fillna("Saved flat")

    selected_df = selected_df.sort_values("overall_score", ascending=False).reset_index(drop=True)

    if len(selected_df) < 2:
        st.warning("Select at least 2 flats for a more meaningful comparison.")

    _render_summary_cards(selected_df)
    st.markdown("---")

    _render_listing_score_cards(selected_df)
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