import pandas as pd
from data.load_data import load_all_data
from backend.schemas.inputs import UserInputs
from backend.services.recommender import run_recommender, RANKING_ALPHA
from backend.services.recommendation_service import recommend_towns_real

DEFAULT_AMENITY_WEIGHTS = {
    "train":          1,
    "bus":            1,
    "primary_school": 1,
    "hawker":         1,
    "mall":           1,
    "polyclinic":     1,
    "supermarket":    1,
}

def get_prediction_bundle(inputs: UserInputs, ranking_profile: str = "balanced") -> dict:
    listings_df, _ = load_all_data()

    town = (inputs.town or "").strip().upper() or None
    if town:
        listings_df = listings_df[listings_df["town"] == town]

    flat_types = getattr(inputs, "flat_types", None)
    if flat_types:
        listings_df = listings_df[listings_df["flat_type"].isin(flat_types)]

    if getattr(inputs, "floor_area_sqm", None):
        listings_df = listings_df[
            listings_df["floor_area_sqm"] >= inputs.floor_area_sqm
        ]

    budget = getattr(inputs, "budget", None)
    if budget:
        listings_df = listings_df[listings_df["asking_price"] <= budget]

    remaining = getattr(inputs, "remaining_lease_years", None)
    if remaining:
        listings_df = listings_df[listings_df["remaining_lease"] >= remaining]

    listings_df = listings_df.reset_index(drop=True)
    if "listing_id" not in listings_df.columns:
        listings_df["listing_id"] = listings_df.index.astype(str)

    amenity_weights = getattr(inputs, "amenity_weights", None) or DEFAULT_AMENITY_WEIGHTS
    amenity_ranking = getattr(inputs, "amenity_rank", None) or list(amenity_weights.keys())
    alpha = RANKING_ALPHA.get(ranking_profile, 0.50)

    rooms = []
    if flat_types:
        for ft in flat_types:
            try:
                rooms.append(int(str(ft).split()[0]))
            except Exception:
                pass

    min_sqft = 0
    if getattr(inputs, "floor_area_sqm", None):
        min_sqft = int(inputs.floor_area_sqm * 10.7639)

    rec = run_recommender(
        listings_df=listings_df,
        amenity_ranking=amenity_ranking,
        amenity_weights=amenity_weights,
        alpha=alpha,
        budget=budget or 10**9,
        rooms=rooms,
        preferred_towns=[town] if town else [],
        min_sqft=min_sqft,
        top_n=10,
    )

    scored_listings = rec["top"].copy()

    if "final_score" in scored_listings.columns:
        scored_listings = (
            scored_listings
            .sort_values("final_score", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
    else:
        scored_listings = scored_listings.head(10).reset_index(drop=True)

    viable_count = len(scored_listings)

    predicted_price = int(scored_listings["predicted_price"].median()) if viable_count else 0
    median_asking = int(scored_listings["asking_price"].median()) if viable_count else 0

    if (
        viable_count
        and "predicted_price_lower" in scored_listings.columns
        and scored_listings["predicted_price_lower"].notna().any()
    ):
        confidence_low = int(scored_listings["predicted_price_lower"].median())
        confidence_high = int(scored_listings["predicted_price_upper"].median())
    else:
        confidence_low = round(predicted_price * 0.96)
        confidence_high = round(predicted_price * 1.04)

    if viable_count and "median_similar" in scored_listings.columns:
        _med = scored_listings["median_similar"].dropna()
        recent_median_transacted = int(_med.median()) if len(_med) else 0
    else:
        recent_median_transacted = 0

    recommendations_df = None
    if not town:
        recommendations_df = recommend_towns_real(
            inputs=inputs,
            df=scored_listings,
            amenity_ranking=amenity_ranking,
            amenity_weights=amenity_weights,
            top_n=5,
        )

    mode = "town" if town else "recommendation"
    mode_label = f"Town mode: {town}" if town else "Recommendation mode"

    return {
        "predicted_price":          predicted_price,
        "recent_median_transacted": recent_median_transacted,
        "confidence_low":           confidence_low,
        "confidence_high":          confidence_high,
        "recent_period":            "last 6 months",
        "listings_df":              scored_listings,
        "recommendations_df":       recommendations_df,
        "viable_listing_count":     viable_count,
        "median_asking_active":     median_asking,
        "mode":                     mode,
        "mode_label":               mode_label,
        "ranking_profile":          ranking_profile,
        "filter_report": {
            "viable_listing_count": viable_count,
            "budget_filter":        budget,
            "flat_types":           getattr(inputs, "flat_types", None),
            "floor_area_sqm":       getattr(inputs, "floor_area_sqm", None),
        },
    }