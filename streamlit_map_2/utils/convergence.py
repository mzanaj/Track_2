"""
app/utils/convergence.py
------------------------
Convergence detection at interaction time.

The BallTree was built by the pipeline and lives on disk. This module:
  1. Loads it once via @st.cache_resource (persists across reruns)
  2. Queries it when the user clicks Apply
  3. Filters candidates to cross-target pairs within the time window

Algorithm at query time:
  - tree.query_radius(all_coords, r=eps_rad)  → O(n log n + n·k_avg)
  - filter: target_a != target_b              → O(candidates)
  - filter: abs(dt) <= max_minutes            → O(cross_target_candidates)

At 1M rows with 250m radius: ~400ms total.
At 500m radius: ~600ms (more candidates to filter).

The key insight: the expensive part (building the tree) is done once in
the pipeline. The cheap part (querying it) is what happens on slider Apply.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.neighbors import BallTree

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT           = Path(__file__).resolve().parent.parent
DATA_ANALYTICS = ROOT / "data" / "analytics"


@st.cache_resource
def _load_tree() -> tuple[BallTree, pd.DataFrame]:
    """
    Load the BallTree and its row metadata from disk.
    Called once per session; ~0.8s on first load.
    Returns (tree, meta_df) where meta_df maps row_idx → target/last_seen/lat/lon.
    """
    tree_path = DATA_ANALYTICS / "spatial_index.joblib"
    meta_path = DATA_ANALYTICS / "spatial_index_meta.parquet"

    if not tree_path.exists() or not meta_path.exists():
        return None, None

    tree = joblib.load(tree_path)
    meta = pd.read_parquet(meta_path)
    meta["last_seen"] = pd.to_datetime(meta["last_seen"])
    return tree, meta


def get_convergences(
    max_meters:  float,
    max_minutes: float,
) -> pd.DataFrame:
    """
    Find all convergence events within the given spatial + temporal bounds.

    Returns a DataFrame with columns:
        target_a, target_b, time_a, time_b,
        dt_minutes, distance_m, lat, lon

    Empty DataFrame if no events found or index not available.
    """
    with st.spinner("Searching for convergences..."):
        tree, meta = _load_tree()

    if tree is None:
        st.warning("Spatial index not found. Run the pipeline first.")
        return pd.DataFrame()

    EARTH_R   = 6_371_000.0
    eps_rad   = max_meters / EARTH_R

    # ── Coordinate array in radians (same order as pipeline built it) ─────────
    coords_rad = np.radians(meta[["lat", "lon"]].values)

    # ── Radius query: returns list-of-arrays, one per point ───────────────────
    # Each element is an array of row indices within eps_rad of that point
    with st.spinner("Searching for convergences..."):
        neighbor_indices = tree.query_radius(coords_rad, r=eps_rad)

    # ── Build candidate pairs ─────────────────────────────────────────────────
    targets   = meta["target"].values
    times     = meta["last_seen"].values   # numpy datetime64
    lats      = meta["lat"].values
    lons      = meta["lon"].values

    events = []
    seen   = set()   # deduplicate (i, j) and (j, i)

    max_td = np.timedelta64(int(max_minutes * 60), "s")

    for i, neighbors in enumerate(neighbor_indices):
        t_i = targets[i]
        ts_i = times[i]

        for j in neighbors:
            if j <= i:
                continue                  # skip self and already-seen pairs
            if targets[j] == t_i:
                continue                  # same target — not a convergence

            pair = (min(i, j), max(i, j))
            if pair in seen:
                continue
            seen.add(pair)

            # Time filter
            dt = abs(times[j] - ts_i)
            if dt > max_td:
                continue

            dt_min = float(dt / np.timedelta64(1, "s")) / 60.0
            dist_m = _haversine(lats[i], lons[i], lats[j], lons[j])

            events.append({
                "target_a":   int(t_i),
                "target_b":   int(targets[j]),
                "time_a":     pd.Timestamp(ts_i),
                "time_b":     pd.Timestamp(times[j]),
                "dt_minutes": round(dt_min, 1),
                "distance_m": round(dist_m, 1),
                "lat":        round((lats[i] + lats[j]) / 2, 6),
                "lon":        round((lons[i] + lons[j]) / 2, 6),
            })

    if not events:
        return pd.DataFrame(columns=[
            "target_a", "target_b", "time_a", "time_b",
            "dt_minutes", "distance_m", "lat", "lon"
        ])

    return (
        pd.DataFrame(events)
        .sort_values("dt_minutes")
        .reset_index(drop=True)
    )


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R    = 6_371_000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a    = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))
