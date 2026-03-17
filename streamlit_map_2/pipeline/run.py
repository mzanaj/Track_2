"""
pipeline/run.py
---------------
Entry point for the analytics pipeline.

SCHEDULED / NORMAL USE (checks incoming/, processes all CSVs found):
    python -m pipeline.run
    python -m pipeline.run --incoming

SINGLE FILE (manual, one specific file):
    python -m pipeline.run --input data/incoming/sightings_2026-03-16.csv

REBUILD FROM EXISTING DATA (no new CSV needed):
    python -m pipeline.run --force

Folder layout:
    data/incoming/    ← drop new CSVs here
    data/raw/         ← master Parquet lives here (built up over time)
    data/processed/   ← CSVs moved here after successful processing
    data/analytics/   ← pipeline outputs (what the app reads)
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
ROOT           = Path(__file__).resolve().parent.parent
DATA_RAW       = ROOT / "data" / "raw"
DATA_ANALYTICS = ROOT / "data" / "analytics"
DATA_INCOMING  = ROOT / "data" / "incoming"
DATA_PROCESSED = ROOT / "data" / "processed"

# ── Pipeline steps ─────────────────────────────────────────────────────
from pipeline.ingest        import ingest_incoming, ingest_force, ingest_single
from pipeline.cluster       import build_clusters
from pipeline.derived       import build_derived_tables
from pipeline.spatial_index import build_spatial_index


def run_pipeline(
    mode:       str  = "incoming",   # "incoming" | "force" | "single"
    input_path: Path = None,
):
    DATA_ANALYTICS.mkdir(parents=True, exist_ok=True)
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_INCOMING.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    total_start = time.perf_counter()

    mode_label = {
        "incoming": "INCOMING (process all files in data/incoming/)",
        "force":    "FORCE REBUILD (reprocess existing raw data)",
        "single":   f"SINGLE FILE ({input_path})",
    }[mode]

    print(f"\n{'='*60}")
    print(f"  GeoIntel Pipeline")
    print(f"  Mode  : {mode_label}")
    print(f"  Output: {DATA_ANALYTICS}")
    print(f"{'='*60}\n")

    # ── Step 1: Ingest ─────────────────────────────────────────────────
    _step("1 / 4  Ingest")
    if mode == "incoming":
        row_count = ingest_incoming(DATA_INCOMING, DATA_RAW, DATA_PROCESSED)
    elif mode == "force":
        row_count = ingest_force(DATA_RAW)
    elif mode == "single":
        row_count = ingest_single(input_path, DATA_RAW, DATA_PROCESSED)
    _done()

    if row_count == 0:
        print("  No data to process. Exiting.")
        return

    # ── Step 2: Cluster ────────────────────────────────────────────────
    _step("2 / 4  Cluster locations (DBSCAN) — runs on full dataset")
    build_clusters(DATA_ANALYTICS, source_parquet=DATA_RAW / "sightings.parquet")
    _done()

    # ── Step 3: Derived tables ─────────────────────────────────────────
    _step("3 / 4  Build derived tables (dwell, routines, home ranges)")
    build_derived_tables(DATA_ANALYTICS)
    _done()

    # ── Step 4: Spatial index ──────────────────────────────────────────
    _step("4 / 4  Build BallTree spatial index")
    build_spatial_index(DATA_ANALYTICS)
    _done()

    # ── Metadata ───────────────────────────────────────────────────────
    elapsed  = round(time.perf_counter() - total_start, 1)
    metadata = {
        "built_at":  datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
        "runtime_s": elapsed,
        "mode":      mode,
    }
    (DATA_ANALYTICS / "metadata.json").write_text(json.dumps(metadata, indent=2))

    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {elapsed}s")
    print(f"  Total rows in dataset: {row_count:,}")
    print(f"{'='*60}\n")

    return metadata


# ── Helpers ────────────────────────────────────────────────────────────
_step_start = None

def _step(label: str):
    global _step_start
    _step_start = time.perf_counter()
    print(f"  ▶  {label} ...", flush=True)

def _done():
    elapsed = round(time.perf_counter() - _step_start, 1)
    print(f"     ✓  {elapsed}s\n", flush=True)


# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GeoIntel analytics pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Folder layout:
  data/incoming/   ← drop new CSVs here before running
  data/raw/        ← master Parquet (grows over time)
  data/processed/  ← CSVs moved here after processing
  data/analytics/  ← pipeline outputs (what the app reads)

Examples:
  Daily scheduled job (cron):
    python -m pipeline.run

  Process one specific file manually:
    python -m pipeline.run --input data/incoming/sightings_2026-03-16.csv

  Rebuild analytics from existing data (no new CSV needed):
    python -m pipeline.run --force
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--incoming", action="store_true", default=True,
        help="Process all CSVs in data/incoming/ (default)"
    )
    group.add_argument(
        "--force", action="store_true",
        help="Rebuild analytics from existing raw Parquet — no new CSV needed"
    )
    group.add_argument(
        "--input", type=Path, metavar="FILE",
        help="Process one specific CSV file"
    )

    args = parser.parse_args()

    if args.force:
        run_pipeline(mode="force")
    elif args.input:
        if not args.input.exists():
            raise FileNotFoundError(f"File not found: {args.input}")
        run_pipeline(mode="single", input_path=args.input)
    else:
        run_pipeline(mode="incoming")