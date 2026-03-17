"""
pipeline/ingest.py
------------------
Handles all data ingestion modes.

Three modes (called from run.py):

  --incoming  (default / scheduled job)
    - Finds all CSVs in data/incoming/
    - Merges each into data/raw/sightings.parquet
    - Deduplicates on (target, last_seen, lat, lon)
    - Moves processed files to data/processed/YYYY-MM-DD_HH-MM-SS_filename.csv
    - Returns total row count

  --force  (rebuild from existing raw Parquet)
    - Reads data/raw/sightings.parquet as-is
    - Re-runs all pipeline steps on existing data
    - No file movement, no CSV needed
    - Returns existing row count

  --input path/to/file.csv  (explicit single file, legacy / manual use)
    - Reads one specific CSV
    - Merges into raw Parquet
    - Moves to processed/
    - Returns total row count
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"target", "lat", "lon", "last_seen"}
LAT_BOUNDS       = (-90.0,   90.0)
LON_BOUNDS       = (-180.0, 180.0)


# ═══════════════════════════════════════════════════════════════════════
# Public entry points
# ═══════════════════════════════════════════════════════════════════════

def ingest_incoming(
    incoming_dir:  Path,
    raw_dir:       Path,
    processed_dir: Path,
) -> int:
    """
    Process all CSVs in incoming_dir.
    Merge each into raw Parquet, then move to processed_dir.
    Returns total row count after all merges.
    """
    csv_files = sorted(incoming_dir.glob("*.csv"))

    if not csv_files:
        print("     No CSV files found in data/incoming/ — nothing to do.")
        existing_path = raw_dir / "sightings.parquet"
        if existing_path.exists():
            return len(pd.read_parquet(existing_path, columns=["target"]))
        return 0

    print(f"     Found {len(csv_files)} file(s) in incoming/:")
    for f in csv_files:
        print(f"       {f.name}")

    processed_dir.mkdir(parents=True, exist_ok=True)
    total_rows = 0

    for csv_path in csv_files:
        print(f"\n     Processing {csv_path.name} ...")
        total_rows = _merge_one(csv_path, raw_dir)
        _move_to_processed(csv_path, processed_dir)

    return total_rows


def ingest_force(raw_dir: Path) -> int:
    """
    Rebuild mode — no new data, just re-run pipeline on existing raw Parquet.
    Returns existing row count.
    """
    existing_path = raw_dir / "sightings.parquet"
    if not existing_path.exists():
        raise FileNotFoundError(
            "data/raw/sightings.parquet not found.\n"
            "No existing data to rebuild from.\n"
            "Drop a CSV into data/incoming/ and run without --force first."
        )
    count = len(pd.read_parquet(existing_path, columns=["target"]))
    print(f"     Rebuilding from existing data: {count:,} rows")
    return count


def ingest_single(
    csv_path:      Path,
    raw_dir:       Path,
    processed_dir: Path,
) -> int:
    """
    Process one specific CSV file.
    Merge into raw Parquet, move to processed.
    Returns total row count.
    """
    print(f"     Processing {csv_path.name} ...")
    total_rows = _merge_one(csv_path, raw_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    _move_to_processed(csv_path, processed_dir)
    return total_rows


# ═══════════════════════════════════════════════════════════════════════
# Core merge logic
# ═══════════════════════════════════════════════════════════════════════

def _merge_one(csv_path: Path, raw_dir: Path) -> int:
    """
    Read one CSV, merge with existing raw Parquet, deduplicate, write back.
    Returns total row count after merge.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    existing_path = raw_dir / "sightings.parquet"

    new_df = _read_and_clean(csv_path)
    print(f"     {len(new_df):,} valid rows in file")

    if existing_path.exists():
        existing_df = pd.read_parquet(existing_path)
        print(f"     {len(existing_df):,} rows in existing data")
        combined = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        print("     No existing data — first load")
        combined = new_df

    before   = len(combined)
    combined = (
        combined
        .drop_duplicates(subset=["target", "last_seen", "lat", "lon"])
        .sort_values(["target", "last_seen"])
        .reset_index(drop=True)
    )
    n_dupes    = before - len(combined)
    n_new      = len(combined) - (len(existing_df) if existing_path.exists() else 0)

    print(f"     {n_dupes:,} duplicate rows dropped")
    print(f"     {max(n_new, 0):,} net new rows added")
    print(f"     {len(combined):,} total rows in dataset")

    combined.to_parquet(existing_path, index=False, compression="snappy")
    return len(combined)


def _move_to_processed(csv_path: Path, processed_dir: Path) -> None:
    """
    Move a CSV from incoming to processed with a timestamp prefix.
    e.g. sightings.csv → 2026-03-16_02-15-00_sightings.csv
    """
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    new_name = f"{ts}_{csv_path.name}"
    dest     = processed_dir / new_name
    csv_path.rename(dest)
    print(f"     Moved -> data/processed/{new_name}")


# ═══════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════

def _read_and_clean(csv_path: Path) -> pd.DataFrame:
    """Read CSV, validate schema, coerce types, drop invalid rows."""
    df = pd.read_csv(csv_path, low_memory=False)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df["target"]    = pd.to_numeric(df["target"],    errors="coerce")
    df["lat"]       = pd.to_numeric(df["lat"],       errors="coerce")
    df["lon"]       = pd.to_numeric(df["lon"],       errors="coerce")
    df["last_seen"] = pd.to_datetime(
        df["last_seen"], errors="coerce", format="mixed"
    )

    before = len(df)
    df = df.dropna(subset=["target", "lat", "lon", "last_seen"])
    df = df[
        df["lat"].between(*LAT_BOUNDS) &
        df["lon"].between(*LON_BOUNDS)
    ].copy()

    dropped = before - len(df)
    if dropped > 0:
        print(f"     Dropped {dropped:,} invalid rows")

    df["target"] = df["target"].astype(int)
    return df.sort_values(["target", "last_seen"]).reset_index(drop=True)