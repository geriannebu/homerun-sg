import pandas as pd
from data.load_data import load_all_data
from backend.schemas.inputs import UserInputs
from backend.services.recommender import run_recommender, RANKING_ALPHA


DEFAULT_AMENITY_WEIGHTS = {
    "train":          1,
    "bus":            1,
    "primary_school": 1,
    "hawker":         1,
    "mall":           1,
    "polyclinic":     1,
    "supermarket":    1,
}


def recommend_towns_real(
    inputs: UserInputs,
    df: pd.DataFrame,
    amenity_ranking: list = None,
    amenity_weights: dict = None,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Aggregate already-scored listings by town and return the top_n towns.
    Expects df to already contain:
        town, final_score, predicted_price
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["town", "estimated_price", "match_score", "why_it_matches"])

    required = {"town", "final_score", "predicted_price"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["town", "estimated_price", "match_score", "why_it_matches"])

    results = []
    for town, grp in df.groupby("town"):
        if grp.empty:
            continue

        results.append({
            "town": town,
            "estimated_price": grp["predicted_price"].median(),
            "match_score": grp["final_score"].median() * 100,
            "count_listings": len(grp),
        })

    if not results:
        return pd.DataFrame(columns=["town", "estimated_price", "match_score", "why_it_matches"])

    town_df = (
        pd.DataFrame(results)
        .sort_values("match_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    def _why(row):
        reasons = []
        budget = getattr(inputs, "budget", None)
        if budget and row["estimated_price"] <= budget:
            reasons.append("affordable within budget")
        if row["match_score"] >= 70:
            reasons.append("good amenities nearby")
        if row["count_listings"] >= 5:
            reasons.append("lots of available flats")
        return "Strong overall fit: " + " · ".join(reasons) if reasons else "Good fit overall"

    town_df["why_it_matches"] = town_df.apply(_why, axis=1)

    return town_df[["town", "estimated_price", "match_score", "why_it_matches"]]


def get_top_towns(inputs: UserInputs, top_n: int = 5):
    listings_df, _ = load_all_data()

    amenity_weights = getattr(inputs, "amenity_weights", None) or DEFAULT_AMENITY_WEIGHTS
    amenity_ranking = getattr(inputs, "amenity_rank", None) or list(amenity_weights.keys())
    ranking_profile = getattr(inputs, "ranking_profile", "balanced")
    alpha = RANKING_ALPHA.get(ranking_profile, 0.50)

    preferred_towns = [inputs.town.strip().upper()] if getattr(inputs, "town", None) else []

    rooms = []
    flat_types = getattr(inputs, "flat_types", None)
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
        budget=getattr(inputs, "budget", None) or 10**9,
        rooms=rooms,
        preferred_towns=preferred_towns,
        min_sqft=min_sqft,
        top_n=200,
    )

    scored = rec["filtered"].copy()

    # score the filtered set, not just the scrambled top deck
    if scored.empty:
        return recommend_towns_real(inputs, df=scored, top_n=top_n)

    scored_top = run_recommender(
        listings_df=scored,
        amenity_ranking=amenity_ranking,
        amenity_weights=amenity_weights,
        alpha=alpha,
        budget=10**9,
        rooms=[],
        preferred_towns=[],
        min_sqft=0,
        top_n=len(scored),
    )["top"]

    return recommend_towns_real(inputs, df=scored_top, top_n=top_n)