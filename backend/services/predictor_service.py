import numpy as np

from backend.services.listings_service import mock_active_listings
from backend.services.recommendation_service import mock_recommend_towns
from backend.schemas.inputs import UserInputs
from backend.utils.scoring import compute_listing_scores


def mock_predict_price(inputs: UserInputs) -> float:
    base = {
        "2 ROOM":    320000,
        "3 ROOM":    410000,
        "4 ROOM":    560000,
        "5 ROOM":    700000,
        "EXECUTIVE": 850000,
    }

    mul = 1.0
    if inputs.town in {"Bishan", "Queenstown", "Bukit Merah",
                       "Kallang/Whampoa", "Toa Payoh"}:
        mul = 1.18
    elif inputs.town in {"Yishun", "Woodlands", "Jurong West",
                         "Choa Chu Kang", "Sembawang"}:
        mul = 0.92

    pred = (
        base[inputs.flat_type] * mul
        + max(0, (inputs.floor_area_sqm - 70) * 3800)
        - max(0, (2026 - inputs.lease_commence_year) * 2500)
        + 70000 * sum(inputs.amenity_weights.values()) / len(inputs.amenity_weights)
        + min(len(inputs.landmark_postals), 2) * 15000
    )
    return max(pred, 180000)


def mock_recent_transaction_median(inputs: UserInputs) -> float:
    return mock_predict_price(inputs) * np.random.uniform(0.95, 1.05)


def get_prediction_bundle(inputs: UserInputs, ranking_profile: str = "balanced"):
    """Return the full prediction bundle.

    Parameters
    ----------
    inputs          : UserInputs from the form
    ranking_profile : one of "amenity-first" | "balanced" | "value-first"
    """
    predicted_price = round(mock_predict_price(inputs))
    recent_median_transacted = round(mock_recent_transaction_median(inputs))

    # Raw listings (may be empty in a real backend after hard filters)
    listings_df = mock_active_listings(inputs)

    # Apply hard budget filter only if user set a budget
    if inputs.budget is not None:
        listings_df = listings_df[listings_df["asking_price"] <= inputs.budget].copy()
    else:
        listings_df = listings_df.copy()

    # Compute scores and rank
    if not listings_df.empty:
        listings_df = compute_listing_scores(
            listings_df,
            budget=inputs.budget,
            amenity_weights=inputs.amenity_weights,
            ranking_profile=ranking_profile,
        )

    viable_listing_count = len(listings_df)
    median_asking_active = (
        round(listings_df["asking_price"].median()) if viable_listing_count else 0
    )

    # Build a filter report for the no-match recovery UI
    filter_report = _build_filter_report(inputs, listings_df, predicted_price)

    recommendations_df = (
        mock_recommend_towns(inputs) if not inputs.town else None
    )

    mode = "town" if inputs.town else "recommendation"
    mode_label = (
        f"Town mode: {inputs.town}" if inputs.town else "Recommendation mode"
    )

    return {
        "predicted_price": predicted_price,
        "recent_median_transacted": recent_median_transacted,
        "confidence_low": round(predicted_price * 0.96),
        "confidence_high": round(predicted_price * 1.04),
        "recent_period": "last 6 months",
        "listings_df": listings_df,
        "recommendations_df": recommendations_df,
        "viable_listing_count": viable_listing_count,
        "median_asking_active": median_asking_active,
        "mode": mode,
        "mode_label": mode_label,
        "ranking_profile": ranking_profile,
        "filter_report": filter_report,
    }


def _build_filter_report(inputs: UserInputs, filtered_df, predicted_price: int) -> dict:
    """Produce a dict describing which filters passed / failed.

    Used by the no-match recovery UI.
    """
    if inputs.budget is None:
        budget_ok = True
        budget_gap = 0
        suggested_budget = None
        budget_set = False
    else:
        budget_gap = predicted_price - inputs.budget
        budget_ok = inputs.budget >= predicted_price * 0.90
        suggested_budget = round(predicted_price * 1.05 / 10000) * 10000
        budget_set = True

    return {
        "budget_set":           budget_set,
        "budget_ok":            budget_ok,
        "budget_gap":           max(0, budget_gap),
        "suggested_budget":     suggested_budget,
        "flat_type":            inputs.flat_type,
        "floor_area_specified": inputs.floor_area_sqm > 35.0,
        "floor_area_sqm":       inputs.floor_area_sqm,
        "town_specified":       inputs.town is not None,
        "town":                 inputs.town,
        "viable_count":         len(filtered_df),
    }