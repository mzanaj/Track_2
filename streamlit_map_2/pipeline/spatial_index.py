"""
pipeline/spatial_index.py
--------------------------
Step 4: Build BallTree spatial index over all sightings and serialise to disk.
Build: O(n log n). Query at runtime: O(log n + k). Load time: ~0.8s.
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree


def build_spatial_index(analytics_dir: Path) -> None:
    sightings_path = analytics_dir / "sightings.parquet"
    tree_path      = analytics_dir / "spatial_index.joblib"
    meta_path      = analytics_dir / "spatial_index_meta.parquet"

    df = pd.read_parquet(sightings_path, columns=["target", "lat", "lon", "last_seen"])
    n  = len(df)
    print(f"     Building BallTree over {n:,} points ...")

    coords_rad = np.radians(df[["lat", "lon"]].values)
    tree       = BallTree(coords_rad, metric="haversine", leaf_size=40)

    joblib.dump(tree, tree_path, compress=3)
    tree_size_mb = tree_path.stat().st_size / 1_048_576
    print(f"     BallTree serialised -> {tree_path} ({tree_size_mb:.1f} MB)")

    # Row metadata: maps tree position -> (target, last_seen, lat, lon)
    meta = df.reset_index(drop=True)
    meta.index.name = "row_idx"
    meta = meta.reset_index()
    meta.to_parquet(meta_path, index=False, compression="snappy")
    print(f"     Row metadata -> {meta_path}")
