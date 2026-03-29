import streamlit as st
import numpy as np


# ---------------------------------------------------------------------------
# Ranking alpha values by profile
# ---------------------------------------------------------------------------
RANKING_ALPHA = {
    "amenity-first": 0.75,
    "balanced":      0.50,
    "value-first":   0.25,
}

RANKING_LABELS = {
    "amenity-first": "Amenity-first (α = 0.75)",
    "balanced":      "Balanced (α = 0.50)",
    "value-first":   "Value-first (α = 0.25)",
}


# ---------------------------------------------------------------------------
# Valuation label
# ---------------------------------------------------------------------------
def classify_listing(row):
    pct = row["asking_vs_predicted_pct"]
    if pct <= -5:
        return "🔥 Steal"
    if pct <= 3:
        return "✅ Fair"
    if pct <= 10:
        return "⚠️ Slightly overpriced"
    return "🚩 Overpriced"


# ---------------------------------------------------------------------------
# Full score pipeline
# FinalScore = α · AmenityScore + (1−α) · ValueScore
# ---------------------------------------------------------------------------
def compute_listing_scores(listings_df, budget: int | None, amenity_weights: dict,
                           ranking_profile: str = "balanced"):
    """Return a scored + ranked copy of listings_df.

    New columns added:
        value_score          — 0‥100, how well price matches model
        budget_score         — 0‥100, how much budget headroom exists
        overall_value_score  — composite value metric (kept for compat)
        amenity_score        — 0‥100, proxy from amenity_weights
        final_score          — FinalScore = α·amenity + (1−α)·value
    """
    df = listings_df.copy()
    alpha = RANKING_ALPHA.get(ranking_profile, 0.50)

    # --- value score ---
    if budget is None:
        # Flexible-budget mode: do not penalise listings based on budget
        df["budget_gap"] = np.nan
        df["budget_score"] = 50.0   # neutral middle score
    else:
        df["budget_gap"] = budget - df["asking_price"]
        df["budget_score"] = df["budget_gap"].apply(
            lambda x: max(0.0, min(100.0, 50.0 + x / 5000.0))
        )

    df["value_score"] = (
        100.0 - df["asking_vs_predicted_pct"]
        .clip(lower=-20, upper=20)
        .abs()
        * 3.0
    )

    df["overall_value_score"] = (
        0.55 * df["value_score"] + 0.45 * df["budget_score"]
    ).round(1)

    # --- amenity score proxy ---
    # Real implementation would look up distances; mock uses weight average + jitter.
    rng_base = (
        df["asking_price"].astype(int).apply(lambda p: p % 997)
        + df.index
    )
    weight_avg = (
        sum(amenity_weights.values()) / len(amenity_weights)
        if amenity_weights else 3.0
    )
    df["amenity_score"] = (
        60.0
        + weight_avg * 5.0
        + rng_base.apply(lambda seed: (seed % 21) - 10)
    ).clip(0, 100).round(1)

    # --- final score ---
    df["final_score"] = (
        alpha * df["amenity_score"] + (1.0 - alpha) * df["value_score"]
    ).round(1)

    return df.sort_values("final_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Shortlist session helpers (unchanged)
# ---------------------------------------------------------------------------
def sync_shortlist_options(valid_ids):
    st.session_state.shortlist_ids = [
        x for x in st.session_state.shortlist_ids if x in valid_ids
    ]
    st.session_state.selected_shortlist_for_compare = [
        x for x in st.session_state.selected_shortlist_for_compare
        if x in valid_ids
    ]