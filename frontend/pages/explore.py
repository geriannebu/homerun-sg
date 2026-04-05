import copy
import numpy as np
import pandas as pd
import streamlit as st

from backend.utils.formatters import fmt_sgd, valuation_tag_html
from backend.utils.scoring import compute_listing_scores
from frontend.components.listing_detail import show_listing_detail


def _safe_str(x):
    return "" if pd.isna(x) else str(x)


def _compute_median_from_filtered_rows(df: pd.DataFrame):
    if df is None or df.empty:
        return np.nan

    price_cols = [
        "resale_price",
        "transacted_price",
        "price",
        "recent_price",
        "median_price",
        "asking_price",
        "median_similar",
        "median_6m_similar",
    ]

    for col in price_cols:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if not vals.empty:
                return float(vals.median())

    return np.nan


def _get_active_session_obj():
    active_session_id = st.session_state.get("active_session_id")
    for s in st.session_state.get("search_sessions", []):
        if s.get("session_id") == active_session_id:
            return s
    return None


def _save_extra_row(row_dict: dict):
    session = _get_active_session_obj()
    if session is None:
        st.warning("No active session found.")
        return False

    session.setdefault("extra_saved_rows", [])

    listing_id = str(row_dict.get("listing_id", "")).strip()
    address = str(row_dict.get("address", "")).strip().lower()

    liked_ids = [str(x).strip() for x in session.get("liked_ids", [])]
    if listing_id and listing_id in liked_ids:
        st.info("This flat is already saved.")
        return False

    for existing in session["extra_saved_rows"]:
        ex_id = str(existing.get("listing_id", "")).strip()
        ex_addr = str(existing.get("address", "")).strip().lower()

        if listing_id and ex_id == listing_id:
            st.info("This flat is already saved.")
            return False

        if address and ex_addr == address:
            st.info("This flat is already saved.")
            return False

    row_dict["session_id"] = session.get("session_id", "na")
    session["extra_saved_rows"].append(copy.deepcopy(row_dict))
    return True


def _is_row_already_saved(row_dict: dict) -> bool:
    session = _get_active_session_obj()
    if session is None:
        return False

    listing_id = str(row_dict.get("listing_id", "")).strip()
    address = str(row_dict.get("address", "")).strip().lower()

    liked_ids = [str(x).strip() for x in session.get("liked_ids", [])]
    if listing_id and listing_id in liked_ids:
        return True

    for existing in session.get("extra_saved_rows", []):
        ex_id = str(existing.get("listing_id", "")).strip()
        ex_addr = str(existing.get("address", "")).strip().lower()

        if listing_id and ex_id == listing_id:
            return True
        if address and ex_addr == address:
            return True

    return False


def _render_flat_snapshot(row: pd.Series):
    address = row.get("address", row.get("listing_id", "Selected flat"))
    predicted_price = row.get("predicted_price", np.nan)
    predicted_low = row.get("predicted_price_lower", np.nan)
    predicted_high = row.get("predicted_price_upper", np.nan)
    valuation_label = row.get("valuation_label", "")
    asking_vs_predicted_pct = row.get("asking_vs_predicted_pct", np.nan)

    if pd.isna(asking_vs_predicted_pct):
        asking_vs_predicted_pct = row.get("valuation_pct", np.nan)

    flat_type = _safe_str(row.get("flat_type", "—"))
    area = row.get("floor_area_sqm", np.nan)
    storey = row.get("storey_range", np.nan)

    meta_parts = [flat_type]
    if pd.notna(area):
        meta_parts.append(f"{float(area):.1f} sqm")
    if pd.notna(storey) and str(storey).strip() and str(storey).lower() != "nan":
        meta_parts.append(f"Storey {storey}")

    meta_text = " · ".join(meta_parts)

    tag_html = valuation_tag_html(valuation_label) if valuation_label else ""
    diff_text = f"{asking_vs_predicted_pct:+.1f}% vs model" if pd.notna(asking_vs_predicted_pct) else ""

    diff_html = ""
    if diff_text:
        diff_html = f"<span style='font-size:0.76rem;color:#9ca3af;'>{diff_text}</span>"

    range_html = ""
    if pd.notna(predicted_low) and pd.notna(predicted_high):
        range_html = (
            f"<div style='font-size:0.78rem;color:#6b7280;margin-top:4px;'>"
            f"95% range: {fmt_sgd(predicted_low)} to {fmt_sgd(predicted_high)}"
            f"</div>"
        )

    card_html = (
        f"<div style='border:1px solid #e4e7ed;background:rgba(255,255,255,0.96);"
        f"border-radius:16px;padding:16px;margin-bottom:10px;box-shadow:0 2px 10px rgba(0,0,0,0.04);'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:16px;'>"
                f"<div style='min-width:0;flex:1;'>"
                    f"<div style='font-size:1rem;font-weight:800;color:#0f172a;line-height:1.35;'>"
                        f"{address}"
                    f"</div>"
                    f"<div style='font-size:0.82rem;color:#6b7280;margin-top:4px;'>"
                        f"{meta_text}"
                    f"</div>"
                f"</div>"
                f"<div style='text-align:right;flex-shrink:0;'>"
                    f"<div style='font-size:1.1rem;font-weight:800;color:#0f172a;'>"
                        f"{fmt_sgd(predicted_price) if pd.notna(predicted_price) else '—'}"
                    f"</div>"
                    f"<div style='font-size:0.82rem;color:#6b7280;margin-top:4px;'>"
                        f"Predicted price"
                    f"</div>"
                    f"{range_html}"
                f"</div>"
            f"</div>"
            f"<div style='display:flex;align-items:center;gap:8px;margin-top:10px;flex-wrap:wrap;'>"
                f"{tag_html}"
                f"{diff_html}"
            f"</div>"
        f"</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)


def _enrich_explore_row(row_dict: dict, inputs):
    one_row_df = pd.DataFrame([row_dict])

    try:
        scored_df = compute_listing_scores(
            listings_df=one_row_df,
            budget=getattr(inputs, "budget", None) if inputs is not None else None,
            amenity_weights=getattr(inputs, "amenity_weights", {}) if inputs is not None else {},
            ranking_profile=getattr(inputs, "ranking_profile", "balanced") if inputs is not None else "balanced",
        )
        return scored_df.iloc[0].to_dict()
    except Exception:
        return row_dict


def _render_custom_flat_median(inputs, listings_df: pd.DataFrame):
    st.markdown("### Check custom flat median")
    st.caption(
        "Optionally adjust any of the fields below to estimate the recent median for similar flats."
    )

    room_options = ["Any", "1 ROOM", "2 ROOM", "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE", "MULTI-GENERATION"]

    town_options = [
        "Any",
        "ANG MO KIO", "BEDOK", "BISHAN", "BUKIT BATOK", "BUKIT MERAH",
        "BUKIT PANJANG", "BUKIT TIMAH", "CENTRAL AREA", "CHOA CHU KANG",
        "CLEMENTI", "GEYLANG", "HOUGANG", "JURONG EAST", "JURONG WEST",
        "KALLANG/WHAMPOA", "MARINE PARADE", "PASIR RIS", "PUNGGOL",
        "QUEENSTOWN", "SEMBAWANG", "SENGKANG", "SERANGOON", "TAMPINES",
        "TOA PAYOH", "WOODLANDS", "YISHUN"
    ]

    inputs_town = getattr(inputs, "town", None) if inputs is not None else None
    inputs_flat_type = getattr(inputs, "flat_type", None) if inputs is not None else None
    inputs_floor_area = getattr(inputs, "floor_area_sqm", None) if inputs is not None else None
    inputs_lease = getattr(inputs, "remaining_lease_years", None) if inputs is not None else None

    default_town = (
        str(inputs_town).upper()
        if inputs_town and str(inputs_town) != "Recommendation mode"
        else "Any"
    )
    default_town = default_town if default_town in town_options else "Any"

    default_type = inputs_flat_type if inputs_flat_type in room_options else "Any"

    col1, col2 = st.columns(2)

    with col1:
        hyp_town = st.selectbox(
            "Town",
            options=town_options,
            index=town_options.index(default_town),
            key="explore_hyp_town_dropdown",
        )

        use_lease = st.checkbox(
            "Filter by minimum remaining lease",
            value=bool(inputs_lease),
            key="explore_use_lease_filter",
        )

        hyp_remaining_lease_years = st.slider(
            "Minimum remaining lease (years)",
            min_value=1,
            max_value=99,
            value=int(inputs_lease if inputs_lease else 70),
            step=1,
            key="explore_hyp_remaining_lease",
            disabled=not use_lease,
        )

    with col2:
        hyp_flat_type = st.selectbox(
            "Flat type",
            options=room_options,
            index=room_options.index(default_type),
            key="explore_hyp_flat_type",
        )

        use_area = st.checkbox(
            "Filter by floor area",
            value=bool(inputs_floor_area),
            key="explore_use_area_filter",
        )

        hyp_area = st.slider(
            "Floor area (sqm)",
            min_value=20.0,
            max_value=300.0,
            value=float(inputs_floor_area if inputs_floor_area else 90.0),
            step=1.0,
            key="explore_hyp_area",
            disabled=not use_area,
        )

    submitted = st.button("Check custom flat median", type="primary", key="explore_hyp_submit")

    if not submitted:
        return

    if listings_df is None or listings_df.empty:
        st.info("No dataset available for median lookup.")
        return

    filtered = listings_df.copy()

    if hyp_town != "Any" and "town" in filtered.columns:
        filtered = filtered[
            filtered["town"].fillna("").str.upper() == str(hyp_town).upper()
        ]

    if hyp_flat_type != "Any" and "flat_type" in filtered.columns:
        filtered = filtered[
            filtered["flat_type"].fillna("").str.upper() == str(hyp_flat_type).upper()
        ]

    if use_area and "floor_area_sqm" in filtered.columns:
        area_vals = pd.to_numeric(filtered["floor_area_sqm"], errors="coerce")
        filtered = filtered[
            (area_vals >= hyp_area - 20) &
            (area_vals <= hyp_area + 20)
        ]

    lease_col = None
    if "remaining_lease_years" in filtered.columns:
        lease_col = "remaining_lease_years"
    elif "remaining_lease" in filtered.columns:
        lease_col = "remaining_lease"

    if use_lease and lease_col:
        lease_vals = pd.to_numeric(filtered[lease_col], errors="coerce")
        filtered = filtered[lease_vals >= hyp_remaining_lease_years]

    median_price = _compute_median_from_filtered_rows(filtered)

    st.markdown("#### Results")

    m1, m2 = st.columns(2)
    with m1:
        st.metric(
            "Recent median transacted",
            fmt_sgd(median_price) if pd.notna(median_price) else "—"
        )
    with m2:
        st.metric("Matching transactions found", len(filtered))

    st.markdown("#### Selected inputs")

    summary_items = []

    summary_items.append(f"**Town:** {hyp_town if hyp_town != 'Any' else 'Any'}")
    summary_items.append(f"**Flat type:** {hyp_flat_type if hyp_flat_type != 'Any' else 'Any'}")
    summary_items.append(f"**Floor area:** {f'{hyp_area:.0f} sqm (±20 sqm)' if use_area else 'Any'}")
    summary_items.append(f"**Minimum remaining lease:** {f'{hyp_remaining_lease_years} years' if use_lease else 'Any'}")

    for item in summary_items:
        st.write(item)

    if filtered.empty:
        st.warning("No similar flats found in the current dataset.")

def _estimate_hypothetical_amenities(result: dict, listings_df: pd.DataFrame) -> dict:
    if listings_df is None or listings_df.empty:
        return {}

    df = listings_df.copy()

    if "town" not in df.columns or "flat_type" not in df.columns:
        return {}

    df = df[
        df["town"].fillna("").str.upper().eq(str(result["town"]).upper()) &
        df["flat_type"].fillna("").str.upper().eq(str(result["flat_type"]).upper())
    ]

    if "floor_area_sqm" in df.columns:
        area = pd.to_numeric(df["floor_area_sqm"], errors="coerce")
        df = df[area.between(float(result["floor_area_sqm"]) - 15, float(result["floor_area_sqm"]) + 15)]

    lease_col = None
    if "remaining_lease_years" in df.columns:
        lease_col = "remaining_lease_years"
    elif "remaining_lease" in df.columns:
        lease_col = "remaining_lease"

    if lease_col:
        lease = pd.to_numeric(df[lease_col], errors="coerce")
        df = df[lease.between(float(result["remaining_lease"]) - 5, float(result["remaining_lease"]) + 5)]

    if "storey_midpoint" in df.columns:
        storey = pd.to_numeric(df["storey_midpoint"], errors="coerce")
        df = df[storey.between(float(result["storey"]) - 5, float(result["storey"]) + 5)]

    if df.empty:
        return {}

    amenity_cols = [
        "train_1_dist_m",
        "bus_1_dist_m",
        "school_1_dist_m",
        "hawker_1_dist_m",
        "mall_1_dist_m",
        "polyclinic_1_dist_m",
        "supermarket_1_dist_m",
        "walk_train_min1",
        "walk_bus_min1",
        "walk_primary_school_min1",
        "walk_hawker_min1",
        "walk_mall_min1",
        "walk_polyclinic_min1",
        "walk_supermarket_min1",
    ]

    usable_cols = [c for c in amenity_cols if c in df.columns]
    if not usable_cols:
        return {"similar_flats_used_for_amenities": len(df)}

    medians = (
        df[usable_cols]
        .apply(pd.to_numeric, errors="coerce")
        .median(numeric_only=True)
        .to_dict()
    )
    medians["similar_flats_used_for_amenities"] = len(df)

    return medians


def _build_hypothetical_result_row(result: dict) -> dict:
    row = {
        "listing_id": (
            f"HYP-{result['town']}-{result['flat_type']}-"
            f"{int(result['floor_area_sqm'])}sqm-{int(result['remaining_lease'])}y-{int(result['storey'])}"
        ),
        "address": (
            f"Hypothetical flat · {result['town']} · {result['flat_type']} · "
            f"{int(result['floor_area_sqm'])} sqm · Storey {int(result['storey'])}"
        ),
        "town": result["town"],
        "flat_type": result["flat_type"],
        "floor_area_sqm": result["floor_area_sqm"],
        "remaining_lease_years": result["remaining_lease"],
        "remaining_lease": result["remaining_lease"],
        "storey_range": str(result["storey"]),
        "storey_midpoint": result["storey"],
        "predicted_price": result["predicted_price"],
        "predicted_price_lower": result.get("confidence_low"),
        "predicted_price_upper": result.get("confidence_high"),
        "comparison_source": "Explore",
        "is_hypothetical": True,
        "similar_flats_used_for_amenities": result.get("similar_flats_used_for_amenities"),
    }

    amenity_cols = [
        "train_1_dist_m",
        "bus_1_dist_m",
        "school_1_dist_m",
        "hawker_1_dist_m",
        "mall_1_dist_m",
        "polyclinic_1_dist_m",
        "supermarket_1_dist_m",
        "walk_train_min1",
        "walk_bus_min1",
        "walk_primary_school_min1",
        "walk_hawker_min1",
        "walk_mall_min1",
        "walk_polyclinic_min1",
        "walk_supermarket_min1",
    ]

    for col in amenity_cols:
        if col in result:
            row[col] = result[col]

    return row

def _render_hypothetical_price_predictor(inputs=None, listings_df: pd.DataFrame = None):
    st.markdown("### Predict hypothetical flat price")
    st.caption("Estimate the modelled fair value of a flat profile before searching live listings.")

    town_options = [
        "ANG MO KIO", "BEDOK", "BISHAN", "BUKIT BATOK", "BUKIT MERAH",
        "BUKIT PANJANG", "BUKIT TIMAH", "CENTRAL AREA", "CHOA CHU KANG",
        "CLEMENTI", "GEYLANG", "HOUGANG", "JURONG EAST", "JURONG WEST",
        "KALLANG/WHAMPOA", "MARINE PARADE", "PASIR RIS", "PUNGGOL",
        "QUEENSTOWN", "SEMBAWANG", "SENGKANG", "SERANGOON", "TAMPINES",
        "TOA PAYOH", "WOODLANDS", "YISHUN"
    ]
    flat_type_options = ["2 ROOM", "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE"]

    inputs_town = getattr(inputs, "town", None) if inputs is not None else None
    inputs_flat_type = getattr(inputs, "flat_type", None) if inputs is not None else None
    inputs_floor_area = getattr(inputs, "floor_area_sqm", None) if inputs is not None else None
    inputs_lease = getattr(inputs, "remaining_lease_years", None) if inputs is not None else None

    default_town = str(inputs_town).upper() if inputs_town else "ANG MO KIO"
    if default_town not in town_options:
        default_town = "ANG MO KIO"

    default_flat_type = inputs_flat_type if inputs_flat_type in flat_type_options else "4 ROOM"
    default_area = float(inputs_floor_area) if inputs_floor_area else 90.0
    default_lease = int(inputs_lease) if inputs_lease else 70

    c1, c2 = st.columns(2)

    with c1:
        hyp_town = st.selectbox(
            "Town",
            options=town_options,
            index=town_options.index(default_town),
            key="explore_predict_hyp_town",
        )
        hyp_floor_area = st.slider(
            "Floor area (sqm)",
            min_value=20.0,
            max_value=300.0,
            value=float(default_area),
            step=1.0,
            key="explore_predict_hyp_area",
        )
        hyp_storey = st.number_input(
            "Storey",
            min_value=1,
            max_value=50,
            value=5,
            step=1,
            key="explore_predict_hyp_storey",
        )

    with c2:
        hyp_flat_type = st.selectbox(
            "Flat type",
            options=flat_type_options,
            index=flat_type_options.index(default_flat_type),
            key="explore_predict_hyp_flat_type",
        )
        hyp_remaining_lease = st.slider(
            "Remaining lease (years)",
            min_value=1,
            max_value=99,
            value=int(default_lease),
            step=1,
            key="explore_predict_hyp_lease",
        )

    predict_clicked = st.button(
        "Predict hypothetical price",
        type="primary",
        key="explore_predict_hyp_submit",
    )

    if predict_clicked:
        try:
            from backend_predictor_listings.price_predictor.notebooks.predict_hypothetical import predict_hypothetical
        except Exception as e:
            st.error(f"Hypothetical predictor is unavailable in this environment: {e}")
            return

        try:
            result = predict_hypothetical(
                floor_area_sqm=hyp_floor_area,
                town=hyp_town,
                flat_type=hyp_flat_type,
                remaining_lease_years=hyp_remaining_lease,
                storey=hyp_storey,
            )

            amenity_estimates = _estimate_hypothetical_amenities(result, listings_df)
            result.update(amenity_estimates)

            st.session_state["explore_hyp_result"] = result
        except Exception as e:
            st.error(f"Could not generate prediction: {e}")
            return

    result = st.session_state.get("explore_hyp_result")
    if not result:
        return

    st.markdown("#### Predicted result")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Estimated price", fmt_sgd(result["predicted_price"]))
    with m2:
        low = result.get("confidence_low")
        st.metric("95% CI low", fmt_sgd(low) if low is not None else "—")
    with m3:
        high = result.get("confidence_high")
        st.metric("95% CI high", fmt_sgd(high) if high is not None else "—")

    hyp_row = _build_hypothetical_result_row(result)

    st.markdown("#### Snapshot")
    _render_flat_snapshot(pd.Series(hyp_row))

    if _is_row_already_saved(hyp_row):
        st.button(
            "Saved ♥",
            key="explore_save_hyp_flat_disabled",
            use_container_width=True,
            disabled=True,
        )
    else:
        if st.button(
            "Save hypothetical flat",
            key="explore_save_hyp_flat",
            use_container_width=True,
        ):
            if _save_extra_row(hyp_row):
                st.success("Hypothetical flat saved to Saved tab.")
                st.rerun()


def render_explore_page(inputs=None, listings_df: pd.DataFrame = None):
    st.markdown("## Explore")
    st.caption("Look up a specific flat, check a custom flat median, or estimate a hypothetical flat price.")

    if listings_df is None:
        listings_df = pd.DataFrame()

    tab1, tab2, tab3 = st.tabs([
        "🔎 Search specific flat",
        "📊 Check custom flat median",
        "🏠 Predict hypothetical flat price",
    ])

    with tab1:
        st.markdown("### Quick lookup")
        st.caption("Search for a specific flat by address and view its details.")

        if listings_df.empty:
            st.info("No listings dataset available for lookup.")
        else:
            search_query = st.text_input(
                "Search by address",
                placeholder="e.g. 4 Taman Ho Swee",
                key="explore_address_search",
            )

            if not search_query.strip():
                st.info("Enter part of an address to search across the full listing.")
            else:
                search_df = listings_df.copy()

                if "address" not in search_df.columns:
                    st.warning("Address column not found in dataset.")
                else:
                    query = search_query.strip().lower()

                    match_df = search_df[
                        search_df["address"].fillna("").str.lower().str.contains(query, na=False)
                    ].copy()

                    if match_df.empty:
                        st.warning("No matching flats found.")
                    else:
                        match_df = match_df.sort_values("address").reset_index(drop=True)

                        selected_match_idx = st.selectbox(
                            "Matching addresses",
                            options=match_df.index.tolist(),
                            format_func=lambda i: match_df.loc[i, "address"],
                            key="explore_matching_listing_dropdown",
                            label_visibility="collapsed",
                        )

                        selected_row = match_df.loc[selected_match_idx]

                        asking_price = selected_row.get("asking_price", np.nan)
                        flat_type = selected_row.get("flat_type", "—")
                        town = selected_row.get("town", "—")

                        st.markdown(
                            f"""
                            <div style="
                                margin-top:0.55rem;
                                padding:0.9rem 1rem;
                                border:1.5px solid #fecdd3;
                                border-radius:14px;
                                background:#fff7f7;
                            ">
                                <div style="font-size:0.72rem;font-weight:700;color:#e11d48;text-transform:uppercase;letter-spacing:0.06em;">
                                    Selected flat
                                </div>
                                <div style="font-size:1rem;font-weight:700;color:#0f172a;margin-top:0.22rem;">
                                    {selected_row.get('address', 'Unknown address')}
                                </div>
                                <div style="font-size:0.84rem;color:#64748b;margin-top:0.18rem;">
                                    {flat_type} · {town}
                                    {" · " + fmt_sgd(asking_price) if pd.notna(asking_price) else ""}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        save_col, view_col = st.columns(2)

                        raw_row_dict = selected_row.to_dict()
                        already_saved = _is_row_already_saved(raw_row_dict)

                        with save_col:
                            if already_saved:
                                st.button(
                                    "Saved ♥",
                                    key="explore_save_selected_flat_disabled",
                                    use_container_width=True,
                                    disabled=True,
                                )
                            else:
                                if st.button(
                                    "Save flat",
                                    key="explore_save_selected_flat",
                                    use_container_width=True,
                                ):
                                    row_to_save = _enrich_explore_row(raw_row_dict, inputs)
                                    row_to_save["comparison_source"] = "Explore"

                                    if "listing_id" not in row_to_save or pd.isna(row_to_save["listing_id"]):
                                        row_to_save["listing_id"] = str(selected_match_idx)

                                    if _save_extra_row(row_to_save):
                                        st.success("Flat saved to Saved tab.")

                        with view_col:
                            if st.button(
                                "View listing details",
                                type="primary",
                                key="explore_view_listing_details",
                                use_container_width=True,
                            ):
                                show_listing_detail(raw_row_dict, show_actions=False)

    with tab2:
        _render_custom_flat_median(inputs, listings_df)

    with tab3:
        _render_hypothetical_price_predictor(inputs, listings_df)