from pathlib import Path
import pandas as pd
import streamlit as st

_CSV_PATH = Path("backend_predictor_listings/price_predictor/csv_outputs/listings_with_walking_times_full.csv")

@st.cache_data
def load_all_data():
    df = pd.read_csv(_CSV_PATH)
    df.columns = df.columns.str.strip()

    # Drop accidental unnamed columns
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed")]

    # Standardise key column names
    df = df.rename(columns={
        "postal": "postal_code",
        "pred_price_lower": "predicted_price_lower",
        "pred_price_upper": "predicted_price_upper",
    })

    # Ensure expected columns exist
    for col in [
        "predicted_price",
        "predicted_price_lower",
        "predicted_price_upper",
        "valuation_pct",
        "median_similar",
        "median_months_back",
        "median_sample_size",
        "median_old",
    ]:
        if col not in df.columns:
            df[col] = float("nan")

    # Standardise text fields
    if "town" in df.columns:
        df["town"] = df["town"].astype(str).str.strip().str.upper()

    if "flat_type" in df.columns:
        df["flat_type"] = df["flat_type"].astype(str).str.strip().str.upper()

    # Numeric coercions
    for col in [
        "floor_area_sqm",
        "lease_commence_date",
        "storey_midpoint",
        "lat",
        "lon",
        "asking_price",
        "predicted_price",
        "predicted_price_lower",
        "predicted_price_upper",
        "valuation_pct",
        "median_similar",
        "median_months_back",
        "median_sample_size",
        "median_old",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # remaining_lease formatting
    if "remaining_lease" in df.columns:
        df["remaining_lease_display"] = df["remaining_lease"]
        df["remaining_lease"] = (
            df["remaining_lease"]
            .astype(str)
            .str.extract(r"(\d+\.?\d*)")[0]
        )
        df["remaining_lease"] = pd.to_numeric(df["remaining_lease"], errors="coerce")
        df["remaining_lease_years"] = df["remaining_lease"]

    # Helper columns used downstream
    df["listing_id"] = df.index.astype(str)

    if "storey_midpoint" in df.columns:
        df["storey_range"] = (
            df["storey_midpoint"]
            .fillna(0)
            .astype(float)
            .round()
            .astype(int)
            .astype(str)
        )
    else:
        df["storey_range"] = ""

    return df, None