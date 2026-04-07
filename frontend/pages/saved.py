"""
frontend/pages/saved.py

Shows saved flats for the active session.
Users can click "View details" for full amenity/score breakdown,
select flats for comparison, or remove them.
"""

import html
import pandas as pd
import streamlit as st
import pydeck as pdk
import numpy as np

from backend.utils.formatters import fmt_sgd, valuation_tag_html
from frontend.state.session import get_active_session_liked_df, get_active_session
from frontend.components.listing_detail import show_listing_detail, _val_style
from backend.utils.constants import AMENITY_COLORS, AMENITY_LABELS, TOWN_COORDS


MAX_COMPARE = 5


def _normalize_amenity_key(key: str) -> str:
    mapping = {
        "mall": "retail",
        "shopping_mall": "retail",
        "retail": "retail",

        "polyclinic": "healthcare",
        "clinic": "healthcare",
        "hospital": "healthcare",
        "healthcare": "healthcare",

        "train": "mrt",
        "station": "mrt",
        "mrt": "mrt",

        "school": "schools",
        "primary_school": "schools",
        "schools": "schools",

        "bus": "bus",
        "hawker": "hawker",
        "supermarket": "supermarket",
    }
    return mapping.get(str(key).strip().lower(), str(key).strip().lower())


def _safe_amenity_label(key: str) -> str:
    key = _normalize_amenity_key(key)
    return AMENITY_LABELS.get(key, key.replace("_", " ").title())


def _safe_amenity_color(key: str):
    key = _normalize_amenity_key(key)
    return AMENITY_COLORS.get(key, [120, 120, 120, 180])


def _selected_amenities_for_saved_map() -> list[str]:
    selected = st.session_state.get("pref_selected_amenities", []) or []
    visible = []

    for key in selected:
        norm_key = _normalize_amenity_key(key)
        if norm_key not in visible:
            visible.append(norm_key)

    return visible


def _distinct_visible_amenity_colors(keys: list[str]) -> dict[str, list[int]]:
    palette = [
        [255, 99, 132, 210],
        [54, 162, 235, 210],
        [255, 206, 86, 210],
        [75, 192, 192, 210],
        [153, 102, 255, 210],
        [255, 159, 64, 210],
        [46, 204, 113, 210],
    ]

    color_map = {}
    for i, key in enumerate(keys):
        color_map[key] = palette[i % len(palette)]
    return color_map


def _selected_amenity_keys_from_weights(amenity_weights: dict) -> list[str]:
    if not amenity_weights:
        return []

    ranked = sorted(
        amenity_weights.items(),
        key=lambda x: (x[1] is not None, float(x[1]) if x[1] is not None else -1),
        reverse=True,
    )

    visible = []
    for key, weight in ranked:
        norm_key = _normalize_amenity_key(key)
        try:
            weight_val = float(weight)
        except Exception:
            continue

        if weight_val > 0 and norm_key not in visible:
            visible.append(norm_key)

    return visible


def _safe_text(value, fallback="—"):
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def _safe_currency(value):
    return fmt_sgd(value) if pd.notna(value) else "—"

def _sqm_to_sqft(val):
    try:
        if pd.isna(val):
            return None
        return round(float(val) * 10.7639)
    except Exception:
        return None

def _safe_pct_text(value):
    if pd.notna(value):
        return f"{float(value):+.1f}% vs model"
    return ""


def _escape(value):
    return html.escape(str(value))


def _render_saved_section(section_df: pd.DataFrame, section_title: str, selected_ids: list[str]):
    if section_df.empty:
        return

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin:1rem 0 0.7rem;'>"
        f"<div style='font-size:0.9rem;font-weight:800;color:#0f172a;'>{section_title}</div>"
        f"<div style='font-size:0.72rem;color:#9ca3af;background:#f7f8fa;"
        f"border:1px solid #e4e7ed;border-radius:999px;padding:2px 8px;'>"
        f"{len(section_df)} saved</div></div>",
        unsafe_allow_html=True,
    )

    for idx, row in section_df.reset_index(drop=True).iterrows():
        lid = str(row.get("listing_id", ""))
        session_id = str(row.get("session_id", "na"))
        is_sel = lid in selected_ids

        valuation_label = _safe_text(row.get("valuation_label"), "")
        tag_html = valuation_tag_html(valuation_label) if valuation_label else ""

        diff_raw = row.get("asking_vs_predicted_pct", row.get("valuation_pct", np.nan))
        diff = float(diff_raw) if pd.notna(diff_raw) else np.nan
        tag_html = ""
        if pd.notna(diff):
            val_label, val_color = _val_style(diff)
            tag_html = (
                f"<span style='display:inline-block;padding:5px 10px;border-radius:999px;"
                f"background:{val_color};color:white;font-weight:700;font-size:0.76rem;'>"
                f"{_escape(val_label)}"
                f"</span>"
            )

        badge = "♥ Saved"
        badge_col = "#059E87"

        border = "2px solid #059E87" if is_sel else "1px solid #e4e7ed"
        bg = "#f0fdf9" if is_sel else "rgba(255,255,255,0.96)"

        card_title = row.get("address")
        if pd.isna(card_title) or not str(card_title).strip():
            card_title = row.get("listing_id", "Unknown listing")
        card_title = _escape(card_title)

        flat_type = _safe_text(row.get("flat_type"))
        area = row.get("floor_area_sqm", np.nan)
        area_sqft = _sqm_to_sqft(area)

        storey = row.get("storey_range")
        if pd.isna(storey) or not str(storey).strip() or str(storey).strip().lower() == "nan":
            storey = row.get("floor_level_text", "")

        meta_parts = [flat_type]
        if area_sqft is not None:
            meta_parts.append(f"{area_sqft:,} sqft")

        storey_text = _safe_text(storey, "")
        if storey_text and storey_text != "—":
            if storey_text.lower().startswith("storey"):
                meta_parts.append(storey_text)
            else:
                meta_parts.append(f"Storey {storey_text}")

        meta_text = " · ".join(meta_parts)

        asking_value = row.get("asking_price", row.get("price"))
        predicted_value = row.get("predicted_price")

        asking_display = _safe_currency(asking_value)
        predicted_display = _safe_currency(predicted_value)
        diff_text = _safe_pct_text(diff)

        card_html = (
            f"<div style='border:{border};background:{bg};border-radius:16px;padding:16px;margin-bottom:10px;"
            f"box-shadow:0 2px 10px rgba(0,0,0,0.04);'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:16px;'>"
                    f"<div style='min-width:0;flex:1;'>"
                        f"<div style='font-size:1rem;font-weight:800;color:#0f172a;line-height:1.35;'>"
                            f"{card_title}"
                        f"</div>"
                        f"<div style='font-size:0.82rem;color:#6b7280;margin-top:4px;'>"
                            f"{_escape(meta_text)}"
                        f"</div>"
                    f"</div>"
                    f"<div style='text-align:right;flex-shrink:0;'>"
                        f"<div style='font-size:1.1rem;font-weight:800;color:#0f172a;'>"
                            f"{asking_display}"
                        f"</div>"
                        f"<div style='font-size:0.82rem;color:#6b7280;margin-top:4px;'>"
                            f"Predicted: {predicted_display}"
                        f"</div>"
                    f"</div>"
                f"</div>"
                f"<div style='display:flex;align-items:center;gap:8px;margin-top:10px;flex-wrap:wrap;'>"
                    f"{tag_html}"
                    f"<span style='font-size:0.76rem;color:#9ca3af;'>{_escape(diff_text)}</span>"
                    f"<span style='font-size:0.72rem;font-weight:700;color:{badge_col};margin-left:auto;'>"
                        f"{badge}"
                    f"</span>"
                f"</div>"
            f"</div>"
        )

        st.markdown(card_html, unsafe_allow_html=True)

        btn_a, btn_b, btn_c = st.columns([1.2, 0.9, 0.9])

        with btn_a:
            if st.button(
                "View details →",
                key=f"detail_{section_title}_{lid}_{session_id}_{idx}",
                use_container_width=True,
                type="primary",
            ):
                show_listing_detail(row.to_dict(), show_actions=False)

        with btn_b:
            sel_label = "✓ Selected" if is_sel else "Select"
            if st.button(
                sel_label,
                key=f"sel_{section_title}_{lid}_{session_id}_{idx}",
                use_container_width=True,
            ):
                cur = st.session_state.get("compare_selected_ids", [])

                if is_sel:
                    st.session_state.compare_selected_ids = [x for x in cur if x != lid]
                else:
                    if len(cur) >= MAX_COMPARE:
                        st.warning(f"You can compare up to {MAX_COMPARE} flats at a time.")
                    else:
                        st.session_state.compare_selected_ids = cur + [lid]

                st.rerun()

        with btn_c:
            if st.button(
                "Remove",
                key=f"rm_{section_title}_{lid}_{session_id}_{idx}",
                use_container_width=True,
            ):
                session = get_active_session()

                if session is not None:
                    if lid in session.get("liked_ids", []):
                        session["liked_ids"].remove(lid)

                    if "extra_saved_rows" in session:
                        session["extra_saved_rows"] = [
                            r for r in session["extra_saved_rows"]
                            if str(r.get("listing_id", "")) != str(lid)
                        ]

                st.session_state.compare_selected_ids = [
                    x for x in selected_ids if x != lid
                ]
                st.rerun()


def render_saved_page():
    session = get_active_session()
    liked_df = get_active_session_liked_df()

    extra_rows = []
    if session:
        extra_rows = session.get("extra_saved_rows", [])

    if extra_rows:
        extra_df = pd.DataFrame(extra_rows)
        liked_df = pd.concat([liked_df, extra_df], ignore_index=True, sort=False)

    if "comparison_source" not in liked_df.columns:
        liked_df["comparison_source"] = "Discover"
    else:
        liked_df["comparison_source"] = liked_df["comparison_source"].fillna("Discover")

    session_label = session["label"] if session else "No active session"

    st.markdown(
        "<h2 style='font-size:1.65rem;font-weight:800;letter-spacing:-0.03em;"
        "color:#0f172a;margin-bottom:0.3rem;'>Saved flats</h2>"
        "<p style='font-size:0.88rem;color:#9ca3af;margin-bottom:1.4rem;'>"
        f"Showing saved flats for: <strong>{session_label}</strong></p>",
        unsafe_allow_html=True,
    )

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
  <span class="ghost" style="top:8%;left:6%;font-size:2rem;opacity:0.12;animation:drift1 9s ease-in-out infinite;">🏠</span>
  <span class="ghost" style="top:10%;right:8%;font-size:1.7rem;opacity:0.10;animation:drift2 11s ease-in-out infinite;animation-delay:-3s;">🏡</span>
  <span class="ghost" style="top:55%;left:4%;font-size:1.3rem;opacity:0.09;animation:drift3 13s ease-in-out infinite;animation-delay:-5s;">🔑</span>
  <span class="ghost" style="top:58%;right:5%;font-size:1.4rem;opacity:0.09;animation:drift1 10s ease-in-out infinite;animation-delay:-7s;">🌳</span>
  <span class="ghost" style="bottom:10%;left:22%;font-size:1.1rem;opacity:0.08;animation:drift2 14s ease-in-out infinite;animation-delay:-2s;">✨</span>
  <span class="ghost" style="bottom:12%;right:24%;font-size:1.0rem;opacity:0.08;animation:drift3 12s ease-in-out infinite;animation-delay:-9s;">💫</span>

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

    valid_ids = set(liked_df["listing_id"].astype(str).tolist())
    current_selected = st.session_state.get("compare_selected_ids", [])
    selected_ids = [x for x in current_selected if str(x) in valid_ids]

    if selected_ids != current_selected:
        st.session_state["compare_selected_ids"] = selected_ids

    c1, c2 = st.columns([3, 1])

    with c1:
        st.markdown(
            f"<p style='font-size:0.82rem;color:#4b5563;padding-top:0.5rem;'>"
            f"<strong>{len(liked_df)}</strong> saved · "
            f"<strong>{len(selected_ids)}</strong>/{MAX_COMPARE} selected for comparison</p>",
            unsafe_allow_html=True,
    )

    with c2:
        btn_label = "Go to Compare →" if len(selected_ids) == 0 else f"Go to Compare ({len(selected_ids)}) →"
        if st.button(btn_label, key="saved_go_compare", type="primary", use_container_width=True):
            st.session_state.active_page = "Compare"
            st.rerun()

    st.markdown("---")
    st.markdown("#### Saved flats map")

    with st.expander("View saved flats map", expanded=False):
        st.caption("Showing your saved flats for the current session, with nearby amenities.")

        latest_inputs = st.session_state.get("latest_inputs")
        latest_map_bundle = st.session_state.get("latest_map_bundle")

        visible = []
        amenities_df = pd.DataFrame()
        visible_color_map = {}

        if latest_map_bundle is not None:
            visible = _selected_amenities_for_saved_map()
            amenities_df = latest_map_bundle.get("amenities_df", pd.DataFrame())

            if not amenities_df.empty and "amenity_type" in amenities_df.columns:
                amenities_df = amenities_df.copy()
                amenities_df["amenity_type"] = amenities_df["amenity_type"].apply(_normalize_amenity_key)

            visible_color_map = _distinct_visible_amenity_colors(visible)

        saved_points = liked_df.copy()

        if saved_points is not None and not saved_points.empty:
            saved_points = saved_points.copy()

            if "lat" in saved_points.columns:
                saved_points["lat"] = pd.to_numeric(saved_points["lat"], errors="coerce")
            else:
                saved_points["lat"] = np.nan

            if "lon" in saved_points.columns:
                saved_points["lon"] = pd.to_numeric(saved_points["lon"], errors="coerce")
            else:
                saved_points["lon"] = np.nan

            if "is_hypothetical" not in saved_points.columns:
                saved_points["is_hypothetical"] = False

            hyp_mask = saved_points["is_hypothetical"].fillna(False)
            for idx, r in saved_points[hyp_mask].iterrows():
                town_key = str(r.get("town", "")).upper().strip()
                if (pd.isna(r.get("lat")) or pd.isna(r.get("lon"))) and town_key in TOWN_COORDS:
                    saved_points.at[idx, "lat"] = TOWN_COORDS[town_key][0]
                    saved_points.at[idx, "lon"] = TOWN_COORDS[town_key][1]

            plotted_points = saved_points.dropna(subset=["lat", "lon"]).copy()

            if not amenities_df.empty and visible:
                filtered_amenities = amenities_df[amenities_df["amenity_type"].isin(visible)].copy()
            else:
                filtered_amenities = pd.DataFrame()

            amenity_distance_cols = {
                "mrt": "train_1_dist_m",
                "bus": "bus_1_dist_m",
                "schools": "school_1_dist_m",
                "hawker": "hawker_1_dist_m",
                "retail": "mall_1_dist_m",
                "healthcare": "polyclinic_1_dist_m",
                "supermarket": "supermarket_1_dist_m",
            }

            def _dist_km_from_row(r, amenity_type):
                col = amenity_distance_cols.get(amenity_type)
                if not col:
                    return ""
                val = r.get(col)
                if val is None or pd.isna(val):
                    return ""
                try:
                    return f"{float(val) / 1000:.2f}"
                except Exception:
                    return ""

            def saved_tooltip(r):
                raw_title = r.get("address", r.get("listing_id", "Unknown listing"))
                raw_title = _safe_text(raw_title, "Unknown listing")

                title_main = raw_title
                postal_caption = ""

                upper_title = str(raw_title).upper().strip()
                if " SINGAPORE " in upper_title:
                    parts = upper_title.rsplit(" SINGAPORE ", 1)
                    if len(parts) == 2:
                        title_main = parts[0].strip()
                        postal_code = parts[1].strip()
                        if postal_code.isdigit():
                            postal_caption = f"S({postal_code})"

                lines = [
                    f"<div style='font-weight:800;font-size:0.95rem;color:#0f172a;line-height:1.2;margin:1;'>"
                    f"{_escape(title_main)}</div>"
                ]

                if postal_caption:
                    lines.append(
                        f"<div style='font-size:0.72rem;color:#6b7280;line-height:1.1;margin:1;'>"
                        f"{_escape(postal_caption)}</div>"
                    )

                lines.append(
                    f"<div style='line-height:1.1;margin:1;'><b>Town:</b> {_escape(r.get('town', '—'))}</div>"
                )
                lines.append(
                    f"<div style='line-height:1.1;margin:1;'><b>Type:</b> {_escape(r.get('flat_type', '—'))}</div>"
                )

                if bool(r.get("is_hypothetical", False)):
                    lines.append(
                        "<div style='line-height:1.1;margin:1;'><b>Location:</b> Approximate town-level estimate</div>"
                    )

                if pd.notna(r.get("asking_price")):
                    lines.append(
                        f"<div style='line-height:1.1;margin:1;'><b>Asking price:</b> ${int(r['asking_price']):,}</div>"
                    )
                elif pd.notna(r.get("price")):
                    lines.append(
                        f"<div style='line-height:1.1;margin:1;'><b>Price:</b> ${int(r['price']):,}</div>"
                    )
                elif pd.notna(r.get("predicted_price")):
                    lines.append(
                        f"<div style='line-height:1.1;margin:1;'><b>Predicted price:</b> ${int(r['predicted_price']):,}</div>"
                    )

                for amenity_type in visible:
                    km_val = _dist_km_from_row(r, amenity_type)
                    if km_val != "":
                        prefix = "Estimated nearest" if bool(r.get("is_hypothetical", False)) else "Nearest"
                        lines.append(
                            f"<div style='line-height:1.1;margin:1;'><b>{prefix} {_escape(_safe_amenity_label(amenity_type))}:</b> {km_val} km</div>"
                        )

                return "".join(lines)

            if not plotted_points.empty:
                plotted_points["tooltip_html"] = plotted_points.apply(saved_tooltip, axis=1)

                summary = plotted_points[["address", "town"]].copy()

                def _clean_address_for_table(val):
                    text = _safe_text(val, "Unknown listing")
                    upper_text = str(text).upper().strip()

                    if " SINGAPORE " in upper_text:
                        parts = upper_text.rsplit(" SINGAPORE ", 1)
                        if len(parts) == 2:
                            return parts[0].strip()

                    return text

                summary["address"] = summary["address"].apply(_clean_address_for_table)
                summary = summary.rename(columns={"address": "Address", "town": "Town"})

                for amenity_type in visible:
                    amenity_type = _normalize_amenity_key(amenity_type)
                    source_col = amenity_distance_cols.get(amenity_type)

                    if source_col in plotted_points.columns:
                        summary[f"Nearest {_safe_amenity_label(amenity_type)} (km)"] = (
                            pd.to_numeric(plotted_points[source_col], errors="coerce") / 1000
                        ).round(2)

                st.markdown("**Nearest amenity distances**")

                selection_event = st.dataframe(
                    summary,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="saved_map_summary_table",
                )

                selected_rows = []
                try:
                    selected_rows = selection_event.selection.rows
                except Exception:
                    selected_rows = []

                if selected_rows:
                    selected_idx = selected_rows[0]
                    if 0 <= selected_idx < len(plotted_points):
                        st.session_state["saved_map_focus_listing_id"] = str(
                            plotted_points.iloc[selected_idx]["listing_id"]
                        )
                else:
                    st.session_state["saved_map_focus_listing_id"] = None

                selected_focus_listing_id = st.session_state.get("saved_map_focus_listing_id")

                focus_row = None
                if selected_focus_listing_id:
                    match = plotted_points[
                        plotted_points["listing_id"].astype(str) == str(selected_focus_listing_id)
                    ]
                    if not match.empty:
                        focus_row = match.iloc[0]

                if focus_row is not None:
                    center_lat = float(focus_row["lat"])
                    center_lon = float(focus_row["lon"])
                    map_zoom = 12.3
                else:
                    center_lat = float(plotted_points["lat"].mean())
                    center_lon = float(plotted_points["lon"].mean())
                    map_zoom = 11.8

                real_points = plotted_points[~plotted_points["is_hypothetical"].fillna(False)].copy()
                hyp_points = plotted_points[plotted_points["is_hypothetical"].fillna(False)].copy()

                layers = []

                if not filtered_amenities.empty:
                    for amenity_type in visible:
                        amenity_type = _normalize_amenity_key(amenity_type)
                        sub = filtered_amenities[filtered_amenities["amenity_type"] == amenity_type]
                        if not sub.empty:
                            sub = sub.copy()
                            amenity_label = _safe_amenity_label(amenity_type)
                            amenity_color = visible_color_map.get(
                                amenity_type,
                                _safe_amenity_color(amenity_type)
                            )

                            sub["tooltip_html"] = sub.apply(
                                lambda r: (
                                    f"<b>{_escape(amenity_label)}</b><br/>"
                                    f"<b>Town:</b> {_escape(r.get('town', '—'))}<br/>"
                                    f"<b>Name:</b> {_escape(r.get('amenity_label', '—'))}<br/>"
                                ),
                                axis=1,
                            )

                            layers.append(
                                pdk.Layer(
                                    "ScatterplotLayer",
                                    data=sub,
                                    get_position="[lon, lat]",
                                    get_fill_color=amenity_color,
                                    get_radius=220 if amenity_type == "bus" else 260,
                                    pickable=True,
                                )
                            )

                if not real_points.empty:
                    layers.append(
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=real_points,
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

                if not hyp_points.empty:
                    layers.append(
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=hyp_points,
                            get_position="[lon, lat]",
                            get_fill_color=[255, 68, 88, 60],
                            get_line_color=[255, 68, 88, 180],
                            line_width_min_pixels=2,
                            stroked=True,
                            filled=True,
                            get_radius=1800,
                            pickable=True,
                        )
                    )
                    layers.append(
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=hyp_points,
                            get_position="[lon, lat]",
                            get_fill_color=[255, 68, 88, 220],
                            get_radius=140,
                            pickable=True,
                        )
                    )

                if focus_row is not None:
                    glow_df = pd.DataFrame([focus_row])

                    layers.append(
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=glow_df,
                            get_position="[lon, lat]",
                            get_fill_color=[255, 196, 0, 70],
                            get_radius=700,
                            pickable=False,
                        )
                    )

                deck = pdk.Deck(
                    map_provider="carto",
                    map_style="light",
                    initial_view_state=pdk.ViewState(
                        latitude=center_lat,
                        longitude=center_lon,
                        zoom=map_zoom,
                        pitch=0,
                    ),
                    layers=layers,
                    tooltip={
                        "html": "{tooltip_html}",
                        "style": {"backgroundColor": "white", "color": "black"},
                    },
                )

                st.pydeck_chart(deck, use_container_width=True)
            else:
                st.info("Saved flats do not have mappable coordinates yet.")
        else:
            st.info("No saved flats available to show on the map.")

    discover_df = liked_df[liked_df["comparison_source"] == "Discover"].copy()
    explore_df = liked_df[liked_df["comparison_source"] == "Explore"].copy()

    _render_saved_section(discover_df, "Saved from Discover", selected_ids)
    _render_saved_section(explore_df, "Saved from Explore", selected_ids)
