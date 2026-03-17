"""
pipeline/cluster.py
-------------------
Step 2: Assign a location_id to every sighting row via DBSCAN.

Reads from data/raw/sightings.parquet (master data).
Writes enriched copy to data/analytics/sightings.parquet (app data).

Keeping raw and analytics separate means:
  - raw/  always has clean source data, never modified after ingest
  - analytics/ has the enriched version the app reads
"""

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

EARTH_RADIUS_M      = 6_371_000
DEFAULT_EPS_M       = 10
DEFAULT_MIN_SAMPLES = 1


def build_clusters(
    analytics_dir:   Path,
    source_parquet:  Path = None,
    eps_meters:      float = DEFAULT_EPS_M,
    min_samples:     int   = DEFAULT_MIN_SAMPLES,
) -> None:
    """
    Read raw sightings, cluster, write enriched copy to analytics dir.

    source_parquet: path to raw/sightings.parquet (passed from run.py)
    analytics_dir:  where to write the enriched parquet + clusters.parquet
    """
    if source_parquet is None:
        source_parquet = analytics_dir / "sightings.parquet"

    clusters_path   = analytics_dir / "clusters.parquet"
    analytics_path  = analytics_dir / "sightings.parquet"

    df = pd.read_parquet(source_parquet)

    # Drop any stale cluster columns — safe to run after merge
    df = df.drop(columns=[c for c in ["location_id", "location_label"] if c in df.columns])

    n = len(df)
    print(f"     Clustering {n:,} points at eps={eps_meters}m ...")

    coords_rad = np.radians(df[["lat", "lon"]].values)
    eps_rad    = eps_meters / EARTH_RADIUS_M

    db = DBSCAN(
        eps=eps_rad,
        min_samples=min_samples,
        algorithm="ball_tree",
        metric="haversine",
        n_jobs=-1,
    ).fit(coords_rad)

    labels     = db.labels_.astype(np.int32)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise    = int((labels == -1).sum())
    print(f"     {n_clusters:,} clusters · {n_noise:,} noise points")

    df["location_id"] = labels

    # ── Cluster centroid table ────────────────────────────────────────
    centers = (
        df.groupby("location_id")
        .agg(
            clat=("lat",    "mean"),
            clon=("lon",    "mean"),
            sighting_count=("lat",    "count"),
            target_count=  ("target", "nunique"),
        )
        .reset_index()
        .rename(columns={"clat": "lat", "clon": "lon"})
    )
    centers["location_label"] = (
        "(" + centers["lat"].round(5).astype(str) +
        ", " + centers["lon"].round(5).astype(str) + ")"
    )

    df = df.merge(
        centers[["location_id", "location_label"]],
        on="location_id",
        how="left",
    )

    analytics_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(analytics_path, index=False, compression="snappy")
    centers.to_parquet(clusters_path, index=False, compression="snappy")
    print(f"     Enriched sightings -> {analytics_path}")
    print(f"     {len(centers):,} cluster centroids -> {clusters_path}")