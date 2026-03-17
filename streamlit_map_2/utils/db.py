"""
app/utils/db.py
---------------
Single DuckDB connection for the entire Streamlit session.

Uses @st.cache_resource — the connection is created once, shared across
all reruns, never serialised. This is correct for DuckDB; @st.cache_data
would try to pickle the connection object and fail.

All pre-computed Parquet files are registered as DuckDB views on first
connection. Queries throughout the app use this connection exclusively.

Usage:
    from app.utils.db import get_db, query

    df = query("SELECT * FROM dwell WHERE target = ?", [1147])
    con = get_db()   # if you need the raw connection
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import streamlit as st

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT           = Path(__file__).resolve().parent.parent
DATA_ANALYTICS = ROOT / "data" / "analytics"

# ── Parquet files to register as views ───────────────────────────────────────
_VIEWS = {
    "sightings":   "sightings.parquet",
    "clusters":    "clusters.parquet",
    "dwell":       "dwell.parquet",
    "routines":    "routines.parquet",
    "home_ranges": "home_ranges.parquet",
    "index_meta":  "spatial_index_meta.parquet",
}


@st.cache_resource
def get_db() -> duckdb.DuckDBPyConnection:
    """
    Create and cache the DuckDB connection.
    Registers all analytics Parquet files as views.
    Called once per session; subsequent calls return the cached connection.

    Uses forward-slash paths for DuckDB — required on Windows because
    DuckDB does not accept backslash-separated paths inside SQL strings.
    """
    con = duckdb.connect(database=":memory:")
    _register_views(con)
    return con


def _register_views(con: duckdb.DuckDBPyConnection) -> None:
    """
    Register all Parquet files as DuckDB views.
    Called on connection creation. Also callable manually to refresh
    after a pipeline run without restarting Streamlit.

    Uses as_posix() to produce forward-slash paths — DuckDB requires
    this on Windows; backslashes in SQL strings cause parse errors.
    """
    missing = []
    for view_name, filename in _VIEWS.items():
        path = DATA_ANALYTICS / filename
        if path.exists():
            # Drop existing view first (safe re-register after pipeline runs)
            try:
                con.execute(f"DROP VIEW IF EXISTS {view_name}")
            except Exception:
                pass
            # as_posix() -> forward slashes, required by DuckDB on Windows
            con.execute(
                f"CREATE VIEW {view_name} AS "
                f"SELECT * FROM read_parquet('{path.as_posix()}')"
            )
        else:
            missing.append(filename)

    if missing:
        st.warning(
            f"Pipeline output missing: {', '.join(missing)}. "
            f"Run `python -m pipeline.run` to build analytics tables."
        )


def query(sql: str, params: list[Any] | None = None) -> pd.DataFrame:
    """
    Execute a SQL query and return a pandas DataFrame.
    Automatically coerces numpy scalar types to native Python —
    DuckDB cannot bind numpy.int64 etc. as parameters.
    """
    con = get_db()
    if params:
        return con.execute(sql, _coerce_params(params)).df()
    return con.execute(sql).df()


def _coerce_params(params: list[Any]) -> list[Any]:
    """Convert numpy scalars to native Python types recursively."""
    import numpy as np

    def _coerce(v: Any) -> Any:
        if isinstance(v, list):
            return [_coerce(x) for x in v]
        if isinstance(v, np.integer):
            return int(v)
        if isinstance(v, np.floating):
            return float(v)
        if isinstance(v, np.bool_):
            return bool(v)
        return v

    return [_coerce(p) for p in params]


def get_pipeline_metadata() -> dict | None:
    """
    Read the metadata.json written by the pipeline.
    Returns None if no pipeline has been run yet.
    Used to display "Analytics built: X days ago" in the UI header.
    """
    meta_path = DATA_ANALYTICS / "metadata.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except Exception:
        return None


def pipeline_age_label() -> str:
    """
    Human-readable label for how old the pipeline output is.
    e.g. "Analytics built 2 days ago (1,047,293 rows)"
    """
    meta = get_pipeline_metadata()
    if not meta:
        return "No pipeline data — run `python pipeline/run.py`"

    built_at = datetime.fromisoformat(meta["built_at"])
    now      = datetime.now(timezone.utc)
    delta    = now - built_at
    days     = delta.days
    hours    = delta.seconds // 3600

    if days == 0 and hours == 0:
        age = "just now"
    elif days == 0:
        age = f"{hours}h ago"
    elif days == 1:
        age = "1 day ago"
    else:
        age = f"{days} days ago"

    row_count = meta.get("row_count", 0)
    return f"Analytics built {age}  ·  {row_count:,} rows"