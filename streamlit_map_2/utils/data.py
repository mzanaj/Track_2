"""
app/utils/data.py
-----------------
Drop-in replacement for the original utils/data.py.

All public function signatures are identical to the original.
What changes is the implementation: DuckDB queries on pre-computed
Parquet instead of pandas/sklearn compute on every call.

CACHING STRATEGY
----------------
@st.cache_resource  — process-level, shared across ALL users and sessions.
                      Use when: the result is identical for every user.
                      Returns the actual object (not a copy) — callers
                      must .copy() before mutating.

@st.cache_data      — per-call, keyed on arguments.
                      Use when: the result varies by user input (sliders,
                      filters). Serialises the return value, so safe to
                      mutate. Slower than cache_resource for large frames.

No cache            — use when: the function is fast (<50ms), or depends
                      on user session state that changes frequently.
"""
from __future__ import annotations
from utils.convergence import get_convergences as _fast
from sklearn.neighbors import BallTree
from utils.db import query, get_db
import streamlit as st
import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════════
# Haversine helpers — no cache, pure math, called inline
# ═══════════════════════════════════════════════════════════════════════════════

def haversine_meters(lat1, lon1, lat2, lon2) -> float:
    R    = 6_371_000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a    = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def haversine_meters_vectorized(lat1, lon1, lat2_series, lon2_series):
    R    = 6_371_000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2_series)
    dphi = np.radians(lat2_series - lat1)
    dlam = np.radians(lon2_series - lon1)
    a    = (np.sin(dphi / 2) ** 2
            + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(a))


# ═══════════════════════════════════════════════════════════════════════════════
# Core data loader
# cache_resource: same rows for every user — load once, share forever
# Callers must .copy() before adding columns or filtering in-place
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_data() -> pd.DataFrame:
    """
    Full sightings table. Shared across all users.
    Returns the live object — callers must .copy() before mutating.
    """
    df = query(
        "SELECT target, lat, lon, last_seen FROM sightings ORDER BY target, last_seen"
    )
    df["last_seen"] = pd.to_datetime(df["last_seen"])
    return df


@st.cache_resource
def get_default_targets(n: int = 10) -> list[int]:
    """
    Returns the top N targets by most recent activity (latest last_seen).

    Used as the default selection across all multiselects in the app.
    Loads instantly — single DuckDB aggregation, result cached for all users.

    Why most recent: analysts want to see who was active lately,
    not who has the most historical records.
    """
    df = query(f"""
        SELECT target, MAX(last_seen) AS latest
        FROM sightings
        GROUP BY target
        ORDER BY latest DESC
        LIMIT {n}
    """)
    return sorted(df["target"].tolist())


# ═══════════════════════════════════════════════════════════════════════════════
# Target summary
# cache_resource: no user-specific arguments — same result for everyone
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_target_summary(_con=None) -> pd.DataFrame:
    """Per-target summary stats. Shared across all users."""
    df = query("""
        SELECT
            target,
            COUNT(*)                        AS total_sightings,
            COUNT(DISTINCT DATE(last_seen)) AS active_days,
            MIN(last_seen)                  AS first_seen,
            MAX(last_seen)                  AS last_seen,
        FROM sightings
        GROUP BY target
        ORDER BY target
    """)
    df["first_seen"] = pd.to_datetime(df["first_seen"])
    df["last_seen"]  = pd.to_datetime(df["last_seen"])

    dist_df = _compute_distances()
    df = df.merge(dist_df, on="target", how="left")
    df["distance_km"] = df["distance_km"].fillna(0.0)

    mfl = query("""
        SELECT target,
               FIRST(location_label ORDER BY visit_count DESC) AS most_frequent_loc,
               MAX(visit_count)                                 AS most_frequent_n
        FROM dwell
        GROUP BY target
    """)
    df = df.merge(mfl, on="target", how="left")
    return df


@st.cache_resource
def _compute_distances() -> pd.DataFrame:
    """
    Total distance traveled per target. Shared across all users.
    Computed in Python (chained haversine) because SQL can't do ordered
    row-by-row distance accumulation cleanly.
    """
    df = query(
        "SELECT target, lat, lon FROM sightings ORDER BY target, last_seen"
    )
    records = []
    for target_id, group in df.groupby("target"):
        coords = group[["lat", "lon"]].values
        if len(coords) < 2:
            records.append({"target": target_id, "distance_km": 0.0})
            continue
        dists = [
            haversine_meters(
                coords[i][0], coords[i][1],
                coords[i+1][0], coords[i+1][1]
            )
            for i in range(len(coords) - 1)
        ]
        records.append({
            "target":      target_id,
            "distance_km": round(sum(dists) / 1000, 2),
        })
    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════════
# Last seen
# cache_resource: same for everyone, no arguments
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_last_seen_table(_con=None) -> pd.DataFrame:
    df = query("""
        SELECT target, last_seen, lat, lon
        FROM sightings
        QUALIFY ROW_NUMBER() OVER (PARTITION BY target ORDER BY last_seen DESC) = 1
        ORDER BY target
    """)
    df["last_seen"] = pd.to_datetime(df["last_seen"])
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Centroid merge — BallTree over cluster centroids
# Used by dwell and routines to make the radius slider genuinely meaningful.
# At ~5K centroids this runs in milliseconds.
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def _build_centroid_merge_map(max_meters: float) -> dict[int, int]:
    """
    Build a mapping from location_id → super_location_id by merging
    cluster centroids that are within max_meters of each other.

    Uses BallTree over the centroid lat/lon values (not raw sightings).
    At 5K centroids this is ~5ms regardless of max_meters.

    Returns: dict mapping each location_id to its super_location_id.
    The super_location_id is the lowest location_id in each merged group,
    so results are stable and deterministic.
    """
    centroids = query(
        "SELECT location_id, lat, lon FROM clusters ORDER BY location_id"
    )
    if centroids.empty:
        return {}

    coords_rad = np.radians(centroids[["lat", "lon"]].values)
    eps_rad    = max_meters / 6_371_000

    tree    = BallTree(coords_rad, metric="haversine")
    indices = tree.query_radius(coords_rad, r=eps_rad)

    ids = centroids["location_id"].values

    # Union-Find to merge overlapping groups
    parent = {loc_id: loc_id for loc_id in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            # Always keep the lower id as root for stability
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    for i, neighbors in enumerate(indices):
        for j in neighbors:
            if i != j:
                union(ids[i], ids[j])

    # Compress: map every id to its root
    return {loc_id: find(loc_id) for loc_id in ids}


# ═══════════════════════════════════════════════════════════════════════════════
# Dwell
# cache_data: result varies by min_visits slider — different per user
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_dwell_locations(
    _df=None,
    min_visits:  int   = 3,
    max_meters:  float = 10,
) -> pd.DataFrame:
    """
    Pre-computed dwell table filtered by min_visits.

    max_meters now works via BallTree centroid merging:
      - Load cluster centroids (~5K rows)
      - Find all centroid pairs within max_meters using BallTree
      - Merge nearby clusters into super-clusters (union-find)
      - Re-aggregate visit counts across merged clusters

    At max_meters=10 (default), each cluster is its own super-cluster —
    identical to the old behavior. At 50m, nearby location clusters are
    merged and their visit counts combined.
    """
    import numpy as np

    # Base dwell data — all locations, unfiltered by radius yet
    result = query(
        """
        SELECT target, location_id, location_label, lat, lon,
               visit_count, first_seen, last_seen
        FROM dwell
        ORDER BY target, visit_count DESC
        """,
    )
    result["first_seen"] = pd.to_datetime(result["first_seen"])
    result["last_seen"]  = pd.to_datetime(result["last_seen"])

    if result.empty:
        return result

    # Build centroid merge map for this radius
    merge_map = _build_centroid_merge_map(float(max_meters))
    if not merge_map:
        return result[result["visit_count"] >= min_visits].copy()

    # Apply merge: assign super_location_id to every row
    result["super_id"] = result["location_id"].map(merge_map).fillna(result["location_id"]).astype(int)

    # Re-aggregate by (target, super_id)
    merged = (
        result
        .groupby(["target", "super_id"])
        .agg(
            location_label=("location_label", "first"),
            lat=("lat",           "mean"),
            lon=("lon",           "mean"),
            visit_count=("visit_count",   "sum"),
            first_seen=("first_seen",    "min"),
            last_seen=("last_seen",     "max"),
        )
        .reset_index()
        .rename(columns={"super_id": "location_id"})
        .sort_values(["target", "visit_count"], ascending=[True, False])
    )

    return merged[merged["visit_count"] >= min_visits].copy()


# ═══════════════════════════════════════════════════════════════════════════════
# Routines
# cache_data: result varies by min_occurrences slider
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_routines(
    _df=None,
    max_meters:      float = 50,
    min_occurrences: int   = 3,
) -> pd.DataFrame:
    """
    Pre-computed routines filtered by min_occurrences.

    max_meters now works via BallTree centroid merging — same mechanism
    as get_dwell_locations. Nearby location clusters are merged before
    aggregating routine counts, so a target appearing at two locations
    50m apart in the same time block counts as one routine.
    """
    # Base routines — unfiltered by radius
    result = query(
        """
        SELECT target, location_id, location_label,
               hour_block, hour_range, dow, occurrences
        FROM routines
        ORDER BY occurrences DESC
        """,
    )

    if result.empty:
        return result

    # Build centroid merge map for this radius
    merge_map = _build_centroid_merge_map(float(max_meters))
    if not merge_map:
        return result[result["occurrences"] >= min_occurrences].copy()

    # Apply merge
    result["super_id"] = result["location_id"].map(merge_map).fillna(result["location_id"]).astype(int)

    # Re-aggregate by (target, super_id, hour_block, dow)
    merged = (
        result
        .groupby(["target", "super_id", "hour_block", "hour_range", "dow"])
        .agg(
            location_label=("location_label", "first"),
            occurrences=("occurrences",    "sum"),
        )
        .reset_index()
        .rename(columns={"super_id": "location_id"})
        .sort_values("occurrences", ascending=False)
    )

    return merged[merged["occurrences"] >= min_occurrences].copy()


# ═══════════════════════════════════════════════════════════════════════════════
# Shared locations
# cache_resource: same for everyone, no user arguments
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_shared_locations_table(_clustered_df=None) -> pd.DataFrame:
    """Locations visited by 2+ distinct targets. Shared across all users."""
    result = query("""
        SELECT
            d.location_id,
            d.location_label,
            COUNT(DISTINCT d.target)  AS target_count,
            COUNT(*)                  AS visit_count,
            MIN(d.first_seen)         AS first_seen,
            MAX(d.last_seen)          AS last_seen
        FROM dwell d
        GROUP BY d.location_id, d.location_label
        HAVING COUNT(DISTINCT d.target) >= 2
        ORDER BY visit_count DESC
    """)

    if result.empty:
        return result

    target_lists = query("""
        SELECT location_id, CAST(target AS VARCHAR) AS target_str
        FROM dwell
        ORDER BY location_id, target
    """)

    tl = (
        target_lists[target_lists["location_id"].isin(result["location_id"])]
        .groupby("location_id")["target_str"]
        .apply(lambda x: ", ".join(f"T{v}" for v in sorted(x)))
        .reset_index()
        .rename(columns={"target_str": "targets"})
    )

    result = result.merge(tl, on="location_id", how="left")
    result["first_seen"] = pd.to_datetime(result["first_seen"])
    result["last_seen"]  = pd.to_datetime(result["last_seen"])
    return result[["location_label", "targets", "visit_count", "first_seen", "last_seen"]]


# ═══════════════════════════════════════════════════════════════════════════════
# Cluster locations — used by network graph
# cache_resource: full sightings with location_id, same for everyone
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def cluster_locations(_df=None, max_meters: float = 10) -> pd.DataFrame:
    """
    Returns sightings with pre-computed location_id.
    max_meters accepted for API compatibility — ignored, clustering
    was fixed at pipeline time.
    """
    result = query(
        "SELECT target, lat, lon, last_seen, location_id, location_label "
        "FROM sightings"
    )
    result["last_seen"] = pd.to_datetime(result["last_seen"])
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Heatmap data
# cache_data: result varies by target filter
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_heatmap_data(_df=None, targets=None) -> pd.DataFrame:
    """
    Lat/lon points for heatmap, optionally filtered by target list.
    Caller passes result to build_heatmap_grid() before rendering.
    """
    if targets:
        targets_clean = [int(t) for t in targets]
        placeholders  = ", ".join("?" * len(targets_clean))
        return query(
            f"SELECT lat, lon, target FROM sightings "
            f"WHERE target IN ({placeholders})",
            targets_clean,
        )
    return query("SELECT lat, lon, target FROM sightings")


# ═══════════════════════════════════════════════════════════════════════════════
# Home range + anomalies
# cache_resource for home range (same for everyone)
# no cache for anomalies (fast, depends on user's sensitivity slider)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_target_home_range(_df=None, decay_rate: float = 0.05) -> dict:
    """
    Pre-computed home ranges. Shared across all users.
    decay_rate accepted for API compatibility — baked in at pipeline time.
    """
    hr_df = query(
        "SELECT target, center_lat, center_lon, mean_dist_m, std_dist_m "
        "FROM home_ranges"
    )
    return {
        row["target"]: {
            "center_lat": row["center_lat"],
            "center_lon": row["center_lon"],
            "mean_dist":  row["mean_dist_m"],
            "std_dist":   row["std_dist_m"],
        }
        for _, row in hr_df.iterrows()
    }


def get_anomalies(_df=None, home_ranges: dict = None, n_std: float = 2.0) -> pd.DataFrame:
    """
    Flag sightings outside each target's normal movement range.
    No cache — fast vectorized compute, depends on n_std slider.
    """
    if not home_ranges:
        return pd.DataFrame()

    df = load_data()
    anomalies = []

    for target, group in df.groupby("target"):
        if target not in home_ranges:
            continue
        hr        = home_ranges[target]
        threshold = hr["mean_dist"] + (n_std * hr["std_dist"])

        group = group.copy()
        group["dist_from_center"] = haversine_meters_vectorized(
            hr["center_lat"], hr["center_lon"],
            group["lat"], group["lon"],
        )
        group["threshold_m"] = round(threshold, 1)
        group["mean_dist_m"] = round(hr["mean_dist"], 1)
        group["std_dist_m"]  = round(hr["std_dist"], 1)

        outside = group[group["dist_from_center"] > threshold].copy()
        outside["target"] = target
        anomalies.append(outside)

    if not anomalies:
        return pd.DataFrame()
    return pd.concat(anomalies).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# IQR box + DBSCAN hulls — home range overlay on map
# cache_data: depends on filtered df and decay_rate slider
# ═══════════════════════════════════════════════════════════════════════════════

def get_iqr_box(df, decay_rate: float = 0.05) -> dict:
    result = {}
    for target, group in df.groupby("target"):
        now_ts   = group["last_seen"].max()
        days_ago = (now_ts - group["last_seen"]).dt.total_seconds() / 86400
        weights  = np.exp(-decay_rate * days_ago)
        repeat_n = (weights * 100).astype(int).clip(lower=1)
        exp_lat  = np.repeat(group["lat"].values,  repeat_n)
        exp_lon  = np.repeat(group["lon"].values,  repeat_n)
        result[target] = {
            "lat_low":  float(np.percentile(exp_lat, 10)),
            "lat_high": float(np.percentile(exp_lat, 90)),
            "lon_low":  float(np.percentile(exp_lon, 10)),
            "lon_high": float(np.percentile(exp_lon, 90)),
        }
    return result


def get_dbscan_hulls(
    df, decay_rate: float = 0.05,
    eps: float = 0.003, min_samples: int = 3,
) -> dict:
    from scipy.spatial import ConvexHull
    from sklearn.cluster import DBSCAN as _DBSCAN

    results = {}
    for target, group in df.groupby("target"):
        now_ts   = group["last_seen"].max()
        days_ago = (now_ts - group["last_seen"]).dt.total_seconds() / 86400
        weights  = np.exp(-decay_rate * days_ago)
        coords   = group[["lat", "lon"]].values
        repeat_n = (weights.values * 100).astype(int).clip(min=1)
        expanded = np.repeat(coords, repeat_n, axis=0)

        db     = _DBSCAN(eps=eps, min_samples=min_samples).fit(expanded)
        labels = db.labels_
        unique, counts = np.unique(labels[labels >= 0], return_counts=True)

        if len(unique) == 0:
            results[target] = None
            continue

        cluster_pts = expanded[labels == unique[np.argmax(counts)]]
        if len(cluster_pts) < 3:
            results[target] = None
            continue

        try:
            hull    = ConvexHull(cluster_pts)
            polygon = cluster_pts[hull.vertices].tolist()
            polygon.append(polygon[0])
            results[target] = polygon
        except Exception:
            results[target] = None

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Convergence — delegated to convergence.py (BallTree query)
# No cache — user-triggered via Apply button, BallTree already cached
# ═══════════════════════════════════════════════════════════════════════════════

def get_convergences(_df=None, max_meters: float = 50, max_minutes: float = 120) -> pd.DataFrame:
    """
    BallTree-based convergence detection.
    df ignored — kept for API compatibility.
    BallTree is cached at process level in convergence.py.
    """
    return _fast(max_meters=max_meters, max_minutes=max_minutes)