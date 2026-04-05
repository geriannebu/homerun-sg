from typing import Any, Dict
import streamlit as st

from backend.schemas.inputs import UserInputs
from backend.utils.formatters import fmt_sgd
from backend.utils.constants import AMENITY_LABELS

from frontend.components.listing_detail import show_listing_detail

# ---------------------------------------------------------------------------
# Value Cards (Predicted vs Budget)
# ---------------------------------------------------------------------------
def render_value_cards(bundle: Dict[str, Any], budget: int):
    pred = bundle.get("predicted_price") or 0
    trans = bundle.get("recent_median_transacted") or 0
    low = bundle.get("confidence_low", round(pred * 0.96)) or 0
    high = bundle.get("confidence_high", round(pred * 1.04)) or 0
    gap_pct = ((budget - pred) / pred) * 100 if (pred and budget is not None) else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Predicted fair value", fmt_sgd(pred))
    with c2:
        st.metric("Recent transacted median", fmt_sgd(trans))
    with c3:
        st.metric("Confidence band", f"{fmt_sgd(low)} – {fmt_sgd(high)}")
    with c4:
        st.metric("Budget vs fair value", f"{gap_pct:+.1f}%")


# ---------------------------------------------------------------------------
# Budget Banner
# ---------------------------------------------------------------------------
def render_budget_banner(bundle: Dict[str,Any], budget: int):
    pred = bundle.get("predicted_price") or 0
    if not pred or budget is None:
        st.info("Budget info unavailable")
        return

    gap  = (budget - pred)/pred
    if gap >= 0.05:
        msg = f"✓ Your budget is {gap*100:.1f}% above the predicted fair value — you have good room to negotiate."
    elif gap >= -0.05:
        msg = f"△ Your budget is close to the predicted fair value ({gap*100:+.1f}%). Look for steals."
    else:
        msg = f"↓ Your budget is {abs(gap)*100:.1f}% below the predicted fair value. Recommendation mode may surface better-value options."
    
    st.info(msg)


# ---------------------------------------------------------------------------
# HomeRun Pick Card
# ---------------------------------------------------------------------------
def render_homerun_pick(inputs: UserInputs, bundle: Dict[str,Any]):
    if bundle["listings_df"].empty:
        st.info("No listings available to pick from.")
        return
    
    amenity_weights = getattr(inputs, "amenity_weights", None) or {
        "train": 1,
        "bus": 1,
        "primary_school": 1,
        "hawker": 1,
        "mall": 1,
        "polyclinic": 1,
        "supermarket": 1,
    }

    top_df = bundle["listings_df"]
    if "final_score" in top_df.columns:
        top_df = top_df.sort_values("final_score", ascending=False)
    top = top_df.iloc[0]

    st.markdown("### 🏆 HomeRun Pick Right Now")
    st.write(f"**Listing ID:** {top['listing_id']}")
    st.write(f"**Town:** {top['town']}")
    st.write(f"**Flat Type:** {top.get('flat_type', 'N/A')}")
    st.write(f"**Floor Area:** {top.get('floor_area_sqm', 0)} sqm")
    st.write(f"**Asking Price:** {fmt_sgd(top['asking_price'])}")
    st.write(f"**Predicted Price:** {fmt_sgd(top['predicted_price'])}")
    st.write(f"**Valuation:** {top['valuation_pct']}")
    st.write(f"**Overall Score:** {float(top.get('final_score', 0)) * 100:.1f}/100")

    # Button to open listing detail dialog
    payload = top.to_dict()
    st.button("View Details", on_click=show_listing_detail, args=(payload,))

    st.write("**Amenities Nearby:**")
    amenity_keys = ["train", "bus", "primary_school", "hawker", "mall", "polyclinic"]

    for amen in amenity_keys:
        score_col = f"walk_acc_{amen}"      # from stage3_score in recommender.py
        dist_col  = f"walk_{amen}_avg_mins" # display avg walking time

        distance = top.get(dist_col, None)
        score    = top.get(score_col, None)
        if distance is not None and score is not None:
            if score >= 0.8:
                closeness = "Very close"
            elif score >= 0.6:
                closeness = "Close"
            elif score >= 0.4:
                closeness = "Moderate"
            else:
                closeness = "Far"

            st.write(f"• {AMENITY_LABELS[amen]}: {closeness} ({float(distance):.0f} min walk, score: {float(score)*100:.0f}/100)")

        