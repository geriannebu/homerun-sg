# Price Prediction Pipeline

This is the README for running the standalone notebooks (`data_preprocessing.ipynb`, `model_training.ipynb` and `predict_current_listings.ipynb`) associated with the modelling process for the price predictor, as well as the on-demand prediction module `predict_hypothetical.py` integrated into the Homerun app.

This pipeline takes raw HDB resale transaction data, enriches it with spatial and amenity features, trains a variety of models (gradient boosting models, random forest etc), and produces price predictions for current listings and hypothetical flat queries.

---

## Setup

### Python environment

```bash
cd price_prediction/notebooks
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**`requirements.txt`**
```
pandas
numpy
scikit-learn
xgboost
lightgbm
catboost
optuna
scipy
joblib
requests
python-dotenv
matplotlib
```

### Environment variables

Required only for initial geocoding of raw amenity datasets and `data_preprocessing.ipynb` (using OneMap API).

Create `price_prediction/.env`:
```
ONEMAP_EMAIL=your_onemap_email
ONEMAP_PW=your_onemap_password
```

Register a free account at [onemap.gov.sg](https://www.onemap.gov.sg). The API is used to geocode (i) the raw amenity datasets, (ii) the small number of HDB blocks with missing coordinates in the amenity table.

---

## Initial geocoding of raw amenity datasets

We obtained raw amenity data from various sources (shown below) for 7 amenity types, as shown in the table below.

Using these datasets, we queried the OneMap API for each unique entry. This returned the top matching result with the corresponding address fields and coordinates. For each successful query, we extracted the latitude and longitude from the first result returned and appended them to each entry in the raw datasets. After cleaning up the data and column types, the final geocoded datasets were then exported and saved to .csv format for use in our model training. Links to the respective datasets can be found in the Appendix of this README. 

| Description of Raw Input File | Source | Output CSV File |
|------|--------|-------------|
| MRT/LRT station coordinates and info | data.gov.sg | `train_station_coords.csv` |
| Bus stop coordinates and info | data.gov.sg | `bus_stop_coords.csv` |
| School coordinates and info | data.gov.sg |  `Generalinformationofschools_with_coords.csv` |
| Polyclinic coordinates and info | maps.gov.sg |  `singapore_polyclinics_with_coords.csv` |
| Hawker center coordinates and info | data.gov.sg | `hawker_centres_final.csv` | 
| Supermarket coordinates and info | data.gov.sg |`supermarkets_coords_clean.csv` |
| Shopping mall coordinates and info (**) | Wikipedia | `sg_malls_final.csv` | 

Following that, we pre-computed an amenity table `hdb_amenity_table_full.csv` using the above geocoded amenity datasets and HDB's Property Information dataset, which contains the information of all HDB blocks in Singapore. 

For each block in the raw HDB Property Information dataset, we concatenated `blk_no` and `street` to use as a search value, which was passed into the OneMap API. The top result for each query was taken and its location data (`full_address`, `postal`, `lat`, `lon`) was added to the corresponding row in the raw dataset. 

We then loaded the 7 amenity datasets and built a BallTree on each amenity dataset's coordinates. For each geocoded HDB block, all 7 BallTrees were queried to get the 3 nearest instances of each amenity type (in terms of haversine distance, in metres). These were then stored as columns in the final output table (eg. `train_1_name`, `train_1_dist_m`). 

(**) *As there is no authoritative source for shopping malls in Singapore, the full list was scraped from Wikipedia and validated via the OneMap API's search function. Shopping malls that did not return a valid OneMap search result were manually checked and their coordinates were input manually.*  

---

## Required datasets

Place all files in `datasets/`.

| File | Source | Description |
|------|--------|-------------|
| `ResaleflatpricesbasedonregistrationdatefromJan2017onwards.csv` | data.gov.sg | HDB resale transactions Jan 2017–present |
| `hdb_amenity_table_full.csv` | Pre-computed | Nearest 3 amenities (haversine distance in metres) per HDB block |
| `HDBResalePriceIndex1Q2009100Quarterly.csv` | data.gov.sg | Quarterly HDB Resale Price Index (base Q1 2009 = 100) |
| `train_station_coords.csv` | data.gov.sg + OneMap | Geocoded MRT/LRT station coordinates |
| `bus_stop_coords.csv` | data.gov.sg | Bus stop coordinates |
| `Generalinformationofschools_with_coords.csv` | data.gov.sg + OneMap | Geocoded school coordinates |
| `singapore_polyclinics_with_coords.csv` | maps.gov.sg | Geocoded polyclinic coordinates |
| `hawker_centres_final.csv` | data.gov.sg | Geocoded hawker centre coordinates |
| `supermarkets_coords_clean.csv` | data.gov.sg + OneMap| Geocoded supermarket coordinates |
| `sg_malls_final.csv` | Wikipedia + OneMap | Geocoded shopping mall coordinates |

---

## Pipeline steps

Run the four steps in order.

---

### Step 1: `notebooks/data_preprocessing.ipynb`

**Purpose:** Merge raw datasets, clean missing values, and engineer all model features.

**Inputs:** All 10 datasets above

**Outputs:**

| File | Description |
|------|-------------|
| `csv_outputs/feature_df.csv` / `.zip` | Full feature table (includes block, street, postal for listings use) |
| `csv_outputs/feature_df_raw.csv` / `.zip` | Prepared for model: `town`/`flat_type` as strings (for LightGBM/XGBoost/CatBoost), with address features dropped |
| `csv_outputs/feature_df_enc.csv` / `.zip` | Prepared for model: `town`/`flat_type` label-encoded (for Random Forest), with address features dropped |

#### Data cleaning
- Left-join HDB transactions to the amenity table on `block` + `street_name` to get pre-computed nearest-3 distances
- Impute 2 rows with `postal == "NIL"` via manual lookup
- For any rows still missing amenity distances: geocode the block address via OneMap API to get lat/lon, then recompute haversine distances to all 7 amenity types
- Standardise column types: `month` → datetime, `postal` → nullable Int64, `town`/`flat_type`/`flat_model` → category

#### Feature engineering

| Feature | Description |
|---------|-------------|
| `storey_midpoint` | Parse `storey_range` string (e.g. "07 TO 09") → `(start + end) / 2` |
| `remaining_lease` | Parse string (e.g. "70 years 3 months") → decimal years |
| `{amenity}_{1,2,3}_dist_m` | Distance (m) to nearest 3 of each amenity type: malls, schools, hawker centres, polyclinics, supermarkets, MRT stations, bus stops (21 columns total) |
| `num_mrt_within_1km` | Count of MRT/LRT stations within 1 km |
| `flag_mrt_within_500m` | 1 if any MRT/LRT station within 500 m |
| `num_primary_schools_within_1km` | Count of primary schools within 1 km |
| `num_hawkers_within_500m` | Count of hawker centres within 500 m |
| `num_bus_within_400m` | Count of bus stops within 400 m |
| `dist_cbd` | Haversine distance (m) to Raffles Place MRT (CBD proxy) |
| `real_price` | Nominal resale price deflated by quarterly RPI: `resale_price / rpi * 100` |
| `month_index` | Months since Jan 2017 (0-based integer; Jan 2017 = 0, Jan 2026 = 108) |

Count features computed using BallTree (bus stops) or vectorised haversine (all others).

---

### Step 2: `notebooks/model_training.ipynb`

**Purpose:** Train and evaluate models; save final models and confidence interval offsets.

**Inputs:** `csv_outputs/feature_df_raw.zip`, `csv_outputs/feature_df_enc.zip`

**Outputs:**

| File | Description |
|------|-------------|
| `models/lgb_model.zip` | Trained LightGBM model |
| `models/xgb_model.ubj` | Trained XGBoost model |
| `models/cb_model.cbm` | Trained CatBoost model |
| `models/ensemble_weights_equal.npy` | Equal ensemble weights (1/3 each) |
| `models/ensemble_weights_bg.npy` | Bates-Granger ensemble weights |
| `models/ensemble_weights_gr.npy` | Granger-Ramanathan ensemble weights |
| `json_outputs/ci_offsets.json` | 95% CI offsets for each model |

#### Modelling approach

**Train/val/test split (temporal):**

- Train: Jan 2017 - Dec 2022

- Validation: Jan 2023 - Dec 2023

- Test: Jan 2024 - Dec 2025

- Listings (held out, not used in model training): Jan 2026 onwards

**Loss function:** Asymmetric Lin-Lin (pinball loss) with α = 0.75, which penalises under-predictions 3× more than over-predictions. This is appropriate for buyers who prefer conservative (lower) estimates.

**Models trained:**

| Model | Loss | Notes |
|-------|------|-------|
| LightGBM | Lin-Lin (α = 0.75) | Natively supports categorical features |
| XGBoost | Lin-Lin (α = 0.75) | Natively supports categorical features |
| CatBoost | Lin-Lin (α = 0.75) | Natively supports categorical features |
| Random Forest | MSE | Symmetric baseline, requires label-encoded features |
| Linear Regression | MSE | Symmetric baseline |

**Hyperparameter tuning:** Optuna with 15 trials using TPE sampler, medianPruner and early stopping after 75 rounds.

**Ensemble methods:**

| Name | Method |
|------|--------|
| `ensemble_equal` | Equal weights (1/3 each) |
| `ensemble_bg` | Bates-Granger: weights ∝ 1/MSE of val-set errors |
| `ensemble_gr` | Granger-Ramanathan: minimises Lin-Lin loss on val set |

**Confidence intervals:** 2.5th and 97.5th percentiles of `(actual − predicted)` on the test set, stored as offsets in `ci_offsets.json` and applied at prediction time.

**`SELECTED_MODEL`** constant (default: `"ensemble_equal"`) controls which model is used throughout. Valid values: `lgbm`, `xgb`, `cb`, `ensemble_equal`, `ensemble_bg`, `ensemble_gr`.

---

### Step 3: `notebooks/predict_current_listings.ipynb`

**Purpose:** Generate price predictions for all 2026 HDB listings. This is used to generate precomputed price predictions for listings shown in our app interface.  

**Inputs:** `csv_outputs/feature_df.zip`, `models/`, `json_outputs/ci_offsets.json`, raw HDB resale CSV (for recent median calculation)

**Outputs:**

| File | Description |
|------|-------------|
| `json_outputs/listings_predictions.json` | Prediction records (JSON) |
| `csv_outputs/listings_predictions.csv` | Prediction records (CSV) with more features |

Each record includes:

| Field | Description |
|-------|-------------|
| `predicted_price` | Model prediction converted to nominal SGD |
| `predicted_price_lower/upper` | 95% confidence interval bounds |
| `asking_price` | Actual transacted price (treated as asking price) |
| `valuation_pct` | `(asking - predicted) / predicted × 100` |
| `median_similar` | Recent median resale price for same town × flat_type |
| `median_months_back` | How many months back the median window extends |
| `median_old` | `True` if window had to extend beyond 12 months |

The recent median uses a 6-month window (relative to Dec 2025). If fewer than 20 transactions exist, the window expands until 20 are found.

---

### Step 4: `notebooks/predict_hypothetical.py`

**Purpose:** Importable module for on-demand predictions for user-customised hypothetical flats. This is used to power the Explore tab in our app interface.

**Inputs:** `csv_outputs/feature_df_raw.zip`, `models/`, `json_outputs/ci_offsets.json`, RPI CSV (all loaded once at import)

**Usage:**
```python
from price_prediction.notebooks.predict_hypothetical import predict_hypothetical

result = predict_hypothetical(
    floor_area_sqm=90,
    town="WOODLANDS",
    flat_type="4 ROOM",
    remaining_lease_years=70,
    storey=10
)

# Returns:
# {
#   "predicted_price": 650000,
#   "confidence_low": 560000,
#   "confidence_high": 695000,
#   "town": "WOODLANDS",
#   "flat_type": "4 ROOM",
#   "floor_area_sqm": 90.0,
#   "remaining_lease": 70,
#   "storey": 10
# }
```

Spatial features (lat/lon, amenity distances, count features) are imputed from group medians of historical transactions for the same `(town, flat_type)` pair. If no exact match exists, medians across all flat types in the town are used as a fallback.

For block-specific predictions (e.g. when exact address is available), use `predict_with_spatial_overrides()` and pass the actual values:
```python
from price_prediction.notebooks.predict_hypothetical import predict_with_spatial_overrides

result = predict_with_spatial_overrides(
    floor_area_sqm=90, town="WOODLANDS", flat_type="4 ROOM",
    remaining_lease_years=70, storey=10,
    spatial_features={"lat": 1.4382, "lon": 103.7890, "dist_cbd": 22000.0}
)
```

---

## Summary of output files

| File | Produced by | Description |
|------|-------------|-------------|
| `csv_outputs/feature_df*.csv/.zip` | data_preprocessing | Cleaned feature tables |
| `models/*.cbm / .ubj / .zip / .npy` | model_training | Trained models + obtained ensemble weights |
| `json_outputs/ci_offsets.json` | model_training | 95% CI offsets for each model |
| `json_outputs/listings_predictions.json` | predict_current_listings | Predictions for 2026 listings |
| `csv_outputs/listings_predictions.csv` | predict_current_listings | Predictions for 2026 listings, with spatial features |

---

## Appendix 

References

1. Housing & Development Board. (2026). *Resale flat prices based on registration date from Jan-2017 onwards* [Data set]. <https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view>

2. Housing & Development Board. (2026). *HDB Resale Price Index (1Q2009 = 100), Quarterly* [Data set]. <https://data.gov.sg/datasets/d_14f63e595975691e7c24a27ae4c07c79/view>

3. Housing & Development Board/ (2026). *HDB Property Information* [Data set]. <https://data.gov.sg/datasets/d_17f5382f26140b1fdae0ba2ef6239d2f/view>

4. Land Transport Authority. (2024). *Train Station Chinese Names* [Data set]. <https://data.gov.sg/datasets/d_d312a5b127e1ae74299b8ae664cedd4e/view>

5.  Land Transport Authority. (2026). *LTA Bus Stop* [Data set]. <https://data.gov.sg/datasets/d_3f172c6feb3f4f92a2f47d93eed2908a/view>

6. List of shopping malls in Singapore. (2026). In *Wikipedia*. <https://en.wikipedia.org/wiki/List_of_shopping_malls_in_Singapore>

7. maps.gov.sg. (n.d.) *List of polyclinics in Singapore* [Data set]. <https://maps.gov.sg/polyclinics-singapore>

8. Ministry of Education. (2025). *General Information of Schools* [Data set].  <https://data.gov.sg/datasets/d_688b934f82c1059ed0a6993d2a829089/view>

9. National Environment Agency. (2026). *Hawker Centres (GEOJSON)* [Data set]. <https://data.gov.sg/datasets/d_4a086da0a5553be1d89383cd90d07ecd/view>

10. Singapore Food Agency. (2024). *Supermarkets (GEOJSON)* [Data set]. <https://data.gov.sg/datasets/d_cac2c32f01960a3ad7202a99c27268a0/view>


