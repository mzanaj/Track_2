"""
app/utils/network.py
--------------------
Network graph rendering with node budget safety.

Identical UI output to the original. Added:
  - Connectivity scoring (shared locations × 2 + co-targets)
  - Greedy node budget trim (max 300 nodes)
  - Info banner when graph is trimmed
  - Uses pre-computed dwell/cluster data instead of iterating raw sightings

Node budget rule:
  total_nodes = len(selected_targets) + len(selected_location_nodes)
  If total_nodes > MAX_NODES, take targets in descending connectivity score
  until adding the next target would exceed the budget.
"""

import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
import pandas as pd

MAX_NODES = 300


def render_network(clustered_df: pd.DataFrame, color_map: dict):
    """
    Render the target–location network graph.

    clustered_df: sightings with location_id (from cluster_locations())
    color_map:    {target_str: hex_color}
    """

    # ── Find shared location IDs (2+ distinct targets) ────────────────────────
    shared_ids = (
        clustered_df.groupby("location_id")["target"]
        .nunique()
        .pipe(lambda s: s[s >= 2])
        .index
    )

    if len(shared_ids) == 0:
        st.info("No shared locations found — try increasing the cluster radius.")
        return

    plot_df = clustered_df[clustered_df["location_id"].isin(shared_ids)].copy()

    # ── Score targets by connectivity ─────────────────────────────────────────
    scores = _score_targets(plot_df)
    total_targets  = len(scores)
    total_locs     = len(shared_ids)
    total_possible = total_targets + total_locs

    # ── Trim to node budget if needed ─────────────────────────────────────────
    trimmed = False
    if total_possible > MAX_NODES:
        selected_targets, selected_loc_ids = _trim_to_budget(
            plot_df, scores, shared_ids, MAX_NODES
        )
        plot_df = plot_df[
            plot_df["target"].isin(selected_targets) &
            plot_df["location_id"].isin(selected_loc_ids)
        ]
        trimmed = True
    else:
        selected_targets = scores.index.tolist()

    # ── UI feedback ───────────────────────────────────────────────────────────
    n_shown_targets = plot_df["target"].nunique()
    n_shown_locs    = plot_df["location_id"].nunique()

    if trimmed:
        st.info(
            f"Showing {n_shown_targets} of {total_targets} targets — "
            f"ranked by connection density. "
            f"Use the target filter above to manually select any subset."
        )
    else:
        st.caption(
            f"Showing {n_shown_targets} targets · "
            f"{n_shown_locs} shared location(s) · "
            f"{len(plot_df)} sightings"
        )

    # ── Build PyVis graph ─────────────────────────────────────────────────────
    net = Network(
        height="600px",
        width="100%",
        bgcolor="#0f1117",
        font_color="#e4e6f0",
        notebook=False,
    )

    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -80,
                "centralGravity": 0.01,
                "springLength": 150,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "stabilization": { "iterations": 150 }
        },
        "nodes": { "font": { "size": 13 } },
        "edges": {
            "smooth": { "type": "continuous" },
            "color": { "opacity": 0.6 }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true
        }
    }
    """)

    added_targets   = set()
    added_locations = set()

    # ── Aggregate to edge list (visit count per target-location pair) ──────────
    edge_df = (
        plot_df
        .groupby(["target", "location_id", "location_label"])
        .size()
        .reset_index(name="visit_count")
    )

    for _, row in edge_df.iterrows():
        target_id   = str(row["target"])
        location_id = f"loc_{row['location_id']}"
        label_loc   = row["location_label"]
        color       = color_map.get(target_id, "#aaaaaa")
        visits      = int(row["visit_count"])

        if target_id not in added_targets:
            connectivity = int(scores.get(row["target"], 0))
            net.add_node(
                target_id,
                label=f"Target {target_id}",
                color=color,
                size=20 + min(connectivity * 2, 20),   # size reflects connectivity
                shape="dot",
                title=f"<b>Target {target_id}</b><br>Connectivity score: {connectivity}",
                borderWidth=2,
                borderWidthSelected=4,
            )
            added_targets.add(target_id)

        if location_id not in added_locations:
            # Node size reflects how many targets share this location
            n_targets_here = int(
                plot_df[plot_df["location_id"] == row["location_id"]]["target"].nunique()
            )
            net.add_node(
                location_id,
                label=label_loc,
                color="#f0c040",
                size=12 + min(n_targets_here * 3, 18),
                shape="diamond",
                title=f"<b>Shared Location</b><br>{label_loc}<br>{n_targets_here} targets",
                borderWidth=1,
            )
            added_locations.add(location_id)

        net.add_edge(
            target_id,
            location_id,
            color=color,
            width=max(1.0, min(visits / 5, 4.0)),   # edge weight = visit count
            title=f"Target {target_id} → {label_loc} ({visits} visits)",
        )

    html = net.generate_html()
    components.html(html, height=620, scrolling=False)


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score_targets(plot_df: pd.DataFrame) -> pd.Series:
    """
    Score each target by:
        (unique shared locations × 2) + unique co-located targets

    Shared locations weighted 2× because geographic breadth is the
    stronger structural signal — a target at many distinct shared
    locations is a hub; raw co-target count can inflate from one
    very busy location.

    Returns: pd.Series indexed by target, values = score, sorted descending.
    """
    scores = {}
    all_targets = plot_df["target"].unique()

    for target in all_targets:
        target_locs = set(
            plot_df[plot_df["target"] == target]["location_id"].unique()
        )
        # Targets that share at least one location with this target
        co_targets = plot_df[
            (plot_df["location_id"].isin(target_locs)) &
            (plot_df["target"] != target)
        ]["target"].nunique()

        scores[target] = len(target_locs) * 2 + co_targets

    return pd.Series(scores).sort_values(ascending=False)


# ── Budget trim ───────────────────────────────────────────────────────────────

def _trim_to_budget(
    plot_df:   pd.DataFrame,
    scores:    pd.Series,
    shared_ids,
    max_nodes: int,
) -> tuple[list, set]:
    """
    Greedily select targets in descending score order until adding
    the next target would exceed max_nodes.

    A target's node cost = 1 (itself) + new location nodes it contributes
    (locations not already added by a previously selected target).

    Returns (selected_targets, selected_location_ids).
    """
    selected_targets = []
    selected_locs    = set()

    for target in scores.index:
        target_locs = set(
            plot_df[
                (plot_df["target"] == target) &
                (plot_df["location_id"].isin(shared_ids))
            ]["location_id"].unique()
        )
        new_locs        = target_locs - selected_locs
        projected_nodes = len(selected_targets) + 1 + len(selected_locs) + len(new_locs)

        if projected_nodes > max_nodes:
            # Check if this target shares only existing locations (zero new nodes)
            if len(new_locs) == 0:
                # Free to add — no new location nodes needed
                selected_targets.append(target)
                continue
            # Otherwise skip and try next (might have lower cost)
            continue

        selected_targets.append(target)
        selected_locs |= target_locs

    return selected_targets, selected_locs
