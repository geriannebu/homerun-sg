import io
import json
import joblib
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
from catboost import CatBoostRegressor, Pool

# Set relative file paths 
_BASE = Path(__file__).parent.parent
_FEATURE_DF_PATH = _BASE / "csv_outputs" / "feature_df_raw.zip"
_RPI_CSV_PATH = _BASE.parent / "datasets" / "HDBResalePriceIndex1Q2009100Quarterly.csv"
_MODEL_DIR = _BASE / "models"
_CI_OFFSETS_PATH = _BASE / "json_outputs" / "ci_offsets.json"

# Constants
SELECTED_MODEL = "ensemble_equal"  # lgbm/xgb/cb/ensemble/ensemble_equal
ENSEMBLE_WEIGHTS = None
RPI_BASE = 100.0

FEATURES = [
    "town", "flat_type", "floor_area_sqm", "lease_commence_date",
    "remaining_lease", "lat", "lon",
    "mall_1_dist_m", "mall_2_dist_m", "mall_3_dist_m",
    "school_1_dist_m", "school_2_dist_m", "school_3_dist_m",
    "hawker_1_dist_m", "hawker_2_dist_m", "hawker_3_dist_m",
    "polyclinic_1_dist_m", "polyclinic_2_dist_m", "polyclinic_3_dist_m",
    "supermarket_1_dist_m", "supermarket_2_dist_m", "supermarket_3_dist_m",
    "train_1_dist_m", "train_2_dist_m", "train_3_dist_m",
    "bus_1_dist_m", "bus_2_dist_m", "bus_3_dist_m",
    "storey_midpoint",
    "num_mrt_within_1km", "flag_mrt_within_500m",
    "num_primary_schools_within_1km", "num_hawkers_within_500m",
    "num_bus_within_400m",
    "dist_cbd",
    "month_index"
]

# Columns that will be imputed from (town, flat_type) group medians
_MEDIAN_COLS = [
    "lat", "lon",
    "mall_1_dist_m", "mall_2_dist_m", "mall_3_dist_m",
    "school_1_dist_m", "school_2_dist_m", "school_3_dist_m",
    "hawker_1_dist_m", "hawker_2_dist_m", "hawker_3_dist_m",
    "polyclinic_1_dist_m", "polyclinic_2_dist_m", "polyclinic_3_dist_m",
    "supermarket_1_dist_m", "supermarket_2_dist_m", "supermarket_3_dist_m",
    "train_1_dist_m", "train_2_dist_m", "train_3_dist_m",
    "bus_1_dist_m", "bus_2_dist_m", "bus_3_dist_m",
    "num_mrt_within_1km", "flag_mrt_within_500m",
    "num_primary_schools_within_1km", "num_hawkers_within_500m",
    "num_bus_within_400m",
    "dist_cbd"
]

# Initialisation helper functions
def _get_group_medians(df):
    df = df.copy()
    df["town"] = df["town"].str.upper().str.strip()
    df["flat_type"] = df["flat_type"].str.upper().str.strip()
    median_cols = [c for c in _MEDIAN_COLS if c in df.columns]
    group_medians = df.groupby(["town", "flat_type"])[median_cols].median().to_dict(orient="index")
    print(f"{len(group_medians)} town–flat_type entries loaded")
    return group_medians

def _compute_rpi_current(df_rpi):
    df_rpi = df_rpi.copy()
    df_rpi.rename(columns={"index": "rpi"}, inplace=True)
    df_rpi["rpi"] = pd.to_numeric(df_rpi["rpi"])
    df_rpi.loc[len(df_rpi)] = {"quarter": "2026-Q1", "rpi": 203.4} # flash estimate from HDB for 2026-Q1

    today = pd.Timestamp.today()
    current_quarter = f"{today.year}-Q{((today.month - 1) // 3) + 1}"

    if current_quarter not in df_rpi["quarter"].values:
        print(f"Current quarter {current_quarter} not in RPI data. Extrapolating...")
        recent = df_rpi.tail(4).copy().reset_index(drop=True)
        recent["t"] = range(4)
        slope, intercept = np.polyfit(recent["t"], recent["rpi"], deg=1)
        lq = df_rpi["quarter"].iloc[-1]
        lq_year, lq_num = int(lq.split("-Q")[0]), int(lq.split("-Q")[1])
        q_year, q_num = int(current_quarter.split("-Q")[0]), int(current_quarter.split("-Q")[1])
        steps = (q_year - lq_year) * 4 + (q_num - lq_num)
        rpi_val = round(intercept + slope * (3 + steps), 1)
        print(f"Extrapolated RPI for {current_quarter}: {rpi_val}")
    else:
        rpi_val = df_rpi.loc[df_rpi["quarter"] == current_quarter, "rpi"].iloc[0]
        print(f"RPI for {current_quarter}: {rpi_val}")

    return float(rpi_val)

def _load_models(model_name):
    models = {}
    if model_name in ("lgbm", "ensemble", "ensemble_equal"):
        print("Loading LightGBM model")
        with zipfile.ZipFile(_MODEL_DIR / "lgb_model.zip") as zf:
            with zf.open("lgb_model.joblib") as f:
                models["lgbm"] = joblib.load(io.BytesIO(f.read()))
    if model_name in ("xgb", "ensemble", "ensemble_equal"):
        print("Loading XGBoost model")
        m = xgb.XGBRegressor()
        m.load_model(str(_MODEL_DIR / "xgb_model.ubj"))
        models["xgb"] = m
    if model_name in ("cb", "ensemble", "ensemble_equal"):
        print("Loading CatBoost model")
        m = CatBoostRegressor()
        m.load_model(str(_MODEL_DIR / "cb_model.cbm"))
        models["cb"] = m
    return models

# Initialisation: will run once upon import
with zipfile.ZipFile(_FEATURE_DF_PATH) as _zf:
    with _zf.open("feature_df_raw.csv") as _f:
        _hist_df = pd.read_csv(_f)

_hist_df = _hist_df[_hist_df["month_index"] < 108] # pre-2026 only
GROUP_MEDIANS = _get_group_medians(_hist_df)

RPI_CURRENT = _compute_rpi_current(pd.read_csv(_RPI_CSV_PATH))

_models = _load_models(SELECTED_MODEL)

with open(_CI_OFFSETS_PATH) as _f:
    _all_offsets = json.load(_f)
_CI_OFFSETS = _all_offsets.get(SELECTED_MODEL) or _all_offsets.get("ensemble_equal")

# Private helper functions
def _predict(models, X):
    cat_cols = ["town", "flat_type"]

    def _cb(X):
        X_cb = X.copy()
        for col in cat_cols:
            X_cb[col] = X_cb[col].astype(str)
        return models["cb"].predict(Pool(X_cb, cat_features=cat_cols))

    if SELECTED_MODEL == "ensemble_equal":
        return np.stack(
            [_cb(X), models["xgb"].predict(X), models["lgbm"].predict(X)], axis=1
        ).mean(axis=1)
    if SELECTED_MODEL == "ensemble":
        w = ENSEMBLE_WEIGHTS if ENSEMBLE_WEIGHTS is not None else np.ones(3) / 3
        return w[0] * _cb(X) + w[1] * models["xgb"].predict(X) + w[2] * models["lgbm"].predict(X)
    if SELECTED_MODEL == "cb":
        return np.array(_cb(X), dtype=float)
    return np.array(models[SELECTED_MODEL].predict(X), dtype=float)

def _build_hypothetical_features(floor_area_sqm, town, flat_type, remaining_lease_years, storey):
    town = town.upper().strip()
    flat_type = flat_type.upper().strip()

    medians = GROUP_MEDIANS.get((town, flat_type))
    if medians is None:
        # Fallback: median across all flat types in the town
        town_keys = {k: v for k, v in GROUP_MEDIANS.items() if k[0] == town}
        if town_keys:
            keys = list(next(iter(town_keys.values())).keys())
            medians = {k: float(np.median([e[k] for e in town_keys.values()])) for k in keys}

    today = pd.Timestamp.today()
    lease_commence_date = today.year - (99 - remaining_lease_years)
    month_index = (today.year - 2017) * 12 + (today.month - 1)

    row = {
        "town": town,
        "flat_type": flat_type,
        "floor_area_sqm": float(floor_area_sqm),
        "lease_commence_date": int(lease_commence_date),
        "remaining_lease": float(remaining_lease_years),
        "storey_midpoint": float(storey),
        "month_index": int(month_index),
    }
    if medians:
        row.update(medians)

    return pd.DataFrame([row])[FEATURES]

# Public API
def predict_hypothetical(floor_area_sqm, town, flat_type, remaining_lease_years, storey):
    """
    Predict the resale price for a hypothetical HDB flat.
    ----------
    INPUT PARAMETERS
    floor_area_sqm: float
    town: str (eg. "WOODLANDS")
    flat_type: str (eg. "EXECUTIVE")
    remaining_lease_years: int
    storey: int
    ----------
    OUTPUT
    dict with keys:
        predicted_price, confidence_low, confidence_high,
        town, flat_type, floor_area_sqm, remaining_lease, storey
    """
    X = _build_hypothetical_features(floor_area_sqm, town, flat_type, remaining_lease_years, storey)
    for col in ["town", "flat_type"]:
        X[col] = X[col].astype("category")

    pred_real = _predict(_models, X)[0]
    pred_nominal = round(pred_real * (RPI_CURRENT / RPI_BASE))

    ci_low = ci_high = None
    if _CI_OFFSETS:
        rpi_factor = RPI_CURRENT / RPI_BASE
        ci_low = round((pred_real + _CI_OFFSETS["p025_real"]) * rpi_factor)
        ci_high = round((pred_real + _CI_OFFSETS["p975_real"]) * rpi_factor)

    return {
        "predicted_price": int(pred_nominal),
        "confidence_low": int(ci_low) if ci_low is not None else None,
        "confidence_high": int(ci_high) if ci_high is not None else None,
        "town": town.upper().strip(),
        "flat_type": flat_type.upper().strip(),
        "floor_area_sqm": float(floor_area_sqm),
        "remaining_lease": int(remaining_lease_years),
        "storey": int(storey)
    }