"""
app/utils/render.py
-------------------
Render-layer helpers. These functions exist for one reason:
the browser has a render budget and 1M raw points will crash it.

The rule: analytics always use full data. Only the visual point cloud
sent to Plotly gets reduced. Intelligence is never lost — just the
pixel density of the map scatter.

Functions:
    downsample_for_map(df, max_points)  → spatially spread sample
    build_heatmap_grid(df, grid_size)   → density grid for Densitymap
    simplify_paths(df, tolerance)       → Douglas-Peucker on trajectories
"""

import numpy as np
import pandas as pd


# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_MAP_POINTS  = 50_000    # max scatter points sent to Plotly
DEFAULT_GRID_SIZE   = 300       # heatmap grid resolution (300×300 cells)


def downsample_for_map(
    df:         pd.DataFrame,
    max_points: int = DEFAULT_MAP_POINTS,
) -> pd.DataFrame:
    """
    Reduce a sightings DataFrame to at most max_points rows for map rendering.

    Uses spatial grid sampling — preserves geographic spread rather than
    random sampling, which would leave dense areas over-represented and
    sparse areas empty.

    Strategy:
      - Round lat/lon to a grid (precision chosen to produce ~max_points cells)
      - Take one representative row per grid cell (first chronologically)

    If df already has <= max_points rows, returns unchanged.
    """
    if len(df) <= max_points:
        return df

    # Choose grid precision so number of cells ≈ max_points
    # At 50K points over DC metro area (~0.5° × 0.5°), 3 decimal places
    # gives cells of ~100m, producing roughly 25K–60K unique cells.
    precision = 3

    sampled = (
        df
        .assign(
            _glat=(df["lat"] * 10 ** precision).round(),
            _glon=(df["lon"] * 10 ** precision).round(),
        )
        .sort_values("last_seen")
        .groupby(["_glat", "_glon"], as_index=False)
        .first()
        .drop(columns=["_glat", "_glon"])
        .reset_index(drop=True)
    )

    # If still over budget (very dense area), random sample the remainder
    if len(sampled) > max_points:
        sampled = sampled.sample(max_points, random_state=42)

    return sampled


def build_heatmap_grid(
    df:        pd.DataFrame,
    grid_size: int = DEFAULT_GRID_SIZE,
) -> pd.DataFrame:
    """
    Aggregate raw sightings into a density grid for Plotly Densitymap.

    Instead of passing 1M points to Plotly (which renders each as a
    separate DOM element), we pre-aggregate into a grid and pass ~90K
    weighted centroid points. The visual output is identical; the
    browser cost drops by ~99%.

    Returns a DataFrame with columns: lat, lon, weight
    where weight is the sighting count in that grid cell.
    """
    if df.empty:
        return df

    lat_min, lat_max = df["lat"].min(), df["lat"].max()
    lon_min, lon_max = df["lon"].min(), df["lon"].max()

    # Assign each sighting to a grid cell
    df = df.copy()
    df["_lat_bin"] = pd.cut(df["lat"], bins=grid_size, labels=False)
    df["_lon_bin"] = pd.cut(df["lon"], bins=grid_size, labels=False)

    grid = (
        df
        .groupby(["_lat_bin", "_lon_bin"], observed=True)
        .agg(
            lat=("lat", "mean"),
            lon=("lon", "mean"),
            weight=("lat",  "count"),
        )
        .reset_index(drop=True)
    )

    return grid


def simplify_paths(
    df:        pd.DataFrame,
    tolerance: float = 0.0001,
    max_per_target: int = 2_000,
) -> pd.DataFrame:
    """
    Reduce path complexity for the Paths tab.

    Two strategies applied in order:
      1. Cap per-target points at max_per_target (chronological head)
      2. Douglas-Peucker simplification on lat/lon sequences

    At 1M rows across 5000 targets, the raw path tab would send millions
    of line segments to Plotly. After simplification, typical result is
    100–400 points per target.

    tolerance: D-P epsilon in degrees (~11m at DC latitude per 0.0001°)
    """
    results = []

    for target_id, group in df.sort_values("last_seen").groupby("target"):
        # Step 1: cap
        if len(group) > max_per_target:
            group = group.head(max_per_target)

        # Step 2: Douglas-Peucker
        pts = group[["lat", "lon"]].values
        if len(pts) > 10:
            mask = _douglas_peucker_mask(pts, tolerance)
            group = group.iloc[mask]

        results.append(group)

    if not results:
        return df

    return pd.concat(results, ignore_index=True)


# ── Douglas-Peucker implementation ─────────────────────────────────────────────

def _douglas_peucker_mask(
    points: np.ndarray,
    epsilon: float,
) -> list[int]:
    """
    Returns indices of points to keep after D-P simplification.
    points: (N, 2) array of [lat, lon]
    epsilon: tolerance in degrees
    """
    if len(points) <= 2:
        return list(range(len(points)))

    def _dp(start: int, end: int) -> list[int]:
        if end <= start + 1:
            return [start, end]

        # Find point with max perpendicular distance from start-end line
        max_dist = 0.0
        max_idx  = start

        p1 = points[start]
        p2 = points[end]

        for i in range(start + 1, end):
            d = _perp_distance(points[i], p1, p2)
            if d > max_dist:
                max_dist = d
                max_idx  = i

        if max_dist > epsilon:
            left  = _dp(start, max_idx)
            right = _dp(max_idx, end)
            return left[:-1] + right
        else:
            return [start, end]

    return _dp(0, len(points) - 1)


def _perp_distance(
    point: np.ndarray,
    line_start: np.ndarray,
    line_end: np.ndarray,
) -> float:
    """Perpendicular distance from point to line (in coordinate units)."""
    if np.allclose(line_start, line_end):
        return float(np.linalg.norm(point - line_start))

    d = line_end - line_start
    n = np.array([-d[1], d[0]])
    n = n / np.linalg.norm(n)
    return float(abs(np.dot(point - line_start, n)))
