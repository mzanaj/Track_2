"""
pipeline/derived.py
-------------------
Step 3: Build dwell, routines, and home_ranges tables from clustered sightings.
All three read location_id — never recluster. Runs in parallel via ThreadPoolExecutor.
"""

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

HOUR_BLOCK_SIZE = 2
DECAY_RATE      = 0.05


def build_derived_tables(analytics_dir: Path) -> None:
    df = pd.read_parquet(analytics_dir / "sightings.parquet")

    tasks = {
        "dwell":       lambda: _build_dwell(df, analytics_dir),
        "routines":    lambda: _build_routines(df, analytics_dir),
        "home_ranges": lambda: _build_home_ranges(df, analytics_dir),
    }

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
                print(f"     done: {name}")
            except Exception as e:
                raise RuntimeError(f"Failed to build {name}: {e}") from e


def _build_dwell(df: pd.DataFrame, analytics_dir: Path) -> None:
    dwell = (
        df.groupby(["target", "location_id"])
        .agg(
            location_label=("location_label", "first"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
            visit_count=("last_seen", "count"),
            first_seen=("last_seen", "min"),
            last_seen=("last_seen", "max"),
        )
        .reset_index()
        .sort_values(["target", "visit_count"], ascending=[True, False])
    )
    dwell.to_parquet(analytics_dir / "dwell.parquet", index=False, compression="snappy")


def _build_routines(df: pd.DataFrame, analytics_dir: Path) -> None:
    df = df.copy()
    df["hour_block"] = (df["last_seen"].dt.hour // HOUR_BLOCK_SIZE) * HOUR_BLOCK_SIZE
    df["dow"]        = df["last_seen"].dt.strftime("%A")

    routines = (
        df.groupby(["target", "location_id", "location_label", "hour_block", "dow"])
        .size()
        .reset_index(name="occurrences")
        .sort_values("occurrences", ascending=False)
    )
    routines["hour_range"] = routines["hour_block"].apply(
        lambda h: f"{h:02d}:00-{h+HOUR_BLOCK_SIZE:02d}:00"
    )
    routines.to_parquet(analytics_dir / "routines.parquet", index=False, compression="snappy")


def _build_home_ranges(df: pd.DataFrame, analytics_dir: Path) -> None:
    records = []
    now_ts  = df["last_seen"].max()

    for target_id, group in df.groupby("target"):
        lats     = group["lat"].values
        lons     = group["lon"].values
        days_ago = (now_ts - group["last_seen"]).dt.total_seconds().values / 86400
        weights  = np.exp(-DECAY_RATE * days_ago)
        w_sum    = weights.sum()

        c_lat = float(np.dot(weights, lats)  / w_sum)
        c_lon = float(np.dot(weights, lons)  / w_sum)

        dists_m = _haversine_vec(c_lat, c_lon, lats, lons)
        mean_d  = float(np.dot(weights, dists_m) / w_sum)
        var_d   = float(np.dot(weights, (dists_m - mean_d) ** 2) / w_sum)
        std_d   = float(np.sqrt(var_d))

        records.append({
            "target":         int(target_id),
            "center_lat":     round(c_lat, 6),
            "center_lon":     round(c_lon, 6),
            "mean_dist_m":    round(mean_d, 2),
            "std_dist_m":     round(std_d, 2),
            "sighting_count": len(group),
        })

    pd.DataFrame(records).to_parquet(
        analytics_dir / "home_ranges.parquet", index=False, compression="snappy"
    )


def _haversine_vec(lat1, lon1, lat2, lon2):
    R    = 6_371_000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a    = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))
