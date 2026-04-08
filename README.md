# HomeRun SG

HomeRun SG is a Streamlit application for discovering HDB resale flats in Singapore, with a swipe-based recommendation deck as its main experience. Pricing, comparison, and Explorer workflows support that core decision journey with fair-value estimates, deeper flat lookup, and shortlist review tools.

## Core Product Areas

- `Discover`: the main product surface, where users swipe through recommended listings ranked from their saved preferences
- `Saved`: a supporting shortlist for flats kept from Discover and Explore
- `Compare`: a supporting decision tool for side-by-side review of shortlisted listings
- `Explore`: a supporting research tool for block lookup and hypothetical flat pricing
- `Account`: preferences, onboarding state, and search history management

## Architecture Overview

```text
app.py
  -> frontend/components/onboarding.py
  -> backend/services/predictor_service.py
      -> backend/services/recommender.py
      -> backend/services/recommendation_service.py
      -> data/load_data.py
  -> backend/services/map_service.py
  -> frontend/pages/flat_outputs/best_matches.py
  -> frontend/pages/saved.py
  -> frontend/pages/comparison_tool.py
  -> frontend/pages/explore.py
  -> frontend/pages/account.py
```

## Repository Layout

Only the most important runtime files are listed below.

```text
app.py                                     Streamlit entry point and page routing
requirements.txt                           Python dependencies
Dockerfile                                 Container build

frontend/
  components/
    onboarding.py                          Onboarding flow and preference-to-input mapping
    listing_detail.py                      Listing detail modal
  pages/
    explore.py                             Explorer tab UI and prediction flows
    saved.py                               Saved flats page
    comparison_tool.py                     Comparison page
    account.py                             Account, auth-adjacent UI, preferences, history
    flat_outputs/
      best_matches.py                      Discover swipe deck and recommendation cards
  state/
    session.py                             Streamlit session state helpers
    user_store.py                          Lightweight persisted account store
  styles/
    css.py                                 Global styling injection

backend/
  schemas/
    inputs.py                              Shared `UserInputs` dataclass
  services/
    predictor_service.py                   Builds recommendation and pricing bundles
    recommender.py                         Main listing ranking logic
    recommendation_service.py              Town recommendation helpers
    quiz.py                                Quiz scoring and ranking logic
    map_service.py                         Map bundle helpers used by current UI
  utils/
    constants.py                           Domain constants and labels
    formatters.py                          Currency and badge formatting helpers

data/
  load_data.py                             Cached loading and normalization of listing data

backend_predictor_listings/
  price_predictor/
    notebooks/
      predict_hypothetical.py              Runtime prediction API used by Explore
    csv_outputs/
      feature_df.csv                       Historical transaction feature table
      listings_with_walking_times_full.csv Active listings feature table used by app
    json_outputs/
      ci_offsets.json                      Confidence interval offsets
```

## Main Runtime Files

### Entry point
- [app.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/app.py)
  - initializes session state and persisted user state
  - handles auth gating, onboarding gating, and page routing
  - routes users into Discover as the primary post-onboarding experience
  - orchestrates prediction and map bundle creation

### Frontend
- [frontend/pages/flat_outputs/best_matches.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/frontend/pages/flat_outputs/best_matches.py)
  - primary Discover deck rendering
  - match explanations and swipe interactions
  - main decision surface for recommended flats
- [frontend/components/onboarding.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/frontend/components/onboarding.py)
  - onboarding UI
  - preference persistence and restore helpers
  - conversion from saved preferences into `UserInputs`
- [frontend/pages/explore.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/frontend/pages/explore.py)
  - block lookup flow
  - hypothetical pricing flow
  - transaction table display and save-from-Explorer flow
- [frontend/pages/saved.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/frontend/pages/saved.py)
  - saved flat cards
  - saved map view
  - compare selection state
- [frontend/pages/comparison_tool.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/frontend/pages/comparison_tool.py)
  - side-by-side comparison and scoring summaries
- [frontend/pages/account.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/frontend/pages/account.py)
  - account page layout
  - preference editing and history replay

### Backend
- [backend/services/predictor_service.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/backend/services/predictor_service.py)
  - builds the recommendation bundle used by Discover
- [backend/services/recommender.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/backend/services/recommender.py)
  - core amenity and value scoring pipeline for active listings
- [backend/services/recommendation_service.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/backend/services/recommendation_service.py)
  - town-level recommendation aggregation
- [backend/services/quiz.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/backend/services/quiz.py)
  - amenity ranking workflow and normalized weight generation
- [data/load_data.py](/Users/geriannebu/Library/Mobile%20Documents/com~apple~CloudDocs/Y3S2/DSE3101/homerun-sg/data/load_data.py)
  - cached data loading for active listings and historical transactions

## Data and Models

### Active app datasets
- `backend_predictor_listings/price_predictor/csv_outputs/listings_with_walking_times_full.csv`
  - active listings and engineered features used by the recommendation flow
- `backend_predictor_listings/price_predictor/csv_outputs/feature_df.csv`
  - historical transaction features used by Explore block lookup and pricing
- `backend_predictor_listings/price_predictor/json_outputs/ci_offsets.json`
  - confidence interval offsets for model output display

### Prediction runtime
- `backend_predictor_listings/price_predictor/notebooks/predict_hypothetical.py`
  - runtime import used by Explore for both block-specific and hypothetical flat pricing

## Recommendation and Pricing Notes

### Discover ranking
Discover is the primary workflow of the app and uses the recommender pipeline in `backend/services/recommender.py`.

At a high level it combines:
- amenity accessibility scoring
- value scoring against predicted price
- user preference weights from onboarding
- a ranking profile alpha that balances amenity fit vs value
  
### Updating Walking Times
Walking times are precomputed and stored in backend_predictor_listings/price_predictor/csv_outputs/listings_with_walking_times_full.csv. Only regenerate this file if the listings dataset changes.

To refresh, run backend/services/preload_walking_times.py from the repo root. This requires a OneMap account — register at onemap.gov.sg and set your credentials as environment variables before running:
bashexport ONEMAP_EMAIL="your@email.com"
export ONEMAP_PASSWORD="yourpassword"

Then in your terminal, run: python backend/services/preload_walking_times.py
The script supports checkpoint resuming — if interrupted, rerun the same command and it will pick up where it left off.

### Explore pricing
Explore has two pricing modes:
- `Look up a flat`: uses real block-level spatial features from `feature_df.csv`
- `Explore a flat profile`: imputes spatial features from grouped historical medians

## Local Development

### Requirements
- Python 3.12
- macOS only: `libomp` may be required for XGBoost

```bash
brew install libomp
pip install -r requirements.txt
```

### Run locally

```bash
streamlit run app.py
```

### Run with Docker

```bash
docker build -t homerun-sg .
docker run -p 8501:8501 homerun-sg
```

If port `8501` is already in use:

```bash
docker run -p 8502:8501 homerun-sg
```

## Contributing Notes

When changing the app, start with these files in order:
1. `frontend/pages/flat_outputs/best_matches.py`
2. `app.py`
3. `frontend/components/onboarding.py`
4. `backend/services/predictor_service.py`
5. `backend/services/recommender.py`
6. `frontend/pages/explore.py`

This will cover most product, UI, and ranking changes without having to scan the whole repository first.
