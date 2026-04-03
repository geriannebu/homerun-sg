# backend/services/predictor_service.py
import pandas as pd
from data.load_data import load_all_data
from backend.schemas.inputs import UserInputs
from backend.utils.scoring import compute_listing_scores
from backend.services.recommendation_service import recommend_towns_real

DEFAULT_AMENITY_WEIGHTS = {
    "mrt":        1,
    "bus":        1,
    "schools":    1,
    "hawker":     1,
    "retail":     1,
    "healthcare": 1,
}


def get_prediction_bundle(inputs: UserInputs, ranking_profile: str = "balanced") -> dict:
    """
    Returns a bundle of:
    - scored listings DataFrame
    - town recommendations (only when no specific town was chosen)
    - predicted price, CI bounds, and recent median
    """
    # ── Load authoritative dataset ────────────────────────────────────────────
    listings_df, _ = load_all_data()

    # ── Hard filters from user inputs ─────────────────────────────────────────
    # Normalise town to uppercase so it matches the data exactly
    town = (inputs.town or "").strip().upper() or None

    if town:
        listings_df = listings_df[listings_df["town"] == town]

    flat_types = getattr(inputs, "flat_types", None)
    if flat_types:
        listings_df = listings_df[listings_df["flat_type"].isin(flat_types)]

    # Floor area: minimum only — show flats at or above the requested size.
    # No upper cap so larger flats are never excluded.
    if getattr(inputs, "floor_area_sqm", None):
        listings_df = listings_df[
            listings_df["floor_area_sqm"] >= inputs.floor_area_sqm
        ]

    # Budget filter — only apply when a concrete budget was provided
    budget = getattr(inputs, "budget", None)
    if budget:
        listings_df = listings_df[listings_df["asking_price"] <= budget]

    # Remaining lease filter
    remaining = getattr(inputs, "remaining_lease_years", None)
    if remaining:
        listings_df = listings_df[listings_df["remaining_lease"] >= remaining]

    listings_df = listings_df.reset_index(drop=True)
    if "listing_id" not in listings_df.columns:
        listings_df["listing_id"] = listings_df.index.astype(str)

    # ── Score listings ────────────────────────────────────────────────────────
    amenity_weights = getattr(inputs, "amenity_weights", None) or DEFAULT_AMENITY_WEIGHTS

    scored_listings = compute_listing_scores(
        listings_df,
        budget=budget,
        amenity_weights=amenity_weights,
        ranking_profile=ranking_profile,
    )

    viable_count = len(scored_listings)

    # ── Summary statistics ────────────────────────────────────────────────────
    predicted_price  = int(scored_listings["predicted_price"].median())  if viable_count else 0
    median_asking    = int(scored_listings["asking_price"].median())      if viable_count else 0

    # Use model CI bounds when available; fall back to ±4 %
    if viable_count and "predicted_price_lower" in scored_listings.columns and \
            scored_listings["predicted_price_lower"].notna().any():
        confidence_low  = int(scored_listings["predicted_price_lower"].median())
        confidence_high = int(scored_listings["predicted_price_upper"].median())
    else:
        confidence_low  = round(predicted_price * 0.96)
        confidence_high = round(predicted_price * 1.04)

    # Recent median transacted price (nullable — ~20 % of listings have no comparable)
    if viable_count and "median_similar" in scored_listings.columns:
        _med = scored_listings["median_similar"].dropna()
        recent_median_transacted = int(_med.median()) if len(_med) else 0
    else:
        recent_median_transacted = 0

    # ── Town recommendations (only in open-search / no-town mode) ─────────────
    recommendations_df = None
    if not town:
        recommendations_df = recommend_towns_real(
            inputs=inputs,
            df=scored_listings,
            amenity_ranking=getattr(inputs, "amenity_rank", None),
            amenity_weights=amenity_weights,
            top_n=5,
        )

    mode       = "town" if town else "recommendation"
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
