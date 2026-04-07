from typing import Any, Dict

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from backend.schemas.inputs import UserInputs
from backend.utils.constants import AMENITY_COLORS, AMENITY_LABELS
from backend.services.map_service import mock_listing_points


def top_priority_keys(weights: dict, top_n: int = 3):
    return [k for k, _ in sorted(weights.items(), key=lambda x: x[1], reverse=True)[:top_n]]


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def add_nearest_amenity_distances(
    listing_points: pd.DataFrame,
    amenities_df: pd.DataFrame,
    visible_types,
):
    if listing_points is None or listing_points.empty:
        return pd.DataFrame()

    out = listing_points.copy()

    for amenity_type in visible_types:
        sub = amenities_df[amenities_df["amenity_type"] == amenity_type] if not amenities_df.empty else pd.DataFrame()
        col = f"nearest_{amenity_type}_km"
        out[col] = ""

        if sub.empty:
            continue

        distances = []
        for _, row in out.iterrows():
            d = haversine_km(
                row["lat"],
                row["lon"],
                sub["lat"].values,
                sub["lon"].values,
            )
            distances.append(round(float(np.min(d)), 2))

        out[col] = distances

    return out


def ensure_cols(df: pd.DataFrame, defaults: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default
    return out


def build_tooltip_html(df: pd.DataFrame, point_type: str, visible_types=None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    visible_types = visible_types or []

    if point_type == "Amenity":
        out = ensure_cols(
            out,
            {
                "town": "",
                "amenity_label": "",
                "postal_code": "",
            },
        )
        out["tooltip_html"] = out.apply(
            lambda r: (
                f"<b>Amenity</b><br/>"
                f"<b>Town:</b> {r['town']}<br/>"
                f"<b>Name:</b> {r['amenity_label']}<br/>"
                f"<b>Postal code:</b> {r['postal_code']}"
            ),
            axis=1,
        )

    elif point_type == "Listing":
        out = ensure_cols(
            out,
            {
                "listing_id": "",
                "town": "",
                "flat_type": "",
                "asking_price": "",
                "valuation_label": "",
                "is_saved": False,
            },
        )

        def listing_tooltip(r):
            lines = [
                "<b>Recommended flat</b>",
                f"<b>ID:</b> {r['listing_id']}",
                f"<b>Town:</b> {r['town']}",
                f"<b>Type:</b> {r['flat_type']}",
                f"<b>Asking price:</b> ${int(r['asking_price']):,}" if pd.notna(r["asking_price"]) and str(r["asking_price"]) != "" else "",
                f"<b>Value:</b> {r['valuation_label']}",
                "<b>Saved:</b> Yes" if bool(r.get("is_saved", False)) else "",
            ]

            for amenity_type in visible_types:
                col = f"nearest_{amenity_type}_km"
                if col in out.columns and r.get(col, "") != "":
                    lines.append(f"<b>Nearest {AMENITY_LABELS[amenity_type]}:</b> {r[col]} km")

            return "<br/>".join([x for x in lines if x])

        out["tooltip_html"] = out.apply(listing_tooltip, axis=1)

    elif point_type == "Anchor":
        out = ensure_cols(
            out,
            {
                "label": "",
                "postal_code": "",
            },
        )
        out["tooltip_html"] = out.apply(
            lambda r: (
                f"<b>Anchor point</b><br/>"
                f"<b>Label:</b> {r['label']}<br/>"
                f"<b>Postal code:</b> {r['postal_code']}"
            ),
            axis=1,
        )

    elif point_type == "Town":
        out = ensure_cols(out, {"town": ""})
        out["tooltip_html"] = out.apply(
            lambda r: f"<b>Town</b><br/>{r['town']}",
            axis=1,
        )

    else:
        out["tooltip_html"] = "<b>Map point</b>"

    return out


def apply_saved_flag(listing_points: pd.DataFrame) -> pd.DataFrame:
    if listing_points is None or listing_points.empty:
        return pd.DataFrame()

    out = listing_points.copy()
    saved = st.session_state.get("saved_listings", [])

    saved_ids = set()
    if isinstance(saved, list):
        for item in saved:
            if isinstance(item, dict) and "listing_id" in item:
                saved_ids.add(item["listing_id"])

    out["is_saved"] = out["listing_id"].isin(saved_ids)
    return out


def get_selected_listing_point(listing_points: pd.DataFrame, selected_listing_id: str):
    if listing_points is None or listing_points.empty or not selected_listing_id:
        return pd.DataFrame()

    sub = listing_points[listing_points["listing_id"] == selected_listing_id]
    return sub.copy()


def compute_map_view(
    listing_points,
    town_pts,
    anchor_df,
    center_lat,
    center_lon,
    selected_listing_point=None,
):
    if selected_listing_point is not None and not selected_listing_point.empty:
        return (
            float(selected_listing_point.iloc[0]["lat"]),
            float(selected_listing_point.iloc[0]["lon"]),
            13.5,
        )

    all_lat = []
    all_lon = []

    for df in [listing_points, town_pts, anchor_df]:
        if df is not None and not df.empty and "lat" in df.columns and "lon" in df.columns:
            all_lat.extend(df["lat"].tolist())
            all_lon.extend(df["lon"].tolist())

    if not all_lat or not all_lon:
        return center_lat, center_lon, 11.2

    lat_min, lat_max = min(all_lat), max(all_lat)
    lon_min, lon_max = min(all_lon), max(all_lon)

    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    spread = max(lat_max - lat_min, lon_max - lon_min)

    if spread < 0.015:
        zoom = 13.0
    elif spread < 0.03:
        zoom = 12.2
    elif spread < 0.06:
        zoom = 11.4
    else:
        zoom = 10.8

    return center_lat, center_lon, zoom


def render_legend():
    st.markdown(
        """
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin: 8px 0 14px 0;">
            <div style="background:#fff; border:1px solid #ddd; border-radius:999px; padding:6px 12px;">🟡 Top flats</div>
            <div style="background:#fff; border:1px solid #ddd; border-radius:999px; padding:6px 12px;">🔵 Towns</div>
            <div style="background:#fff; border:1px solid #ddd; border-radius:999px; padding:6px 12px;">🟣 Anchor points</div>
            <div style="background:#fff; border:1px solid #ddd; border-radius:999px; padding:6px 12px;">⭐ Saved flats</div>
            <div style="background:#fff; border:1px solid #ddd; border-radius:999px; padding:6px 12px;">• Amenities</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_distance_summary_table(listing_points: pd.DataFrame, visible_types):
    if listing_points is None or listing_points.empty:
        st.caption("No flat distance summary available.")
        return None

    base_cols = ["listing_id", "town", "flat_type", "asking_price"]
    dist_cols = [f"nearest_{k}_km" for k in visible_types if f"nearest_{k}_km" in listing_points.columns]

    summary = listing_points[base_cols + dist_cols].copy()

    rename_map = {
        "listing_id": "Listing ID",
        "town": "Town",
        "flat_type": "Flat type",
        "asking_price": "Asking price",
    }
    for k in visible_types:
        col = f"nearest_{k}_km"
        if col in summary.columns:
            rename_map[col] = f"Nearest {AMENITY_LABELS[k]} (km)"

    summary = summary.rename(columns=rename_map)
    summary["Asking price"] = summary["Asking price"].apply(lambda x: f"${int(x):,}" if pd.notna(x) else "")

    event = st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="map_distance_table",
    )

    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        return listing_points.iloc[selected_idx]["listing_id"]

    return None


def build_flat_detail_html(row, visible_types):
    lines = [
        f"<b>{row['listing_id']}</b>",
        f"<b>Town:</b> {row['town']}",
        f"<b>Flat type:</b> {row['flat_type']}",
        f"<b>Asking price:</b> ${int(row['asking_price']):,}",
    ]

    if "valuation_label" in row and pd.notna(row["valuation_label"]):
        lines.append(f"<b>Value:</b> {row['valuation_label']}")

    for amenity_type in visible_types:
        col = f"nearest_{amenity_type}_km"
        if col in row and row[col] != "":
            lines.append(f"<b>Nearest {AMENITY_LABELS[amenity_type]}:</b> {row[col]} km")

    if "listing_url" in row and pd.notna(row["listing_url"]):
        lines.append(f"<b>Listing URL:</b> {row['listing_url']}")

    return "<br/>".join(lines)


def render_map_tab(inputs: UserInputs, map_bundle: Dict[str, Any]):
    st.markdown("#### Interactive map")
    st.caption("Showing top-priority amenities, anchor postals, towns, and recommended flats.")

    top_am = top_priority_keys(inputs.amenity_weights, 3)
    visible = st.multiselect(
        "Amenity layers",
        options=list(AMENITY_LABELS.keys()),
        default=top_am,
        format_func=lambda k: AMENITY_LABELS[k],
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        show_towns = st.checkbox("Show towns", value=True)
    with c2:
        show_anchors = st.checkbox("Show anchor points", value=True)
    with c3:
        show_listings = st.checkbox("Show recommended flats", value=True)
    with c4:
        show_saved_flats = st.checkbox("Show saved flats", value=True)

    town_pts = map_bundle["town_points"]
    amenities = map_bundle["amenities_df"]
    anchors = map_bundle["anchor_points"]

    filtered = amenities[amenities["amenity_type"].isin(visible)] if not amenities.empty else amenities

    latest_bundle = st.session_state.get("latest_bundle")
    listings_df = latest_bundle.get("listings_df") if latest_bundle else pd.DataFrame()

    top_listings = listings_df.head(5) if listings_df is not None and not listings_df.empty else pd.DataFrame()

    listing_points = mock_listing_points(top_listings)
    listing_points = add_nearest_amenity_distances(listing_points, filtered, visible)
    listing_points = apply_saved_flag(listing_points)

    if not show_saved_flats and not listing_points.empty:
        listing_points = listing_points[listing_points["is_saved"] == False]

    # Build layer-specific tooltip html
    town_pts = build_tooltip_html(town_pts, "Town")
    filtered = build_tooltip_html(filtered, "Amenity")
    listing_points = build_tooltip_html(listing_points, "Listing", visible_types=visible)

    if anchors:
        adf = pd.DataFrame(anchors)
        adf = build_tooltip_html(adf, "Anchor")
    else:
        adf = pd.DataFrame()

    # Table-driven selection
    selected_listing_id = None
    selected_listing_point = pd.DataFrame()
    selected_listing_row = None

    # First render a temporary table source before map-selection logic
    raw_listing_points = listing_points.copy()

    # Determine selected listing from dataframe selection state, if it exists
    table_state = st.session_state.get("map_distance_table")
    if table_state and isinstance(table_state, dict):
        rows = table_state.get("selection", {}).get("rows", [])
        if rows and not raw_listing_points.empty:
            idx = rows[0]
            if 0 <= idx < len(raw_listing_points):
                selected_listing_id = raw_listing_points.iloc[idx]["listing_id"]

    if selected_listing_id:
        selected_listing_point = get_selected_listing_point(raw_listing_points, selected_listing_id)
        if not selected_listing_point.empty:
            selected_listing_row = selected_listing_point.iloc[0]

    center_lat, center_lon, zoom = compute_map_view(
        raw_listing_points if show_listings else pd.DataFrame(),
        town_pts if show_towns else pd.DataFrame(),
        adf if show_anchors else pd.DataFrame(),
        map_bundle["center_lat"],
        map_bundle["center_lon"],
        selected_listing_point=selected_listing_point,
    )

    layers = []

    if show_towns and not town_pts.empty:
        layers += [
            pdk.Layer(
                "ScatterplotLayer",
                data=town_pts,
                get_position="[lon, lat]",
                get_fill_color=AMENITY_COLORS["town"],
                get_radius=1000,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=town_pts,
                get_position="[lon, lat]",
                get_text="town",
                get_size=16,
                get_color=[0, 0, 0, 200],
                get_alignment_baseline="bottom",
                pickable=False,
            ),
        ]

    if show_anchors and not adf.empty:
        layers += [
            pdk.Layer(
                "ScatterplotLayer",
                data=adf,
                get_position="[lon, lat]",
                get_fill_color=[140, 90, 160, 35],
                get_radius=1800,
                pickable=False,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=adf,
                get_position="[lon, lat]",
                get_fill_color=AMENITY_COLORS["anchor"],
                get_radius=600,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=adf,
                get_position="[lon, lat]",
                get_text="label",
                get_size=14,
                get_color=[90, 0, 90, 220],
                get_alignment_baseline="bottom",
                pickable=False,
            ),
        ]

    for k in visible:
        sub = filtered[filtered["amenity_type"] == k] if not filtered.empty else pd.DataFrame()
        if sub.empty:
            continue

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=sub,
                get_position="[lon, lat]",
                get_fill_color=AMENITY_COLORS[k],
                get_radius=260,
                pickable=True,
            )
        )

    if show_listings and not raw_listing_points.empty:
        unsaved_points = raw_listing_points[raw_listing_points["is_saved"] == False]
        saved_points = raw_listing_points[raw_listing_points["is_saved"] == True]

        if not unsaved_points.empty:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=unsaved_points,
                    get_position="[lon, lat]",
                    get_fill_color=[217, 163, 95, 210],
                    get_radius=320,
                    pickable=True,
                )
            )

        if not saved_points.empty and show_saved_flats:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=saved_points,
                    get_position="[lon, lat]",
                    get_fill_color=[245, 197, 66, 230],
                    get_line_color=[70, 70, 70, 220],
                    line_width_min_pixels=2,
                    stroked=True,
                    filled=True,
                    get_radius=420,
                    pickable=True,
                )
            )

        if not selected_listing_point.empty:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=selected_listing_point,
                    get_position="[lon, lat]",
                    get_fill_color=[255, 99, 71, 220],
                    get_line_color=[60, 60, 60, 255],
                    line_width_min_pixels=3,
                    stroked=True,
                    filled=True,
                    get_radius=560,
                    pickable=True,
                )
            )

    deck = pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=0,
        ),
        layers=layers,
        tooltip={
            "html": "{tooltip_html}",
            "style": {"backgroundColor": "white", "color": "black"},
        },
    )

    st.pydeck_chart(deck, use_container_width=True)

    render_legend()

    if selected_listing_row is not None:
        st.markdown("**Selected flat details**")
        st.markdown(
            f"""
            <div style="
                background:#ffffff;
                border:1px solid #E3E8EC;
                border-radius:18px;
                padding:1rem 1.1rem;
                box-shadow:0 4px 12px rgba(36,55,70,0.04);
                margin: 0.5rem 0 1rem 0;
            ">
                {build_flat_detail_html(selected_listing_row, visible)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("**Distance summary for shown flats**")
    _ = render_distance_summary_table(raw_listing_points, visible)

    ml, mr = st.columns(2)
    with ml:
        st.markdown("**Anchor points**")
        st.dataframe(
            pd.DataFrame(anchors) if anchors else pd.DataFrame({"status": ["None entered"]}),
            use_container_width=True,
            hide_index=True,
        )

    with mr:
        st.markdown("**Flats shown on map**")
        st.dataframe(
            top_listings if not top_listings.empty else pd.DataFrame({"status": ["None"]}),
            use_container_width=True,
            hide_index=True,
        )