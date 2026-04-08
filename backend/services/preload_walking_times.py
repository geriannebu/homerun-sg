"""
preload_walking_times.py
========================
One-off data prep script — generates listings_with_walking_times_full.csv.

The output is already committed to the repository. Only re-run this script
if the listings dataset changes.

NOTE: This script requires a OneMap account to obtain API credentials.
Register at https://www.onemap.gov.sg/ and provide your credentials via
the following methods before running:

    Set Environment variables in terminal:
        export ONEMAP_EMAIL="your@email.com"
        export ONEMAP_PASSWORD="yourpassword"


Do NOT hardcode credentials directly in this file.

Usage
-----
    # From repo root:
    python backend/services/preload_walking_times.py

Output
------
    listings_with_walking_times_full.csv.

    Columns added per amenity type (train, bus, hawker, mall,
    supermarket, polyclinic, primary_school):
        walk_{amenity}_min1     — walking minutes to nearest
        walk_{amenity}_min2     — walking minutes to 2nd nearest
        walk_{amenity}_min3     — walking minutes to 3rd nearest
        walk_{amenity}_avg_mins — mean of the above (used by recommender)
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
from sklearn.neighbors import BallTree
from tqdm import tqdm

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Paths (relative to repo root) ─────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # one extra .parent since now 2 levels deep

LISTINGS_PATH = REPO_ROOT / "backend_predictor_listings" / "price_predictor" / "csv_outputs" / "listings_predictions.csv"

AMENITY_DIR = REPO_ROOT / "backend_predictor_listings" / "datasets"

AMENITY_CSV_PATHS = {
    "train":          AMENITY_DIR / "train_station_coords.csv",
    "bus":            AMENITY_DIR / "bus_stop_coords.csv",
    "hawker":         AMENITY_DIR / "hawker_centres_final.csv",
    "mall":           AMENITY_DIR / "sg_malls_final.csv",
    "supermarket":    AMENITY_DIR / "supermarkets_coords_clean.csv",
    "polyclinic":     AMENITY_DIR / "singapore_polyclinics_with_coords.csv",
    "primary_school": AMENITY_DIR / "Generalinformationofschools_with_coords.csv",
}

OUTPUT_PATH = REPO_ROOT / "backend_predictor_listings" / "price_predictor" / "csv_outputs" / "listings_with_walking_times_full.csv"


# ── API Config ─────────────────────────────────────────────────────────────
ONEMAP_AUTH_URL    = "https://www.onemap.gov.sg/api/auth/post/getToken"
ONEMAP_ROUTING_URL = "https://www.onemap.gov.sg/api/public/routingsvc/route"
REQUEST_TIMEOUT    = 15
MAX_RETRIES        = 4
RETRY_DELAY        = 1.2
POLITE_SLEEP       = 0.15
BATCH_SAVE_EVERY   = 50
N_THREADS          = 5
K_NEAREST          = 3

# ── Shared state (thread-safe) ─────────────────────────────────────────────
_cache_lock  = threading.Lock()
_route_cache: dict = {}

_save_lock   = threading.Lock()
_records     = []


# ── Credentials ────────────────────────────────────────────────────────────

def _get_credentials() -> tuple[str, str]:
    """
    Read OneMap credentials. Checks in order:
      1. Environment variables (ONEMAP_EMAIL, ONEMAP_PASSWORD)
      2. Streamlit secrets (.streamlit/secrets.toml) if streamlit is importable
    Raises RuntimeError if neither source has the credentials.
    """
    email    = os.environ.get("ONEMAP_EMAIL")
    password = os.environ.get("ONEMAP_PASSWORD")

    if not email or not password:
        try:
            import streamlit as st
            email    = st.secrets.get("ONEMAP_EMAIL")
            password = st.secrets.get("ONEMAP_PASSWORD")
        except Exception:
            pass

    if not email or not password:
        raise RuntimeError(
            "OneMap credentials not found.\n"
            "Set ONEMAP_EMAIL and ONEMAP_PASSWORD in .streamlit/secrets.toml "
            "or as environment variables before running this script."
        )
    return email, password


# ── Helpers ────────────────────────────────────────────────────────────────

def _std_latlon(df: pd.DataFrame, name: str = "") -> pd.DataFrame:
    """Standardise lat/lon column names to 'lat' and 'lon'."""
    lat_opts = ["lat", "latitude"]
    lon_opts = ["lon", "lng", "long", "longitude"]
    cols     = {c.lower().strip(): c for c in df.columns}
    lat_col  = next((cols[k] for k in lat_opts if k in cols), None)
    lon_col  = next((cols[k] for k in lon_opts if k in cols), None)
    if not lat_col or not lon_col:
        raise ValueError(f"No lat/lon columns found in {name}. Got: {list(df.columns)}")
    out = df.rename(columns={lat_col: "lat", lon_col: "lon"}).copy()
    out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
    out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
    return out.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def get_onemap_token(email: str, password: str) -> Optional[str]:
    try:
        r = requests.post(
            ONEMAP_AUTH_URL,
            json={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        token = r.json().get("access_token")
        if token:
            log.info("OneMap token obtained.")
        return token
    except Exception as e:
        log.error(f"Token fetch failed: {e}")
        return None


def _walk_minutes(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    token: str,
) -> Optional[float]:
    """OneMap walking time in minutes, thread-safe cache + retries."""
    key = (round(lat1, 6), round(lon1, 6), round(lat2, 6), round(lon2, 6))

    with _cache_lock:
        if key in _route_cache:
            return _route_cache[key]

    url = (
        f"{ONEMAP_ROUTING_URL}"
        f"?start={lat1},{lon1}&end={lat2},{lon2}&routeType=walk"
    )
    headers = {"Authorization": f"Bearer {token}"}

    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            secs   = r.json().get("route_summary", {}).get("total_time")
            result = float(secs) / 60.0 if secs is not None else None
            with _cache_lock:
                _route_cache[key] = result
            time.sleep(POLITE_SLEEP)
            return result
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                with _cache_lock:
                    _route_cache[key] = None
                return None


def _nearest_k_coords(
    lat: float, lon: float,
    amenity_df: pd.DataFrame,
    tree: BallTree,
    k: int = K_NEAREST,
) -> list:
    """Return list of (lat, lon) for k-nearest amenities via BallTree."""
    pt     = np.radians([[lat, lon]])
    k      = min(k, len(amenity_df))
    _, idx = tree.query(pt, k=k)
    return [
        (float(amenity_df.iloc[i]["lat"]), float(amenity_df.iloc[i]["lon"]))
        for i in idx[0]
    ]


def _save_checkpoint(existing_df: Optional[pd.DataFrame], path: Path) -> None:
    """Merge new records with existing checkpoint and save."""
    with _save_lock:
        new_df = pd.DataFrame(_records)
        if existing_df is not None and not existing_df.empty:
            combined = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined = new_df
        if "_id" in combined.columns:
            combined = combined.drop_duplicates(subset=["_id"])
        combined.to_csv(path, index=False)


def _process_listing(
    listing,
    active_amenities: list,
    amenity_dfs: dict,
    amenity_trees: dict,
    walk_cols: dict,
    token: str,
) -> dict:
    """Compute walking times for all amenities for a single listing."""
    lat, lon = listing["lat"], listing["lon"]
    row = listing.to_dict()

    for amenity in active_amenities:
        coords = _nearest_k_coords(lat, lon, amenity_dfs[amenity], amenity_trees[amenity])
        times  = []
        for i, (a_lat, a_lon) in enumerate(coords):
            t   = _walk_minutes(lat, lon, a_lat, a_lon, token)
            col = walk_cols[amenity]["mins"][i]
            row[col] = round(t, 2) if t is not None else None
            if t is not None:
                times.append(t)

        # Pad any missing slots with None
        for i in range(len(coords), K_NEAREST):
            row[walk_cols[amenity]["mins"][i]] = None

        row[walk_cols[amenity]["avg"]] = (
            round(float(np.mean(times)), 2) if times else None
        )

    return row


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    global _records

    # 1. Credentials
    email, password = _get_credentials()

    # 2. Load all listings (no row limit)
    log.info(f"Loading listings from {LISTINGS_PATH}")
    listings = pd.read_csv(LISTINGS_PATH)
    listings = _std_latlon(listings, name="listings_predictions.csv")

    listings["_id"] = (
        listings.index.astype(str) + "_" +
        listings["lat"].round(6).astype(str) + "_" +
        listings["lon"].round(6).astype(str)
    )
    listings = (
        listings[listings["town"] != "ERROR"]
        .dropna(subset=["lat", "lon"])
        .drop_duplicates(subset=["_id"])
        .reset_index(drop=True)
    )
    log.info(f"  {len(listings)} listings after filtering.")

    # 3. Load amenity CSVs and build BallTrees
    log.info("Loading amenity CSVs...")
    amenity_dfs   = {}
    amenity_trees = {}
    for amenity, path in AMENITY_CSV_PATHS.items():
        if not path.exists():
            log.warning(f"  Missing: {path} — skipping {amenity}")
            continue
        df = _std_latlon(pd.read_csv(path), name=str(path))
        amenity_dfs[amenity]   = df
        amenity_trees[amenity] = BallTree(
            np.radians(df[["lat", "lon"]].values), metric="haversine"
        )
        log.info(f"  {amenity}: {len(df)} locations")

    active_amenities = list(amenity_dfs.keys())

    # 4. Get one token per thread
    log.info(f"Fetching {N_THREADS} OneMap tokens (one per thread)...")
    tokens = []
    for i in range(N_THREADS):
        t = get_onemap_token(email, password)
        if not t:
            raise RuntimeError(f"Could not obtain OneMap token for thread {i}.")
        tokens.append(t)
        time.sleep(0.3)
    log.info(f"  {len(tokens)} tokens ready.")

    # 5. Build output column name map
    walk_cols = {
        amenity: {
            "mins": [f"walk_{amenity}_min{n}" for n in range(1, K_NEAREST + 1)],
            "avg":  f"walk_{amenity}_avg_mins",
        }
        for amenity in active_amenities
    }

    # 6. Resume from checkpoint if it exists
    done_df = None
    if OUTPUT_PATH.exists():
        log.info(f"Checkpoint found at {OUTPUT_PATH}, resuming...")
        done_df = pd.read_csv(OUTPUT_PATH)
        if "_id" in done_df.columns:
            done_ids = set(done_df["_id"].tolist())
            listings = listings[~listings["_id"].isin(done_ids)].reset_index(drop=True)
            log.info(f"  {len(done_ids)} already done, {len(listings)} remaining.")
        else:
            log.warning("  Checkpoint has no _id column — starting fresh.")
            done_df = None

    if listings.empty:
        log.info("All listings already processed. Nothing to do.")
        return

    # 7. Process with ThreadPoolExecutor
    log.info(f"Processing {len(listings)} listings with {N_THREADS} threads...")
    listing_rows = [listings.iloc[i] for i in range(len(listings))]
    pbar = tqdm(total=len(listing_rows), desc="Listings")

    def worker(args):
        idx, listing = args
        token = tokens[idx % N_THREADS]
        row = _process_listing(
            listing, active_amenities, amenity_dfs, amenity_trees, walk_cols, token
        )
        with _save_lock:
            _records.append(row)
            count = len(_records)
        pbar.update(1)
        if count % BATCH_SAVE_EVERY == 0:
            _save_checkpoint(done_df, OUTPUT_PATH)
            log.info(f"  Checkpoint saved ({count} new rows processed)")
        return row

    with ThreadPoolExecutor(max_workers=N_THREADS) as executor:
        futures = [
            executor.submit(worker, (i, row))
            for i, row in enumerate(listing_rows)
        ]
        for f in as_completed(futures):
            f.result()  # surface any exceptions

    pbar.close()

    # 8. Final save
    _save_checkpoint(done_df, OUTPUT_PATH)
    log.info(f"Done. Output saved to {OUTPUT_PATH}")

    # 9. Report None coverage
    result_df      = pd.read_csv(OUTPUT_PATH)
    walk_time_cols = [c for c in result_df.columns if c.startswith("walk_")]
    none_pct       = result_df[walk_time_cols].isna().mean().mean() * 100
    log.info(f"  Total rows: {len(result_df)}")
    log.info(f"  None rate in walk time columns: {none_pct:.2f}%")
    if none_pct > 0:
        log.warning(
            f"  {none_pct:.2f}% None cells — some API calls failed. "
            "Re-run the script to retry (checkpoint resumes automatically)."
        )


if __name__ == "__main__":
    main()
