import numpy as np
import pandas as pd

from backend.utils.constants import TOWN_COORDS, AMENITY_LABELS
from backend.schemas.inputs import UserInputs


def latlon_from_town(town: str):
    return TOWN_COORDS.get(town, (1.3521, 103.8198))


def mock_anchor_points(inputs: UserInputs):
    anchors = []
    for i, postal in enumerate(inputs.landmark_postals):
        anchors.append({
            "label": f"Anchor {i+1}",
            "postal_code": postal,
            "lat": 1.30 + np.random.uniform(-0.06, 0.06),
            "lon": 103.82 + np.random.uniform(-0.06, 0.06),
        })
    return anchors


def mock_amenities_for_town(towns):
    rows = []
    amenity_types = ["train", "bus", "polyclinic", "primary_school", "hawker", "mall", "supermarket"]

    for town in towns:
        base_lat, base_lon = latlon_from_town(town)

        for amenity_type in amenity_types:
            for i in range(3):
                rows.append({
                    "town": town,
                    "amenity_type": amenity_type,
                    "amenity_label": AMENITY_LABELS[amenity_type],
                    "lat": base_lat + np.random.uniform(-0.015, 0.015),
                    "lon": base_lon + np.random.uniform(-0.015, 0.015),
                })

    return pd.DataFrame(rows)

def mock_listing_points(listings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create mock lat/lon for listings using town centers.
    Minimal-change helper so we can plot actual top listings on the map.
    """
    if listings_df is None or listings_df.empty:
        return pd.DataFrame()

    rows = []
    for i, row in listings_df.reset_index(drop=True).iterrows():
        base_lat, base_lon = latlon_from_town(row["town"])
        rng = np.random.default_rng(200 + i)

        rows.append({
            "listing_id": row["listing_id"],
            "town": row["town"],
            "flat_type": row["flat_type"],
            "asking_price": row["asking_price"],
            "valuation_label": row.get("valuation_label", ""),
            "lat": base_lat + rng.uniform(-0.008, 0.008),
            "lon": base_lon + rng.uniform(-0.008, 0.008),
        })

    return pd.DataFrame(rows)

def get_map_bundle(inputs: UserInputs, recommendations_df: pd.DataFrame):
    selected_towns = []

    if inputs.town:
        selected_towns = list(inputs.town)
    elif recommendations_df is not None and not recommendations_df.empty:
        selected_towns = recommendations_df["town"].head(5).tolist()

    town_points = []
    for town in selected_towns:
        lat, lon = latlon_from_town(town)
        town_points.append({"town": town, "lat": lat, "lon": lon, "amenity_label": "Town", "postal_code": ""})

    town_points_df = pd.DataFrame(town_points)
    amenities_df = mock_amenities_for_town(selected_towns) if selected_towns else pd.DataFrame()
    anchor_points = mock_anchor_points(inputs)

    if town_points:
        center_lat = sum(x["lat"] for x in town_points) / len(town_points)
        center_lon = sum(x["lon"] for x in town_points) / len(town_points)
    else:
        center_lat, center_lon = 1.3521, 103.8198

    return {
        "town_points": town_points_df,
        "amenities_df": amenities_df,
        "anchor_points": anchor_points,
        "center_lat": center_lat,
        "center_lon": center_lon,
    }