# import streamlit as st
# from utils.streamlit_config import apply_config, render_header, render_footer

# apply_config()

# def render_home():
#     st.markdown("## Welcome to GeoMap")
#     st.markdown("""
#     A geospatial intelligence platform for tracking, analyzing, and surfacing 
#     behavioral patterns across multiple targets. Built for analysts who need 
#     to move fast and see clearly.
    
#     Use the sidebar to navigate between pages.
#     """)

#     st.divider()

#     # ── What this app does ────────────────────────────────────────────────
#     st.markdown("### What This App Does")
#     st.markdown("""
#     GeoMap ingests location sighting data — target ID, timestamp, and GPS coordinates — 
#     and transforms it into a layered intelligence picture. Every section is designed 
#     around a specific analytical question, from high-level overviews down to 
#     individual behavioral fingerprints.
#     """)

#     st.divider()

#     # ── Page breakdown ────────────────────────────────────────────────────
#     st.markdown("### Pages")

#     col1, col2 = st.columns(2)

#     with col1:
#         st.markdown("""
#         #### 🎯 Tracker
#         The core analytical workspace. Organized into progressive layers of analysis:
        
#         **Target Intelligence**
#         High-level cards showing each target's sighting count, active days, 
#         first/last seen, last known location, and total distance traveled. 
#         Expand any card for a full breakdown — sighting history, movement chart, 
#         and individual map.
        
#         **Sightings Analysis**
#         Six-tab geographic and temporal analysis suite:
#         - Raw sighting map with home range overlay and adaptive anomaly detection
#         - Sighting timeline across all targets
#         - Movement path visualization
#         - Animated path replay with multi-target convergence detection
#         - Density heatmap showing collective hotspots
#         - Convergence detection — flags when two targets were at the same place at the same time
        
#         **Temporal Analysis**
#         Hour × Day heatmap showing when each target is active, 
#         plus automated routine detection — confirmed patterns of repeated 
#         presence at the same location during the same time block.
        
#         **Location Intelligence**
#         Dwell detection flags locations a target returns to repeatedly. 
#         Shared location analysis and a force-directed network graph reveal 
#         which targets share locations — the strongest structural indicator of relationship.
#         """)

#     with col2:
#         st.markdown("""
#         #### 📊 Stats
#         Operational data pipeline monitoring. Tracks daily ingest volume 
#         over a rolling 90-day window with KPIs, trend line, average reference, 
#         and weekend highlighting. Useful for verifying data freshness and 
#         spotting ingestion anomalies before they affect analysis.
#         """)

#         st.divider()

#         st.markdown("### Key Analytical Concepts")
#         st.markdown("""
#         **Haversine Distance**
#         All distance calculations use the Haversine formula — actual 
#         ground distance between two GPS coordinates accounting for Earth's curvature. 
#         More accurate than flat coordinate math, especially over longer distances.
        
#         **Convergence vs Shared Location**
#         A *shared location* means two targets visited the same place — at any time. 
#         A *convergence* means they were there within the same time window. 
#         Only convergence implies a potential meeting.
        
#         **Adaptive Anomaly Detection**
#         Home range thresholds are computed per target using their own movement 
#         standard deviation — so a target with a small daily range gets a tight 
#         threshold, and a wide-ranging target gets a proportionally wider one. 
#         No fixed distance — the data sets its own baseline.
        
#         **Recency Decay**
#         Home range and anomaly detection weight recent sightings more heavily 
#         using exponential decay. Older behavior fades out — the model reflects 
#         who the target is now, not months ago.
        
#         **Routine Detection**
#         A routine is flagged when the same target appears at the same location 
#         cluster, in the same 2-hour time block, on the same day of week, 
#         a minimum number of times. Confirmed routines are predictive — 
#         you can anticipate where a target will be before they arrive.
        
#         **Location Clustering**
#         All GPS coordinates are grouped into stable location clusters at pipeline 
#         time using DBSCAN (10m radius). Every sighting is permanently assigned a 
#         location ID. Dwell, routines, and network analysis all read this ID — 
#         none of them re-run spatial math at query time.
#         """)

#     st.divider()

#     # ── Data pipeline ─────────────────────────────────────────────────────
#     st.markdown("### Data Pipeline")
#     st.markdown("""
#     The Tracker page reads from pre-computed analytics tables built by the pipeline.
#     Raw sightings are never queried directly by the app — all heavy computation 
#     happens at pipeline time, not at interaction time.
#     """)

#     col1, col2 = st.columns(2)

#     with col1:
#         st.markdown("#### First use")
#         st.code("""# 1. Drop your CSV into incoming/
# data/incoming/sightings.csv

# # 2. Run the pipeline
# python -m pipeline.run

# # 3. Launch the app
# streamlit run 1_🏠_Home.py""", language="bash")

#     with col2:
#         st.markdown("#### Daily updates")
#         st.code("""# 1. Drop new CSV into incoming/
# data/incoming/sightings_2026-03-17.csv

# # 2. Run — merges automatically
# python -m pipeline.run

# # Overlapping rows are deduplicated.
# # Processed files move to data/processed/
# # with a timestamp prefix.""", language="bash")

#     st.markdown("""
#     The pipeline runs in ~60–90 seconds on 1M rows. 
#     It can be scheduled via cron or Windows Task Scheduler to run nightly after your data pull.
#     """)

#     st.divider()

#     # ── Folder layout ─────────────────────────────────────────────────────
#     st.markdown("### Folder Layout")
#     st.code("""data/
#   incoming/    ← drop new CSVs here before running the pipeline
#   raw/         ← master Parquet, grows over time
#   processed/   ← CSVs moved here after successful processing (timestamped)
#   analytics/   ← pre-computed tables the app reads from""", language="bash")

#     st.divider()

#     # ── Data format ───────────────────────────────────────────────────────
#     st.markdown("### Expected Input Format")
#     st.markdown("CSV files dropped into `data/incoming/` must contain these columns:")

#     st.dataframe(
#         {
#             "Column":      ["target", "last_seen", "lat", "lon"],
#             "Type":        ["integer", "datetime", "float", "float"],
#             "Description": [
#                 "Unique target identifier",
#                 "Sighting timestamp (YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS)",
#                 "Latitude (decimal degrees, WGS84)",
#                 "Longitude (decimal degrees, WGS84)",
#             ],
#         },
#         hide_index=True,
#         width="stretch",
#     )

#     st.markdown("""
#     Mixed datetime formats within the same file are handled automatically. 
#     Rows with invalid coordinates or unparseable timestamps are dropped with a count reported.
    
#     The Stats page reads from `data/daily_ingest_data.csv`. Required columns: 
#     `datetime`, `date`, `day_of_week`, `is_weekend`, `data_count`.
#     """)


# def main():
#     apply_config()
#     render_header(title="Home")
#     render_home()
#     render_footer()


# if __name__ == "__main__":
#     main()

import streamlit as st
from utils.streamlit_config import apply_config, render_header, render_footer

apply_config()

def render_home():
    st.markdown("## Welcome to GeoMap")
    st.markdown("""
    A geospatial intelligence platform for tracking, analyzing, and surfacing 
    behavioral patterns across multiple targets. Built for analysts who need 
    to move fast and see clearly.
    
    Use the sidebar to navigate between pages.
    """)

    st.divider()

    # ── What this app does ────────────────────────────────────────────────
    st.markdown("### What This App Does")
    st.markdown("""
    GeoMap ingests location sighting data — target ID, timestamp, and GPS coordinates — 
    and transforms it into a layered intelligence picture. Every section is designed 
    around a specific analytical question, from high-level overviews down to 
    individual behavioral fingerprints.
    """)

    st.divider()

    # ── Page breakdown ────────────────────────────────────────────────────
    st.markdown("### Pages")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🎯 Tracker
        The core analytical workspace. Organized into progressive layers of analysis:
        
        **Target Intelligence**
        High-level cards showing each target's sighting count, active days, 
        first/last seen, last known location, and total distance traveled. 
        Expand any card for a full breakdown — sighting history, movement chart, 
        and individual map.
        
        **Sightings Analysis**
        Six-tab geographic and temporal analysis suite:
        - Raw sighting map with home range overlay and adaptive anomaly detection
        - Sighting timeline across all targets
        - Movement path visualization
        - Animated path replay with multi-target convergence detection
        - Density heatmap showing collective hotspots
        - Convergence detection — flags when two targets were at the same place at the same time
        
        **Temporal Analysis**
        Hour × Day heatmap showing when each target is active, 
        plus automated routine detection — confirmed patterns of repeated 
        presence at the same location during the same time block.
        
        **Location Intelligence**
        Dwell detection flags locations a target returns to repeatedly. 
        Shared location analysis and a force-directed network graph reveal 
        which targets share locations — the strongest structural indicator of relationship.
        """)

    with col2:
        st.markdown("""
        #### 📊 Stats
        Operational data pipeline monitoring. Tracks daily ingest volume 
        over a rolling 90-day window with KPIs, trend line, average reference, 
        and weekend highlighting. Useful for verifying data freshness and 
        spotting ingestion anomalies before they affect analysis.
        """)

    st.divider()

    # ── Key concepts ──────────────────────────────────────────────────────
    st.markdown("### Key Analytical Concepts")

    with st.expander("Haversine Distance — how distances are calculated", expanded=False):
        st.markdown("""
        All distance calculations in GeoMap use the **Haversine formula** — the correct 
        way to measure distance between two GPS coordinates on the surface of the Earth.
        
        Latitude and longitude are angles, not distances. You cannot subtract them directly. 
        One degree of longitude near the poles is only a few kilometres wide; 
        at the equator it is 111km. The Haversine formula accounts for this compression.
        
        **The formula:**
        ```
        a = sin²(Δlat/2) + cos(lat₁) · cos(lat₂) · sin²(Δlon/2)
        distance = 2 · R · arcsin(√a)
        ```
        where R = 6,371,000 metres (Earth's radius).
        
        The `cos(lat₁) · cos(lat₂)` term is the correction — it shrinks the longitude 
        contribution as you move away from the equator. At Washington DC (~39°N), 
        1° of longitude ≈ 85km instead of 111km. Without this correction, 
        east-west distances would be overstated by ~30%.
        
        Used in: distance traveled per target, convergence detection, dwell clustering, 
        anomaly thresholds, BallTree spatial index.
        """)

    with st.expander("Convergence vs Shared Location — what's the difference?", expanded=False):
        st.markdown("""
        These two concepts are often confused. The distinction is time.
        
        **Shared location** — two targets visited the same place. No time constraint.
        Target A visited the coffee shop on Monday. Target B visited it on Friday. 
        That is a shared location. It may mean nothing — it's a popular coffee shop.
        
        **Convergence** — two targets were at the same place *within the same time window*.
        Target A at the coffee shop at 08:15. Target B at the coffee shop at 08:45. 
        That is a convergence. Same place, 30 minutes apart — possible meeting.
        
        **Example:**
        
        | Target | Location | Time |
        |--------|----------|------|
        | A | Coffee shop | Mon 08:15 |
        | B | Coffee shop | Mon 08:45 |
        | A | Coffee shop | Tue 14:00 |
        
        - A + B on Monday → **Convergence** (45 min apart, same place)
        - A Monday + A Tuesday → **Shared location** (same target, same place, different days → routine)
        - B Monday + A Tuesday → **Shared location** (different targets, different days → no meeting implied)
        
        Use Convergence Detection to identify possible meetings. 
        Use Shared Locations to map the relationship network regardless of timing.
        Both are necessary — neither alone tells the full story.
        """)

    with st.expander("Adaptive Anomaly Detection — home range methods explained", expanded=False):
        st.markdown("""
        The home range overlay flags sightings that fall outside a target's normal 
        movement area. Two methods are available, each suited to different target behaviors.
        
        ---
        
        **Method 1 — IQR Box**
        
        Draws a rectangular bounding box using the 10th–90th percentile of the target's 
        weighted lat/lon values. Simple, fast, and easy to reason about.
        
        - Good for targets with roughly rectangular movement patterns 
          (commute corridor between home and work)
        - Limitation: the box is always axis-aligned — diagonal movement patterns 
          produce a box that is wider than necessary, reducing sensitivity
        - Points on the corners of the box may be flagged even if they lie within 
          the target's normal diagonal corridor
        
        **Method 2 — DBSCAN Hull**
        
        Finds the densest cluster of the target's sightings using DBSCAN, 
        then draws a convex hull (tight polygon) around it.
        
        - Good for irregular movement patterns — wraps the actual shape of where the target goes
        - Naturally ignores sparse outlier sightings when building the boundary
        - Better at catching genuinely unusual locations without flagging border cases
        
        **Important:** this is a *different* DBSCAN from the one used in the pipeline.
        
        | | Pipeline DBSCAN | Home Range DBSCAN |
        |---|---|---|
        | Purpose | Groups GPS pings into stable place IDs | Finds where a target most densely operates |
        | Radius | 10m — precise GPS grouping | ~300m — behavioral region |
        | Runs when | Once, pipeline time | At query time, per target |
        | Output | `location_id` column | Convex hull polygon on map |
        
        ---
        
        **Anomaly threshold**
        
        Each target gets their own threshold based on their own movement standard deviation:
        
        ```
        threshold = mean_distance_from_center + (N × std_distance)
        ```
        
        - Conservative (3σ) — only extreme outliers flagged. Very far from normal.
        - Moderate (2σ) — clear deviations flagged. Default.
        - Aggressive (1σ) — subtle deviations flagged. Higher noise, higher sensitivity.
        
        Because each target uses their own std, a wide-ranging target gets a wide threshold 
        and a tightly-routed target gets a tight threshold. The sensitivity is relative — 
        not a fixed distance.
        
        **Recency weighting** applies here too — recent sightings contribute more to 
        the center and threshold calculation than older ones.
        """)

    with st.expander("Recency Decay — how quickly does old behavior fade?", expanded=False):
        st.markdown("""
        Home range calculations and anomaly thresholds give more weight to recent sightings 
        using exponential decay:
        
        ```
        weight = e^(−rate × days_ago)
        ```
        
        With the **default rate of 0.05**:
        
        | Days ago | Weight remaining |
        |----------|-----------------|
        | Today | 100% |
        | 2 weeks | 50% |
        | 4 weeks | 25% |
        | 2 months | 5% |
        | 3 months | ~1% |
        
        Practically: a sighting from two weeks ago counts half as much as today's. 
        After three months it is nearly irrelevant.
        
        **The decay rate slider** controls how fast the fade happens:
        - Low rate (0.01) — very slow decay. A sighting from two weeks ago still counts for 87%. 
          Good if the target's behavior is stable and history is meaningful.
        - High rate (0.20) — fast decay. Two-week-old data is down to 6%. 
          Good if behavior changes frequently and you only care about recent patterns.
        
        This matters most when a target has changed their routine. If they moved home 
        three weeks ago, the new home should dominate their home range calculation — 
        not be averaged against months of old data from the old address.
        """)

    with st.expander("Routine Detection — how patterns are surfaced", expanded=False):
        st.markdown("""
        A routine is confirmed when the same target appears at the same location, 
        during the same 2-hour time block, on the same day of week, 
        a minimum number of times.
        
        **Algorithm:**
        1. Each sighting is assigned to a location cluster (via its `location_id`)
        2. Each sighting's time is bucketed into a 2-hour block (08:00–10:00, 10:00–12:00, etc.)
        3. Each sighting is tagged with its day of week
        4. Any combination of `(target, location, time block, day)` that repeats at or 
           above the minimum threshold is surfaced as a routine
        
        **Why this is operationally powerful:** a confirmed routine is predictive. 
        If Target 7 has appeared at location 4291 every Wednesday between 08:00–10:00 
        at least 4 times, you can anticipate they will be there next Wednesday. 
        You know where they will be before they get there.
        
        **Controls:**
        - Minimum Occurrences — how many repetitions before a pattern is confirmed. 
          Lower = more patterns, more noise. Higher = only the strongest signals.
        - The location grouping is fixed at pipeline time (see Location Clustering below). 
          The slider does not re-cluster raw GPS points.
        """)

    with st.expander("Location Clustering — what location_id means", expanded=False):
        st.markdown("""
        GPS devices introduce small errors. Two readings from the same coffee shop 
        might be 8 metres apart. Without clustering, they would appear as two separate 
        locations. With clustering, they are correctly recognised as the same place.
        
        **At pipeline time**, all GPS coordinates are grouped using DBSCAN at a 10-metre radius. 
        Every sighting is permanently assigned a `location_id` — a stable number identifying 
        which physical place that sighting belongs to.
        
        **Why this matters for performance:** every feature that involves "places" — 
        dwell detection, routine detection, shared locations, the network graph — 
        reads the `location_id` number instead of recomputing spatial proximity. 
        None of them re-run spatial math at query time. DBSCAN runs once, at 2am, 
        on the full dataset. Not once per user, not once per slider move.
        
        **The "Cluster Radius" slider in Dwell and Routines:**
        This slider currently filters which pre-clustered results are shown — 
        it does not re-cluster raw GPS points. The underlying groupings were 
        fixed at pipeline time with a 10m radius. Moving the slider to 50m 
        broadens which location groups are included in the results; 
        it does not recompute how individual GPS pings are grouped together.
        
        If you need different clustering granularity (e.g. 50m to treat a whole 
        city block as one location), that requires re-running the pipeline with 
        a different `eps_meters` setting in `pipeline/cluster.py`.
        """)

    st.divider()

    # ── Data pipeline ─────────────────────────────────────────────────────
    st.markdown("### Data Pipeline")
    st.markdown("""
    The Tracker page reads from pre-computed analytics tables built by the pipeline.
    Raw sightings are never queried directly by the app — all heavy computation 
    happens at pipeline time, not at interaction time. This keeps the app fast 
    regardless of dataset size.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### First use")
        st.code("""# 1. Drop your CSV into incoming/
data/incoming/sightings.csv

# 2. Run the pipeline
python -m pipeline.run

# 3. Launch the app
streamlit run 1_🏠_Home.py""", language="bash")

    with col2:
        st.markdown("#### Daily updates (scheduled)")
        st.code("""# 1. Your query saves to incoming/
data/incoming/sightings_2026-03-17.csv

# 2. Pipeline merges automatically
python -m pipeline.run

# Overlapping rows are deduplicated on
# (target, last_seen, lat, lon).
# Files move to data/processed/ with
# a timestamp prefix after success.""", language="bash")

    st.markdown("""
    The pipeline runs in approximately 60–90 seconds on 1M rows and can be 
    scheduled via cron (Linux/Mac) or Task Scheduler (Windows) to run nightly 
    after your data pull completes.
    """)

    st.divider()

    # ── Folder layout ─────────────────────────────────────────────────────
    st.markdown("### Folder Layout")
    st.code("""data/
  incoming/    ← drop new CSVs here before running the pipeline
  raw/         ← master Parquet, grows over time as data merges in
  processed/   ← CSVs moved here after successful processing (timestamped)
  analytics/   ← pre-computed tables the app reads from

pipeline/      ← run.py, ingest.py, cluster.py, derived.py, spatial_index.py
utils/         ← db.py, data.py, convergence.py, render.py, network.py""",
        language="bash")

    st.divider()

    # ── Data format ───────────────────────────────────────────────────────
    st.markdown("### Expected Input Format")
    st.markdown("CSV files dropped into `data/incoming/` must contain these columns:")

    st.dataframe(
        {
            "Column":      ["target", "last_seen", "lat", "lon"],
            "Type":        ["integer", "datetime", "float", "float"],
            "Description": [
                "Unique target identifier",
                "Sighting timestamp — YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS",
                "Latitude in decimal degrees (WGS84)",
                "Longitude in decimal degrees (WGS84)",
            ],
        },
        hide_index=True,
        width="stretch",
    )

    st.markdown("""
    Mixed datetime formats within the same file are handled automatically. 
    Rows with invalid coordinates, unparseable timestamps, or missing values 
    are dropped with a count reported in the pipeline output.
    
    The Stats page reads from `data/daily_ingest_data.csv`. Required columns: 
    `datetime`, `date`, `day_of_week`, `is_weekend`, `data_count`.
    """)


def main():
    apply_config()
    render_header(title="Home")
    render_home()
    render_footer()


if __name__ == "__main__":
    main()