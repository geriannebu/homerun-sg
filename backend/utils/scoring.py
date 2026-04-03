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
def _distance_score(dist):
    if dist is None or np.isnan(dist):
        return 40
    if dist <= 300:
        return 90
    elif dist <= 600:
        return 75
    elif dist <= 1000:
        return 60
    else:
        return 40


def compute_listing_scores(listings_df, budget: int | None, amenity_weights: dict,
                           ranking_profile: str = "balanced"):
    df = listings_df.copy()

    # Ensure asking_vs_predicted_pct exists
    if "asking_vs_predicted_pct" not in df.columns:
        df["asking_vs_predicted_pct"] = ((df["asking_price"] - df["predicted_price"]) / df["predicted_price"]) * 100

    alpha = RANKING_ALPHA.get(ranking_profile, 0.50)
    # ─────────────────────────────────────────
    # VALUE SCORE (unchanged — already correct)
    # ─────────────────────────────────────────
    if budget is None:
        df["budget_score"] = 50.0
    else:
        df["budget_gap"] = budget - df["asking_price"]
        df["budget_score"] = df["budget_gap"].apply(
            lambda x: max(0.0, min(100.0, 50.0 + x / 5000.0))
        )

    df["value_score"] = (
        100.0 - df["asking_vs_predicted_pct"]
        .clip(-20, 20)
        .abs() * 3.0
    )

    df["overall_value_score"] = (
        0.55 * df["value_score"] + 0.45 * df["budget_score"]
    ).round(1)

    # ─────────────────────────────────────────
    # REAL AMENITY SCORE (FIXED)
    # ─────────────────────────────────────────

    df["mrt_score"] = df["train_1_dist_m"].apply(_distance_score)
    df["bus_score"] = df["bus_1_dist_m"].apply(_distance_score)
    df["school_score"] = df["school_1_dist_m"].apply(_distance_score)
    df["hawker_score"] = df["hawker_1_dist_m"].apply(_distance_score)
    df["mall_score"] = df["mall_1_dist_m"].apply(_distance_score)
    df["health_score"] = df["polyclinic_1_dist_m"].apply(_distance_score)

    # apply user weights
    def weighted_amenity(row):
        scores = {
            "mrt": row["mrt_score"],
            "bus": row["bus_score"],
            "schools": row["school_score"],
            "hawker": row["hawker_score"],
            "retail": row["mall_score"],
            "healthcare": row["health_score"],
        }

        total = 0
        weight_sum = 0

        for k, v in amenity_weights.items():
            if k in scores:
                total += scores[k] * v
                weight_sum += v

        return total / weight_sum if weight_sum > 0 else np.mean(list(scores.values()))

    df["amenity_score"] = df.apply(weighted_amenity, axis=1).round(1)

    # ─────────────────────────────────────────
    # FINAL SCORE
    # ─────────────────────────────────────────
    df["final_score"] = (
        alpha * df["amenity_score"] +
        (1 - alpha) * df["value_score"]
    ).round(1)

    # ─────────────────────────────────────────
    # LABEL (important for UI)
    # ─────────────────────────────────────────
    df["valuation_label"] = df.apply(classify_listing, axis=1)

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

# Quiz scoring 

QUIZ_SCORE_BASE = 0.25

def compute_normalised_weights(selected, answers):
    scores = {a: QUIZ_SCORE_BASE for a in selected}
    for amenity in answers.values():
        if amenity and amenity in scores:
            scores[amenity] += 1.0

    total = sum(scores.values())
    if total == 0:
        n = len(selected)
        return {a: round(1 / n, 4) for a in selected}

    return {a: round(v / total, 4) for a, v in scores.items()}


def rank_sum_weights(ranking):
    n = len(ranking)
    denom = n * (n + 1) / 2
    return {a: round((n - i) / denom, 6) for i, a in enumerate(ranking)}