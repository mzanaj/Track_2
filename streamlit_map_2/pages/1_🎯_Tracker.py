from utils.timing import timer, reset_timing_log, render_timing_log

# from utils.streamlit_config import apply_config, render_header, render_footer
# from utils.data import (
#     load_data, get_last_seen_table, get_convergences,
#     cluster_locations, get_shared_locations_table,
#     get_dwell_locations, get_heatmap_data,
#     get_target_summary, haversine_meters,
#     haversine_meters_vectorized,
#     get_routines, get_target_home_range,
#     get_iqr_box, get_dbscan_hulls, get_anomalies
# )
# from utils.render import build_heatmap_grid
# from utils.network import render_network
# from utils.db import pipeline_age_label
# import plotly.graph_objects as go
# import plotly.express as px
# import streamlit as st
# import pandas as pd

# # ── At the top of the file or in a config function ────────────────────
# def init_session_state():
#     defaults = {
#         "max_meters":           50,
#         "max_minutes":          120,
#         "decay_rate":           0.05,
#         "sensitivity":          "Moderate",
#         "range_method":         "IQR Box",
#         "heatmap_radius":       20,
#         "routine_min":          3,
#         "routine_radius":       50,
#         "anim_speed":           600,
#         "dwell_min_visits":     3,
#         "dwell_cluster_radius": 10,
#         "show_home_range":      False,
#         "map_style":            "Street",
#         "charts_selected":      [],
#         "temporal_selected":    [],
#         "show_all_routines":    False,
#         "show_all_dwell":       False,
#         "show_all_shared":      False
#     }
#     for key, val in defaults.items():
#         if key not in st.session_state:
#             st.session_state[key] = val
            
# # ── Color assignment — qualitative palette with rotation for many targets ──
# def assign_target_colors(targets):
#     palette = px.colors.qualitative.Safe  # 11 distinct colors, colorblind-friendly
#     return {t: palette[i % len(palette)] for i, t in enumerate(sorted(targets))}
    
# def render_target_intel():
#     st.markdown("## Target Intelligence")
#     st.markdown("""
#     Consolidated intelligence profile for each tracked target. 
#     Cards display the most operationally relevant information at a glance — 
#     total sightings, active days, first and last seen timestamps, last known coordinates, 
#     and total distance traveled between sightings.
    
#     Use the **search bar** to filter by target number. By default the top 10 targets are shown — 
#     toggle **Show All** to see the full list.
    
#     Click **▶ Detail** on any card to expand a full intelligence breakdown inline, including:
#     - Complete sighting history with timestamps and coordinates
#     - Movement analysis — distance from origin and speed between sightings over time
#     - Individual sighting map showing all recorded positions
    
#     *Distance traveled is calculated using the Haversine formula — 
#     actual ground distance between consecutive sightings in chronological order.*
#     """)

#     df      = load_data()
#     summary = get_target_summary(df)

#     last_seen_df = get_last_seen_table(df)
#     summary = summary.merge(
#         last_seen_df[["target", "lat", "lon"]],
#         on="target", how="left",
#     )
#     summary = summary.rename(columns={"lat": "last_lat", "lon": "last_lon"})

#     color_map = assign_target_colors([str(t) for t in summary["target"].tolist()])

#     # ── Search / filter ───────────────────────────────────────────────────
#     col1, col2 = st.columns([2, 1])
#     with col1:
#         search = st.text_input(
#             "Search Target",
#             placeholder="Type target number...",
#             label_visibility="collapsed",
#         )
#     with col2:
#         show_all = st.toggle("Show All", value=False)

#     filtered_summary = (
#         summary[summary["target"].astype(str).str.contains(search.strip())]
#         if search else summary
#     )
#     display_summary = filtered_summary if show_all else filtered_summary.head(10)

#     if not show_all and len(filtered_summary) > 10:
#         st.caption(f"Showing 10 of {len(filtered_summary)} targets. Toggle 'Show All' to see more.")

#     # ── Session state for expanded card ───────────────────────────────────
#     if "expanded_target" not in st.session_state:
#         st.session_state.expanded_target = None

#     # ── Cards grid — render detail after each row of 3 ───────────────────
#     rows = [display_summary.iloc[i:i+3] for i in range(0, len(display_summary), 3)]

#     for row_df in rows:
#         cols = st.columns(3)

#         for i, (_, row) in enumerate(row_df.iterrows()):
#             color  = color_map[str(row["target"])]
#             target = row["target"]

#             with cols[i % 3]:
#                 st.markdown(f"""
#                 <div style="
#                     border: 1px solid {color};
#                     border-radius: 8px;
#                     padding: 16px;
#                     margin-bottom: 4px;
#                     background: rgba(255,255,255,0.02);
#                 ">
#                     <div style="color:{color}; font-weight:700; font-size:1rem; margin-bottom:8px;">
#                         Target {target}
#                     </div>
#                     <div style="font-size:0.82rem; line-height:1.8; color:#c8cad4;">
#                         🔍 <b>Sightings:</b> {row['total_sightings']}<br>
#                         📅 <b>Active Days:</b> {row['active_days']}<br>
#                         🕐 <b>First Seen:</b> {row['first_seen'].strftime('%Y-%m-%d %H:%M')}<br>
#                         🕑 <b>Last Seen:</b> {row['last_seen'].strftime('%Y-%m-%d %H:%M')}<br>
#                         📍 <b>Last Location:</b> ({row['last_lat']:.5f}, {row['last_lon']:.5f})<br>
#                         🛣️ <b>Distance:</b> {row['distance_km']} km
#                     </div>
#                 </div>
#                 """, unsafe_allow_html=True)

#                 is_expanded = st.session_state.expanded_target == target
#                 btn_label   = "▼ Close" if is_expanded else "▶ Detail"
#                 if st.button(btn_label, key=f"btn_{target}", use_container_width=True):
#                     st.session_state.expanded_target = None if is_expanded else target
#                     st.rerun()

#         # ── Detail panel — renders immediately after its row ──────────────
#         row_targets = row_df["target"].tolist()
#         if st.session_state.expanded_target in row_targets:
#             target = st.session_state.expanded_target
#             row    = summary[summary["target"] == target].iloc[0]
#             color  = color_map[str(target)]

#             st.divider()
#             st.markdown(f"#### Target {target} — Detail")
#             st.caption(
#                 f"Full sighting record for Target {target}. "
#                 f"Movement chart shows distance from first known sighting (left axis) "
#                 f"and estimated speed between consecutive sightings (right axis, km/h). "
#                 f"Speed spikes may indicate vehicle use. "
#                 f"Distance returning toward zero suggests the target is returning to their origin point."
#             )

#             target_df = df[df["target"] == target].sort_values("last_seen").copy()
#             target_df["target"] = target_df["target"].astype(str)
#             coords = target_df[["lat", "lon"]].values

#             c1, c2, c3 = st.columns([1, 2, 2])

#             with c1:
#                 st.markdown("**Sightings**")
#                 st.dataframe(
#                     target_df[["last_seen", "lat", "lon"]],
#                     column_config={
#                         "last_seen": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
#                         "lat":       st.column_config.NumberColumn("Lat", format="%.5f"),
#                         "lon":       st.column_config.NumberColumn("Lon", format="%.5f"),
#                     },
#                     hide_index=True,
#                     width="stretch",
#                     height=300,
#                 )

#             with c2:
#                 st.markdown("**Movement**")
#                 origin_lat, origin_lon = coords[0][0], coords[0][1]
#                 target_df["dist_m"] = haversine_meters_vectorized(
#                     origin_lat, origin_lon,
#                     target_df["lat"], target_df["lon"]
#                 )
#                 speeds = [None]
#                 for j in range(1, len(coords)):
#                     dist_m = haversine_meters(
#                         coords[j-1][0], coords[j-1][1],
#                         coords[j][0],   coords[j][1]
#                     )
#                     dt_hrs = (
#                         target_df["last_seen"].iloc[j] - target_df["last_seen"].iloc[j-1]
#                     ).total_seconds() / 3600
#                     speeds.append(round(dist_m / 1000 / dt_hrs, 2) if dt_hrs > 0 else 0)
#                 target_df["speed_kmh"] = speeds

#                 fig_m = go.Figure()
#                 fig_m.add_trace(go.Scatter(
#                     x=target_df["last_seen"],
#                     y=target_df["dist_m"],
#                     name="Dist (m)",
#                     mode="lines+markers",
#                     line=dict(color=color, width=2),
#                     yaxis="y1",
#                 ))
#                 fig_m.add_trace(go.Scatter(
#                     x=target_df["last_seen"],
#                     y=target_df["speed_kmh"],
#                     name="Speed (km/h)",
#                     mode="lines+markers",
#                     line=dict(color="rgba(255,200,50,0.8)", width=2, dash="dot"),
#                     yaxis="y2",
#                 ))
#                 fig_m.update_layout(
#                     height=300,
#                     margin={"t": 5, "b": 5, "l": 5, "r": 5},
#                     yaxis=dict(title="Dist (m)"),
#                     yaxis2=dict(
#                         title="Speed (km/h)",
#                         overlaying="y",
#                         side="right",
#                         showgrid=False,
#                     ),
#                     legend=dict(orientation="h", y=-0.35),
#                 )
#                 st.plotly_chart(fig_m, width="stretch")

#             with c3:
#                 st.markdown("**Map**")
#                 fig_map = px.scatter_map(
#                     target_df,
#                     lat="lat",
#                     lon="lon",
#                     color="target",
#                     color_discrete_map=color_map,
#                     hover_data={"lat": True, "lon": True, "last_seen": True},
#                     zoom=12,
#                     height=300,
#                 )
#                 fig_map.update_layout(
#                     map_style="carto-darkmatter",
#                     margin={"r": 0, "t": 0, "l": 0, "b": 0},
#                     showlegend=False,
#                 )
#                 st.plotly_chart(fig_map, width="stretch")

#             st.divider()
            
# def render_charts():
#     st.markdown("## Sightings Analysis")
#     st.markdown("""
#     Comprehensive geographic and temporal analysis of all target sightings.
#     Use the filters below to focus on specific targets. The map style applies across all map-based tabs.
    
#     Tabs cover: raw sighting positions, timeline, movement paths, animated path replay, 
#     density heatmap, and convergence detection between targets.
#     """)

#     df = load_data()

#     # ── Global filters — apply to all tabs ───────────────────────────────
#     all_targets = sorted(df["target"].unique())
#     col1, col2 = st.columns([3, 1])
#     with col1:
#         selected = st.multiselect(
#             "Filter by Target",
#             options=all_targets,
#             default=st.session_state["charts_selected"] if st.session_state["charts_selected"] else all_targets,
#             format_func=lambda x: f"Target {x}",
#             key="charts_selected",
#         )
#     with col2:
#         map_styles = {
#             "Street":  "open-street-map",
#             "Dark":    "carto-darkmatter",
#             "Light":   "carto-positron",
#             "Blank":   "white-bg",
#         }
#         style_choice = st.selectbox("Map Style", options=list(map_styles.keys()), index=0)

#         style_choice = st.selectbox("Map Style",
#                                     options=list(map_styles.keys()),
# index=list(map_styles.keys()).index(st.session_state["map_style"]),
#             key="map_style",
#         )

#     filtered = df[df["target"].isin(selected)].copy() if selected else df.copy()
#     filtered["target"] = filtered["target"].astype(str)
#     color_map = assign_target_colors([str(t) for t in all_targets])

#     # ── Tabs ─────────────────────────────────────────────────────────────
#     tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
#         "📍 Map", "📈 Timeline", "🛤️ Paths", "▶️ Animate", "🌡️ Heatmap", "🔴 Convergence"
#     ])

#     # ── Tab 1 — Sightings map + home range overlay ────────────────────────
#     with tab1:
#         st.markdown("#### Sightings Map")
#         st.markdown("""
#         All recorded sightings plotted by geographic position. Each target has a unique color.
        
#         **Home Range overlay** — when enabled, draws each target's normal movement area based on 
#         historical sightings. Sightings that fall outside this range are flagged as anomalies.
#         - **IQR Box** — bounding box built from the 10th–90th percentile of weighted lat/lon values. 
#           Simple and fast. Good for targets with roughly rectangular movement patterns.
#         - **DBSCAN** — density-based clustering that finds the tightest region where the target 
#           most frequently appears, then draws a convex hull around it. Better for irregular patterns.
#         - **Recency Decay** — how much weight to give recent vs older sightings when computing 
#           the home range. Higher = older sightings fade out faster.
#         - **Anomaly Sensitivity** — controls how far outside the normal range a sighting must be 
#           before it is flagged. Conservative (3σ) = only extreme outliers. Aggressive (1σ) = 
#           flags subtle deviations. Based on each target's own movement standard deviation, 
#           so thresholds adapt per target automatically.
#         """)

#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             show_range = st.toggle(
#                 "Show Home Range",
#                 value=st.session_state["show_home_range"],
#                 key="show_home_range",
#             )
#         with col2:
#             range_method = st.radio(
#                 "Method", options=["IQR Box", "DBSCAN"],
#                 horizontal=True, 
#                     index=["IQR Box", "DBSCAN"].index(st.session_state["range_method"]),

#                 key="range_method",
#                 disabled=not show_range,
#             )
#         with col3:
#             decay_rate = st.slider(
#                 "Recency Decay",
#                 min_value=0.01, max_value=0.20, step=0.01,
#                 value=st.session_state["decay_rate"],
#                 help="Higher = older sightings matter less",
#                 key="decay_rate", disabled=not show_range,
#             )
#         with col4:
#             sensitivity = st.select_slider(
#                 "Anomaly Sensitivity",
#                 options=["Conservative", "Moderate", "Aggressive"],
#                 value=st.session_state["sensitivity"],
#                 key="sensitivity",
#                 disabled=not show_range
#             )

#         sensitivity_map = {"Conservative": 3.0, "Moderate": 2.0, "Aggressive": 1.0}
#         n_std = sensitivity_map[sensitivity]

#         fig = px.scatter_map(
#             filtered, lat="lat", lon="lon",
#             color="target", color_discrete_map=color_map,
#             hover_data={"lat": True, "lon": True, "last_seen": True, "target": True},
#             zoom=12, height=550,
#             title="Target Sightings — Washington DC",
#         )

#         if show_range:
#             home_ranges = get_target_home_range(filtered, decay_rate=decay_rate)

#             if range_method == "IQR Box":
#                 iqr_boxes = get_iqr_box(filtered, decay_rate=decay_rate)
#                 for target, box in iqr_boxes.items():
#                     color = color_map.get(str(target), "#ffffff")
#                     lats  = [box["lat_low"], box["lat_low"],  box["lat_high"], box["lat_high"], box["lat_low"]]
#                     lons  = [box["lon_low"], box["lon_high"], box["lon_high"], box["lon_low"],  box["lon_low"]]
#                     fig.add_trace(go.Scattermap(
#                         lat=lats, lon=lons, mode="lines", fill="toself",
#                         fillcolor=color.replace(")", ",0.10)").replace("rgb", "rgba"),
#                         line=dict(color=color, width=1.5),
#                         name=f"T{target} Range", legendgroup=f"range_{target}",
#                         showlegend=True, hoverinfo="skip",
#                     ))

#             elif range_method == "DBSCAN":
#                 hulls = get_dbscan_hulls(filtered, decay_rate=decay_rate)
#                 for target, polygon in hulls.items():
#                     if polygon is None:
#                         continue
#                     color = color_map.get(str(target), "#ffffff")
#                     lats  = [p[0] for p in polygon]
#                     lons  = [p[1] for p in polygon]
#                     fig.add_trace(go.Scattermap(
#                         lat=lats, lon=lons, mode="lines", fill="toself",
#                         fillcolor=color.replace(")", ",0.10)").replace("rgb", "rgba"),
#                         line=dict(color=color, width=1.5),
#                         name=f"T{target} Range", legendgroup=f"range_{target}",
#                         showlegend=True, hoverinfo="skip",
#                     ))

#             anomalies = get_anomalies(filtered, home_ranges, n_std=n_std)
#             if not anomalies.empty:
#                 anomalies["target"] = anomalies["target"].astype(str)
#                 fig.add_trace(go.Scattermap(
#                     lat=anomalies["lat"], lon=anomalies["lon"],
#                     mode="markers",
#                     marker=dict(size=14, color="red", symbol="cross"),
#                     name="⚠ Anomaly",
#                     hovertemplate=(
#                         "<b>⚠ Anomaly</b><br>"
#                         "Target: %{customdata[0]}<br>"
#                         "Time: %{customdata[1]}<br>"
#                         "Dist from center: %{customdata[2]}m<br>"
#                         "Normal range: %{customdata[3]}m ± %{customdata[4]}m<br>"
#                         "Threshold: %{customdata[5]}m<extra></extra>"
#                     ),
#                     customdata=anomalies[[
#                         "target", "last_seen", "dist_from_center",
#                         "mean_dist_m", "std_dist_m", "threshold_m"
#                     ]].round({"dist_from_center": 1}).values,
#                 ))
#                 st.warning(f"⚠ **{len(anomalies)} anomalous sighting(s)** detected.")
#                 st.markdown("##### Anomalous Sightings")
#                 st.caption("Sightings outside each target's adaptive normal movement range, sorted by distance from center.")
#                 st.dataframe(
#                     anomalies[[
#                         "target", "last_seen", "lat", "lon",
#                         "dist_from_center", "mean_dist_m", "threshold_m"
#                     ]].sort_values("dist_from_center", ascending=False),
#                     column_config={
#                         "target":           st.column_config.NumberColumn("Target"),
#                         "last_seen":        st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
#                         "lat":              st.column_config.NumberColumn("Lat", format="%.6f"),
#                         "lon":              st.column_config.NumberColumn("Lon", format="%.6f"),
#                         "dist_from_center": st.column_config.NumberColumn("Dist from Center (m)", format="%.1f"),
#                         "mean_dist_m":      st.column_config.NumberColumn("Normal Range (m)"),
#                         "threshold_m":      st.column_config.NumberColumn("Threshold (m)"),
#                     },
#                     hide_index=True, width="stretch",
#                 )
#             else:
#                 st.success("✓ No anomalies detected at current sensitivity.")

#         fig.update_layout(
#             map_style=map_styles[style_choice],
#             margin={"r": 0, "t": 40, "l": 0, "b": 0},
#             legend_title_text="Target",
#         )
#         st.plotly_chart(fig, width="stretch")

#     # ── Tab 2 — Timeline ──────────────────────────────────────────────────
#     with tab2:
#         st.markdown("#### Sighting Timeline")
#         st.markdown("""
#         Each dot represents a single sighting, plotted by time (x-axis) and target (y-axis).
#         Useful for identifying active periods, gaps in sightings, and whether multiple targets 
#         are active simultaneously — which may indicate coordinated movement.
#         Hover over any point to see full sighting details.
#         """)
#         fig2 = px.scatter(
#             filtered, x="last_seen", y="target",
#             color="target", color_discrete_map=color_map,
#             hover_data={"lat": True, "lon": True, "last_seen": True, "target": True},
#             height=400, title="Sighting Timeline by Target",
#         )
#         fig2.update_layout(
#             yaxis=dict(tickmode="linear", dtick=1),
#             margin={"t": 40}, legend_title_text="Target",
#         )
#         st.plotly_chart(fig2, width="stretch")

#     # ── Tab 3 — Paths ─────────────────────────────────────────────────────
#     with tab3:
#         st.markdown("#### Target Movement Paths")
#         st.markdown("""
#         Lines connect each target's sightings in chronological order, showing the sequence 
#         of movement over time. Dots mark individual sighting points.
        
#         Note: lines represent the order of sightings, not actual routes taken — 
#         the target may have taken any path between two recorded points.
#         Click a target in the legend to toggle its path on or off.
#         """)
#         path_df = filtered.sort_values(["target", "last_seen"])
#         fig3    = go.Figure()

#         for target_id, group in path_df.groupby("target"):
#             color = color_map[str(target_id)]
#             fig3.add_trace(go.Scattermap(
#                 lat=group["lat"], lon=group["lon"], mode="lines",
#                 line=dict(width=2, color=color),
#                 name=f"Target {target_id}", legendgroup=f"target_{target_id}",
#                 showlegend=False,
#             ))
#             fig3.add_trace(go.Scattermap(
#                 lat=group["lat"], lon=group["lon"], mode="markers",
#                 marker=dict(size=8, color=color),
#                 name=f"Target {target_id}", legendgroup=f"target_{target_id}",
#                 showlegend=True,
#                 hovertemplate=(
#                     "<b>Target %{customdata[0]}</b><br>"
#                     "Time: %{customdata[1]}<br>"
#                     "Lat: %{lat:.6f}<br>"
#                     "Lon: %{lon:.6f}<extra></extra>"
#                 ),
#                 customdata=group[["target", "last_seen"]].values,
#             ))

#         fig3.update_layout(
#             map_style=map_styles[style_choice],
#             map=dict(center=dict(lat=filtered["lat"].mean(), lon=filtered["lon"].mean()), zoom=12),
#             height=550, margin={"r": 0, "t": 10, "l": 0, "b": 0},
#             legend_title_text="Target",
#         )
#         st.plotly_chart(fig3, width="stretch")

#     # ── Tab 4 — Animation ─────────────────────────────────────────────────
#     with tab4:
#         st.markdown("#### Target Path Animation")
#         st.markdown("""
#         Watch sightings accumulate over time as an animation. Each frame adds the next recorded 
#         sighting, drawing the path as it builds. 
        
#         Select multiple targets simultaneously to look for **convergence patterns** — 
#         moments where two targets appear in the same area at the same time.
        
#         - **Date Range** — narrow the animation to a specific period
#         - **Speed** — controls milliseconds per frame. Lower = faster playback
#         - Use ▶ Play to start, ⏸ Pause to stop, or drag the slider to any point in time
#         """)

#         col1, col2, col3 = st.columns([2, 2, 1])
#         with col1:
#             anim_targets = st.multiselect(
#                 "Select Targets",
#                 options=all_targets, default=[all_targets[0]],
#                 format_func=lambda x: f"Target {x}",
#                 key="anim_targets",
#             )
#         with col2:
#             anim_df_full = df[df["target"].isin(anim_targets)].copy() if anim_targets else df.copy()
#             min_date = anim_df_full["last_seen"].min().date()
#             max_date = anim_df_full["last_seen"].max().date()
#             date_range = st.date_input(
#                 "Date Range", value=(min_date, max_date),
#                 min_value=min_date, max_value=max_date,
#                 key="anim_date_range",
#             )
#         with col3:
#             speed_ms = st.slider(
#                 "Speed (ms/frame)",
#                 min_value=100, max_value=2000,  step=100,
#                 value=st.session_state["anim_speed"],
#                 key="anim_speed"
#             )

#         if not anim_targets:
#             st.info("Select at least one target to animate.")
#         elif len(date_range) < 2:
#             st.info("Select a start and end date.")
#         else:
#             start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
#             anim_df = anim_df_full[
#                 (anim_df_full["last_seen"] >= start_date) &
#                 (anim_df_full["last_seen"] <= end_date)
#             ].copy()
#             anim_df["target"] = anim_df["target"].astype(str)
#             anim_df = anim_df.sort_values("last_seen").reset_index(drop=True)

#             if anim_df.empty:
#                 st.warning("No sightings in selected date range.")
#             else:
#                 timestamps = sorted(anim_df["last_seen"].unique())
#                 frames = []
#                 for ts in timestamps:
#                     slice_df = anim_df[anim_df["last_seen"] <= ts].copy()
#                     slice_df["frame"] = str(ts)
#                     frames.append(slice_df)
#                 animated_df = pd.concat(frames).reset_index(drop=True)
#                 target_colors = {str(t): color_map[str(t)] for t in anim_targets}
#                 first_frame   = animated_df[animated_df["frame"] == str(timestamps[0])]
#                 fig4 = go.Figure()

#                 for t in [str(t) for t in anim_targets]:
#                     color = target_colors[t]
#                     grp   = first_frame[first_frame["target"] == t]
#                     fig4.add_trace(go.Scattermap(
#                         lat=grp["lat"], lon=grp["lon"], mode="lines",
#                         line=dict(width=2, color=color),
#                         name=f"Target {t}", legendgroup=f"t_{t}", showlegend=False,
#                     ))
#                     fig4.add_trace(go.Scattermap(
#                         lat=grp["lat"], lon=grp["lon"], mode="markers",
#                         marker=dict(size=8, color=color),
#                         name=f"Target {t}", legendgroup=f"t_{t}", showlegend=True,
#                         hovertemplate=(
#                             "<b>Target %{customdata[0]}</b><br>"
#                             "Time: %{customdata[1]}<br>"
#                             "Lat: %{lat:.6f}<br>"
#                             "Lon: %{lon:.6f}<extra></extra>"
#                         ),
#                         customdata=grp[["target", "last_seen"]].values,
#                     ))

#                 plotly_frames = []
#                 for ts in timestamps:
#                     frame_df   = animated_df[animated_df["frame"] == str(ts)]
#                     frame_data = []
#                     for t in [str(t) for t in anim_targets]:
#                         color = target_colors[t]
#                         grp   = frame_df[frame_df["target"] == t]
#                         frame_data.append(go.Scattermap(
#                             lat=grp["lat"], lon=grp["lon"], mode="lines",
#                             line=dict(width=2, color=color),
#                         ))
#                         frame_data.append(go.Scattermap(
#                             lat=grp["lat"], lon=grp["lon"], mode="markers",
#                             marker=dict(size=8, color=color),
#                             customdata=grp[["target", "last_seen"]].values,
#                         ))
#                     plotly_frames.append(go.Frame(data=frame_data, name=str(ts)))

#                 fig4.frames = plotly_frames
#                 fig4.update_layout(
#                     map_style=map_styles[style_choice],
#                     map=dict(center=dict(lat=anim_df["lat"].mean(), lon=anim_df["lon"].mean()), zoom=12),
#                     height=580, margin={"r": 0, "t": 10, "l": 0, "b": 0},
#                     legend_title_text="Target",
#                     updatemenus=[dict(
#                         type="buttons", showactive=False,
#                         y=-0.05, x=0.5, xanchor="center",
#                         buttons=[
#                             dict(label="▶ Play", method="animate",
#                                  args=[None, {"frame": {"duration": speed_ms, "redraw": True},
#                                               "fromcurrent": True, "transition": {"duration": 0}}]),
#                             dict(label="⏸ Pause", method="animate",
#                                  args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}]),
#                         ]
#                     )],
#                     sliders=[dict(
#                         steps=[dict(method="animate", args=[[str(ts)], {
#                             "frame": {"duration": speed_ms, "redraw": True}, "mode": "immediate",
#                         }], label=str(ts)) for ts in timestamps],
#                         x=0.0, y=-0.12, len=1.0,
#                         currentvalue=dict(prefix="Time: ", visible=True, xanchor="center"),
#                     )]
#                 )
#                 st.plotly_chart(fig4, width="stretch")

#     # ── Tab 5 — Heatmap ───────────────────────────────────────────────────
#     with tab5:
#         st.markdown("#### Sighting Density Heatmap")
#         st.markdown("""
#         A density map showing where targets spend the most time collectively. 
#         Brighter, hotter areas indicate higher concentrations of sightings.
        
#         Useful for identifying shared hotspots across all targets — areas that are 
#         frequently visited regardless of which target is being tracked.
        
#         - **Heat Radius** — controls how far each sighting point bleeds into its neighbors. 
#           Larger radius = smoother, broader blobs. Smaller = tighter, more precise hotspots.
        
#         The bar chart below breaks down sighting counts per target so you can see 
#         if one target is driving the density or if it is evenly distributed.
#         """)

#         radius_px = st.slider(
#             "Heat Radius",
#             min_value=5, max_value=50, step=5,
#             value=st.session_state["heatmap_radius"],
#             key="heatmap_radius"
#         )

#         heat_df = get_heatmap_data(df, targets=selected if selected else None)

#         if heat_df.empty:
#             st.warning("No data for selected targets.")
#         else:

#             fig5h = go.Figure()
#             grid_df = build_heatmap_grid(heat_df)
#             fig5h.add_trace(go.Densitymap(
#                 lat=grid_df["lat"], lon=grid_df["lon"],
#                 z=grid_df["weight"],
#                 radius=radius_px,
#                 colorscale="Inferno", showscale=True,
#                 colorbar=dict(title="Density"),
#                 hoverinfo="skip",
#             ))
#             fig5h.update_layout(
#                 map_style=map_styles[style_choice],
#                 map=dict(center=dict(lat=heat_df["lat"].mean(), lon=heat_df["lon"].mean()), zoom=12),
#                 height=500, margin={"r": 0, "t": 10, "l": 0, "b": 0},
#             )
#             st.plotly_chart(fig5h, width="stretch")

#             st.markdown("#### Sighting Count by Target")
#             counts = (
#                 heat_df.groupby("target").size()
#                 .reset_index(name="sightings")
#                 .sort_values("sightings", ascending=False)
#             )
#             counts["target_str"] = counts["target"].astype(str)
#             fig5b = px.bar(
#                 counts, x="target_str", y="sightings",
#                 color="target_str", color_discrete_map=color_map,
#                 labels={"target_str": "Target", "sightings": "Sightings"},
#                 height=280,
#             )
#             fig5b.update_layout(
#                 showlegend=False, margin={"t": 10},
#                 xaxis_title="Target", yaxis_title="Total Sightings",
#             )
#             st.plotly_chart(fig5b, width="stretch")
#                         # ── Hour distribution across all targets ──────────────────
#             st.markdown("#### Activity by Hour of Day")
#             st.caption("Collective view — when are targets most active across all sightings?")

#             heat_df["hour"] = pd.to_datetime(
#                 df[df["target"].isin(selected if selected else all_targets)]["last_seen"]
#             ).dt.hour.values

#             hourly = (
#                 heat_df.groupby("hour")
#                 .size()
#                 .reset_index(name="sightings")
#             )

#             fig5c = px.bar(
#                 hourly, x="hour", y="sightings",
#                 labels={"hour": "Hour of Day", "sightings": "Total Sightings"},
#                 height=250,
#                 color_discrete_sequence=["#4f8ef7"],
#             )
#             fig5c.update_layout(
#                 margin={"t": 10},
#                 xaxis=dict(tickmode="linear", dtick=1),
#             )
#             st.plotly_chart(fig5c, width="stretch")

#     # ── Tab 6 — Convergence ───────────────────────────────────────────────
#     with tab6:
#         st.markdown("#### Convergence Detection")
#         st.markdown("""
#         Identifies moments when two targets were recorded at the same location within 
#         a defined time window — a potential meeting or coordinated movement event.
        
#         Two conditions must both be true for a convergence to be flagged:
#         - **Distance** — the two sightings must be within X meters of each other
#         - **Time Delta** — the two sightings must be within X minutes of each other
        
#         A sighting at the same location 3 days apart is **not** convergence — 
#         both spatial and temporal proximity are required simultaneously.
        
#         - **Max Distance** — how close the two sightings must be geographically (meters)
#         - **Max Time Delta** — how close in time the two sightings must be (minutes)
        
#         The map plots each convergence event at the midpoint between the two sightings. 
#         Dot size reflects proximity (smaller = closer). 
#         Color reflects time delta (darker red = closer in time = higher confidence event).

#         Set your distance and time thresholds above, then click **Apply** to run the detection.
#         Results persist when switching tabs — you will not lose them by navigating away.
#         """)
#         col1, col2, col3 = st.columns([2, 2, 1])
#         with col1:
#             max_meters = st.slider(
#                 "Max Distance (meters)",
#                 min_value=10, max_value=500, step=10,
#                 value=st.session_state["max_meters"],
#                 key="max_meters",
#             )
#         with col2:
#             max_minutes = st.slider(
#                 "Max Time Delta (minutes)",
#                 min_value=15, max_value=240, step=15,
#                 value=st.session_state["max_minutes"],
#                 key="max_minutes",
#             )
#         with col3:
#             st.markdown("&nbsp;", unsafe_allow_html=True)
#             run_conv = st.button("Apply", use_container_width=True, type="primary")

#         if "conv_df" not in st.session_state:
#             st.session_state.conv_df = None
            
#         if run_conv:
#             st.session_state.conv_df = get_convergences(
#                 df, max_meters=max_meters, max_minutes=max_minutes
#             )

#         conv_df = st.session_state.conv_df
#         if conv_df is None:
#             st.info("Set parameters above then click **Apply** to run convergence detection.")
#         else:
#             if conv_df.empty:
#                 st.warning("No convergence events found. Try increasing distance or time window.")
#             else:
#                 st.success(f"**{len(conv_df)} convergence event(s) detected.**")
#                 st.markdown("##### Events")
#                 st.dataframe(
#                     conv_df[[
#                         "target_a", "target_b", "time_a", "time_b",
#                         "dt_minutes", "distance_m", "lat", "lon"
#                     ]].sort_values("dt_minutes"),
#                     column_config={
#                         "target_a":   st.column_config.NumberColumn("Target A"),
#                         "target_b":   st.column_config.NumberColumn("Target B"),
#                         "time_a":     st.column_config.DatetimeColumn("Time A", format="YYYY-MM-DD HH:mm"),
#                         "time_b":     st.column_config.DatetimeColumn("Time B", format="YYYY-MM-DD HH:mm"),
#                         "dt_minutes": st.column_config.NumberColumn("Δ Minutes"),
#                         "distance_m": st.column_config.NumberColumn("Distance (m)"),
#                         "lat":        st.column_config.NumberColumn("Lat", format="%.6f"),
#                         "lon":        st.column_config.NumberColumn("Lon", format="%.6f"),
#                     },
#                     hide_index=True, width="stretch",
#                 )
    
#                 st.markdown("##### Convergence Locations")
#                 fig6 = px.scatter_map(
#                     conv_df, lat="lat", lon="lon",
#                     size="distance_m", color="dt_minutes",
#                     color_continuous_scale="Reds_r",
#                     hover_data={
#                         "target_a": True, "target_b": True,
#                         "dt_minutes": True, "distance_m": True,
#                         "lat": True, "lon": True,
#                     },
#                     zoom=12, height=450,
#                     title="Convergence Locations — smaller dot = closer proximity",
#                 )
#                 fig6.update_layout(
#                     map_style=map_styles[style_choice],
#                     margin={"r": 0, "t": 40, "l": 0, "b": 0},
#                     coloraxis_colorbar=dict(title="Δ Minutes"),
#                 )
#                 st.plotly_chart(fig6, width="stretch")    

# def render_temporal():
#     st.markdown("## Temporal Analysis")
#     st.markdown("""
#     Time-based behavioral analysis across all tracked targets. This section answers:
    
#     - **When** are targets active — which hours, which days of the week?
#     - **What routines exist** — repeated presence at the same place at the same time?
    
#     The **Hour × Day heatmap** can be viewed per target or combined across all targets. 
#     Per-target reveals individual schedules. Combined reveals collective hotspots and 
#     whether multiple targets share active periods — a potential indicator of coordination.
    
#     The **Routines** tab is the most actionable output — it flags confirmed behavioral 
#     patterns you can act on predictively.
    
#     Use the target filter below to focus on a subset across both tabs.
#     """)

#     df        = load_data()
#     color_map = assign_target_colors([str(t) for t in sorted(df["target"].unique())])

#     # ── Global filter ─────────────────────────────────────────────────────
#     all_targets = sorted(df["target"].unique())
#     selected    = st.multiselect(
#         "Filter by Target",
#         options=all_targets,
#         default=st.session_state["temporal_selected"] if st.session_state["temporal_selected"] else all_targets,
#         format_func=lambda x: f"Target {x}",
#         key="temporal_selected",
#     )
#     filtered = df[df["target"].isin(selected)].copy() if selected else df.copy()

#     tab1, tab2 = st.tabs(["⏰ Hour × Day", "🔁 Routines"])

#     # ── Tab 1 — Hour × Day heatmap ────────────────────────────────────────
#     with tab1:
#         st.markdown("#### Activity Pattern — Hour × Day of Week")
#         st.markdown("""
#         Each cell represents a **hour + day of week combination**. 
#         Color intensity = number of sightings at that time slot. 
#         Numbers inside each cell show the exact count.
        
#         **What to look for:**
#         - **Bright clusters** — the target is consistently active at that hour on that day. High-confidence routine.
#         - **Isolated bright cells** — one-off activity at an unusual time. Potentially anomalous.
#         - **Dark rows or columns** — the target is never active on a given day or hour range.
#         - **Combined view** — if two targets share the same bright cells, they are active at the 
#           same times. Cross-reference with Convergence Detection to see if they were also 
#           at the same location.
        
#         Weekend rows (Saturday, Sunday) are lightly shaded.
#         """)

#         col1, col2 = st.columns([2, 1])
#         with col1:
#             view_mode = st.radio(
#                 "View",
#                 options=["Per Target", "Combined"],
#                 horizontal=True,
#                 key="hour_dow_mode",
#             )
#         with col2:
#             focus_target = None
#             if view_mode == "Per Target":
#                 focus_target = st.selectbox(
#                     "Select Target",
#                     options=selected if selected else all_targets,
#                     format_func=lambda x: f"Target {x}",
#                     key="hour_dow_target",
#                 )

#         # ── Build plot dataframe ──────────────────────────────────────
#         plot_df = (
#             filtered[filtered["target"] == focus_target].copy()
#             if view_mode == "Per Target" and focus_target is not None
#             else filtered.copy()
#         )

#         day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

#         heatmap_df = (
#             plot_df
#             .assign(
#                 hour=plot_df["last_seen"].dt.hour,
#                 dow=plot_df["last_seen"].dt.strftime("%A"),
#             )
#             .groupby(["dow", "hour"])
#             .size()
#             .reset_index(name="sightings")
#         )

#         if heatmap_df.empty:
#             st.info("No data for selected target.")
#         else:
#             fig1 = px.density_heatmap(
#                 heatmap_df,
#                 x="hour",
#                 y="dow",
#                 z="sightings",
#                 category_orders={"dow": day_order},
#                 color_continuous_scale="Greens",
#                 height=400,
#                 labels={
#                     "hour":     "Hour of Day",
#                     "dow":      "Day of Week",
#                     "sightings": "Sightings",
#                 },
#                 text_auto=True,
#             )
#             fig1.update_layout(
#                 margin={"t": 10},
#                 xaxis=dict(tickmode="linear", dtick=1, title="Hour of Day"),
#                 yaxis_title="Day of Week",
#                 coloraxis_colorbar=dict(title="Sightings"),
#             )

#             # Shade weekend rows
#             for day in ["Saturday", "Sunday"]:
#                 fig1.add_hrect(
#                     y0=day_order.index(day) - 0.5,
#                     y1=day_order.index(day) + 0.5,
#                     fillcolor="rgba(255,255,255,0.03)",
#                     layer="below", line_width=0,
#                 )

#             st.plotly_chart(fig1, width="stretch")

#     # ── Tab 2 — Routines ──────────────────────────────────────────────────
#     with tab2:
#         st.markdown("#### Detected Routines")
#         st.markdown("""
#         Automatically surfaces behavioral patterns — cases where a target was seen 
#         at the **same location**, during the **same 2-hour time block**, on the **same day of week**, 
#         a minimum number of times.
        
#         This is the most actionable output in this section. A confirmed routine means 
#         you can predict where a target will be before they get there.
        
#         **How it works:**
#         - Sightings are clustered by location within the radius you set
#         - Each sighting is bucketed into a 2-hour time block (e.g. 08:00–10:00)
#         - Each sighting is tagged with its day of week
#         - Any combination of target + location + time block + day that repeats 
#           at or above the minimum threshold is flagged
        
#         **Controls:**
#         - **Minimum Occurrences** — how many times the pattern must repeat to be flagged. 
#           Lower = more patterns, higher noise. Higher = only strong confirmed patterns.
#         - **Location Cluster Radius** — filters which routines are shown based on location 
#           proximity. The underlying clustering was fixed at pipeline time (10m radius). 
#           Increasing this slider broadens which location groups are included — it does not 
#           recompute how sightings are grouped.
        
#         Each card: target · location · time block · day of week · occurrences.
        
#         """)

#         col1, col2 = st.columns(2)
#         with col1:
#             min_occ = st.slider(
#                 "Minimum Occurrences",
#                 min_value=2, max_value=10,step=1,
#                 value=st.session_state["routine_min"],
#                 key="routine_min"
#             )
#         with col2:
#             cluster_r = st.slider(
#                 "Location Cluster Radius (m)",
#                 min_value=10, max_value=200, step=10,
#                 value=st.session_state["routine_radius"],
#                 key="routine_radius"
#             )

#         routines = get_routines(filtered, max_meters=cluster_r, min_occurrences=min_occ)

#         if routines.empty:
#             st.warning("No routines detected. Try lowering minimum occurrences or increasing cluster radius.")
#         else:
#             st.success(f"**{len(routines)} routine(s) detected.**")

#             rcol1, rcol2 = st.columns([3, 1])
#             with rcol1:
#                 st.caption(f"Showing top 10 of {len(routines)} routines by occurrences.")
#             with rcol2:
#                 show_all_routines = st.toggle("Show All", key="show_all_routines", value=False)

#             display_routines = routines if show_all_routines else routines.head(10)

#             with st.container(height=500):
#                 for _, row in display_routines.iterrows():
#                     color = color_map[str(row["target"])]
#                     st.markdown(f"""
#                     <div style="
#                         border-left: 3px solid {color};
#                         padding: 10px 16px;
#                         margin-bottom: 10px;
#                         background: rgba(255,255,255,0.02);
#                         border-radius: 4px;
#                     ">
#                         <span style="color:{color}; font-weight:700;">Target {row['target']}</span>
#                         &nbsp;·&nbsp;
#                         <span style="color:#e4e6f0;">📍 {row['location_label']}</span>
#                         &nbsp;·&nbsp;
#                         <span style="color:#aaa;">🕐 {row['hour_range']}</span>
#                         &nbsp;·&nbsp;
#                         <span style="color:#aaa;">📅 {row['dow']}</span>
#                         &nbsp;·&nbsp;
#                         <span style="color:#f0c040;">🔁 {row['occurrences']}x</span>
#                     </div>
#                     """, unsafe_allow_html=True)
# def network():
#     st.markdown("## Location Intelligence")
#     st.markdown("""
#     Location-based analysis across all targets. This section answers two questions:
    
#     - **Where does each target repeatedly return?** — Dwell detection flags locations 
#       visited above a minimum threshold, suggesting home bases, meeting points, or routine stops.
#     - **Which locations are shared between targets?** — The shared location table and network 
#       graph show places visited by more than one target — a key indicator of relationship 
#       or coordination. The table gives the details, the graph makes the relationships visible.
    
#     These two views build on each other: dwell identifies important locations per target, 
#     shared locations identify overlap between targets.
#     """)

#     df          = load_data()
#     all_targets = sorted(df["target"].unique())
#     color_map   = assign_target_colors([str(t) for t in all_targets])

#     # ── Pre-compute clustered df once — used in both tabs ─────────────────
#     clustered_df = cluster_locations(df, max_meters=10)

#     tab1, tab2 = st.tabs(["📍 Dwell Detection", "🔗 Shared Locations & Network"])

#     # ── Tab 1 — Dwell Detection ───────────────────────────────────────────
#     with tab1:
#         st.markdown("#### Dwell Detection")
#         st.markdown("""
#         Flags locations where a single target was observed repeatedly — above the minimum 
#         visit threshold you set. A dwell location suggests a place of significance: 
#         a home address, workplace, regular meeting point, or routine stop.
        
#         **Controls:**
#         - **Minimum Visits** — how many times a target must appear at a location to be flagged. 
#           Lower = more locations flagged, higher noise. Higher = only the most significant spots.
#         - **Cluster Radius** — filters results to locations clustered within this radius. 
#           Note: the underlying location grouping was computed at pipeline time using a 10m radius. 
#           Increasing this slider surfaces locations across a wider area — it does not regroup 
#           raw GPS points.
        
#         Dot size on the map scales with visit count — larger dots are higher-frequency locations.
#         """)

#         col1, col2 = st.columns(2)
#         with col1:
#             min_visits = st.slider(
#                 "Minimum Visits to Flag",
#                 min_value=2, max_value=10, step=1,
#                 value=st.session_state["dwell_min_visits"],
#                 key="dwell_min_visits"
#             )
#         with col2:
#             cluster_radius = st.slider(
#                 "Cluster Radius (meters)",
#                 min_value=5, max_value=100, step=5,
#                 value=st.session_state["dwell_cluster_radius"],
#                 key="dwell_cluster_radius",
#             )

#         dwell_df = get_dwell_locations(df, min_visits=min_visits, max_meters=cluster_radius)

#         if dwell_df.empty:
#             st.warning("No dwell locations found. Try lowering minimum visits or increasing cluster radius.")
#         else:
#             st.success(f"**{len(dwell_df)} dwell location(s) detected across {dwell_df['target'].nunique()} target(s).**")

#             dwell_targets  = sorted(dwell_df["target"].unique())
#             dwell_selected = st.multiselect(
#                 "Filter by Target",
#                 options=dwell_targets,
#                 default=dwell_targets,
#                 format_func=lambda x: f"Target {x}",
#                 key="dwell_targets",
#             )
#             dwell_filtered = (
#                 dwell_df[dwell_df["target"].isin(dwell_selected)].copy()
#                 if dwell_selected else dwell_df.copy()
#             )

#             dcol1, dcol2 = st.columns([3, 1])
#             with dcol1:
#                 st.caption(f"Showing top 10 of {len(dwell_filtered)} locations by visit count.")
#             with dcol2:
#                 show_all_dwell = st.toggle("Show All", key="show_all_dwell", value=False)

#             display_dwell = dwell_filtered if show_all_dwell else dwell_filtered.head(10)

#             st.dataframe(
#                 display_dwell[["target", "location_label", "visit_count", "first_seen", "last_seen"]],
#                 column_config={
#                     "target":         st.column_config.NumberColumn("Target"),
#                     "location_label": st.column_config.TextColumn("Location (lat, lon)"),
#                     "visit_count":    st.column_config.NumberColumn("Visits"),
#                     "first_seen":     st.column_config.DatetimeColumn("First Seen", format="YYYY-MM-DD HH:mm"),
#                     "last_seen":      st.column_config.DatetimeColumn("Last Seen",  format="YYYY-MM-DD HH:mm"),
#                 },
#                 hide_index=True, width="stretch", height=500,
#             )
#             dwell_filtered["target_str"] = dwell_filtered["target"].astype(str)
#             fig1 = px.scatter_map(
#                 dwell_filtered,
#                 lat="lat", lon="lon",
#                 color="target_str",
#                 color_discrete_map=color_map,
#                 size="visit_count", size_max=30,
#                 hover_data={
#                     "target_str":     True,
#                     "location_label": True,
#                     "visit_count":    True,
#                     "first_seen":     True,
#                     "last_seen":      True,
#                     "lat":            True,
#                     "lon":            True,
#                 },
#                 zoom=12, height=480,
#             )
#             fig1.update_layout(
#                 map_style="carto-darkmatter",
#                 margin={"r": 0, "t": 10, "l": 0, "b": 0},
#                 legend_title_text="Target",
#             )
#             st.plotly_chart(fig1, width="stretch")

#     # ── Tab 2 — Shared Locations + Network ───────────────────────────────
#     with tab2:
#         st.markdown("#### Shared Location Analysis")
#         st.markdown("""
#         Locations visited by **more than one target**, shown as both a table and a network graph.
        
#         The table gives precise details — which targets were seen there, total visit count, 
#         and the time range of recorded sightings at that location.
#         The network graph below makes the relationships immediately visible.
        
#         **Note:** a shared location does not confirm a meeting — targets may have visited 
#         at different times. Cross-reference with **Convergence Detection** to confirm 
#         whether visits were temporally close enough to constitute a meeting.
#         """)

#         shared_locs = get_shared_locations_table(clustered_df)

#         if shared_locs.empty:
#             st.info("No shared locations detected within 10 meters.")
#         else:
#             st.success(f"**{len(shared_locs)} shared location(s) detected.**")

#             slcol1, slcol2 = st.columns([3, 1])
#             with slcol1:
#                 st.caption(f"Showing top 10 of {len(shared_locs)} shared locations by visit count.")
#             with slcol2:
#                 show_all_shared = st.toggle("Show All", key="show_all_shared", value=False)

#             display_shared = shared_locs if show_all_shared else shared_locs.head(10)

#             st.dataframe(
#                 display_shared,
#                 column_config={
#                     "location_label": st.column_config.TextColumn("Location (lat, lon)"),
#                     "targets":        st.column_config.TextColumn("Targets Present"),
#                     "visit_count":    st.column_config.NumberColumn("Total Visits"),
#                     "first_seen":     st.column_config.DatetimeColumn("First Seen", format="YYYY-MM-DD HH:mm"),
#                     "last_seen":      st.column_config.DatetimeColumn("Last Seen",  format="YYYY-MM-DD HH:mm"),
#                 },
#                 hide_index=True, width="stretch", height=500,
#             )

#         st.markdown("#### Target–Location Network")
#         st.markdown("""
#         A force-directed network graph connecting targets to every location where they were sighted.
        
#         - **Colored circles** — targets, each with a unique color matching the rest of the app
#         - **Yellow diamonds** — location clusters (points within 10 meters grouped as one node)
#         - **Edges** — a line between a target and a location means that target was seen there
        
#         **What to look for:**
#         - **Two targets connected to the same location node** — they share that location. 
#           The more shared nodes, the stronger the implied relationship.
#         - **Highly connected location nodes** — hotspots visited by many targets.
#         - **Isolated target nodes** — targets with no shared locations, operating independently.
        
#         Drag nodes to rearrange. Scroll to zoom. Hover for details.
#         """)
#         render_network(clustered_df, color_map)
        
# # ── Update main() ─────────────────────────────────────────────────────
# def main():
#     # General page layout settings
#     apply_config()

#     # Header
#     render_header()

#     # Pipeline staleness indicator
#     st.caption(pipeline_age_label())

#     # Initialize default values
#     init_session_state()

#     # Intel card ( High level info, about target)
#     render_target_intel()
#     st.divider()

#     # Plotly charts (geo, path, timelaps, convergence) 
#     render_charts()
#     st.divider()

#     # Common times/days/patterns
#     render_temporal()
#     st.divider()

#     # Common locations
#     network()
#     st.divider()

#     # Footer
#     render_footer()

# if __name__ == "__main__":
#     main()


### Removed the FRAME BUILDER (VIDEO), PATH 
from utils.streamlit_config import apply_config, render_header, render_footer
from utils.data import (
    load_data, get_last_seen_table, get_convergences,
    cluster_locations, get_shared_locations_table,
    get_dwell_locations, get_heatmap_data,
    get_target_summary, haversine_meters,
    haversine_meters_vectorized,
    get_routines, get_target_home_range,
    get_iqr_box, get_dbscan_hulls, get_anomalies,
    get_default_targets,
)
from utils.render import build_heatmap_grid
from utils.network import render_network
from utils.db import pipeline_age_label
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd



def init_session_state():
    defaults = {
        "max_meters":           50,
        "max_minutes":          120,
        "decay_rate":           0.05,
        "sensitivity":          "Moderate",
        "range_method":         "IQR Box",
        "heatmap_radius":       20,
        "routine_min":          3,
        "routine_radius":       50,
        "anim_speed":           600,
        "dwell_min_visits":     3,
        "dwell_cluster_radius": 10,
        "show_home_range":      False,
        "map_style":            "Street",
        "charts_selected":      None,
        "temporal_selected":    None,
        "location_selected":    None,
        "show_all_routines":    False,
        "show_all_dwell":       False,
        "show_all_shared":      False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Default target selections — top 10 by most recent activity
    # Only runs once per session; get_default_targets is cached at process level
    for key in ["charts_selected", "temporal_selected", "location_selected"]:
        if st.session_state[key] is None:
            st.session_state[key] = get_default_targets(10)


def assign_target_colors(targets):
    palette = px.colors.qualitative.Safe
    return {t: palette[i % len(palette)] for i, t in enumerate(sorted(targets))}


def render_target_intel():
    st.markdown("## Target Intelligence")
    st.markdown("""
    Consolidated intelligence profile for each tracked target. 
    Cards display the most operationally relevant information at a glance — 
    total sightings, active days, first and last seen timestamps, last known coordinates, 
    and total distance traveled between sightings.
    
    Use the **search bar** to filter by target number. By default the top 10 targets are shown — 
    toggle **Show All** to see the full list.
    
    Click **▶ Detail** on any card to expand a full intelligence breakdown inline, including:
    - Complete sighting history with timestamps and coordinates
    - Movement analysis — distance from origin and speed between sightings over time
    - Individual sighting map showing all recorded positions
    
    *Distance traveled is calculated using the Haversine formula — 
    actual ground distance between consecutive sightings in chronological order.*
    """)

    df      = load_data()
    summary = get_target_summary(df)

    last_seen_df = get_last_seen_table(df)
    summary = summary.merge(
        last_seen_df[["target", "lat", "lon"]],
        on="target", how="left",
    )
    summary = summary.rename(columns={"lat": "last_lat", "lon": "last_lon"})

    color_map = assign_target_colors([str(t) for t in summary["target"].tolist()])

    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input(
            "Search Target",
            placeholder="Type target number...",
            label_visibility="collapsed",
        )
    with col2:
        show_all = st.toggle("Show All", value=False)

    filtered_summary = (
        summary[summary["target"].astype(str).str.contains(search.strip())]
        if search else summary
    )
    display_summary = filtered_summary if show_all else filtered_summary.head(10)

    if not show_all and len(filtered_summary) > 10:
        st.caption(f"Showing 10 of {len(filtered_summary)} targets. Toggle 'Show All' to see more.")

    if "expanded_target" not in st.session_state:
        st.session_state.expanded_target = None

    rows = [display_summary.iloc[i:i+3] for i in range(0, len(display_summary), 3)]

    for row_df in rows:
        cols = st.columns(3)

        for i, (_, row) in enumerate(row_df.iterrows()):
            color  = color_map[str(row["target"])]
            target = row["target"]

            with cols[i % 3]:
                st.markdown(f"""
                <div style="
                    border: 1px solid {color};
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 4px;
                    background: rgba(255,255,255,0.02);
                ">
                    <div style="color:{color}; font-weight:700; font-size:1rem; margin-bottom:8px;">
                        Target {target}
                    </div>
                    <div style="font-size:0.82rem; line-height:1.8; color:#c8cad4;">
                        🔍 <b>Sightings:</b> {row['total_sightings']}<br>
                        📅 <b>Active Days:</b> {row['active_days']}<br>
                        🕐 <b>First Seen:</b> {row['first_seen'].strftime('%Y-%m-%d %H:%M')}<br>
                        🕑 <b>Last Seen:</b> {row['last_seen'].strftime('%Y-%m-%d %H:%M')}<br>
                        📍 <b>Last Location:</b> ({row['last_lat']:.5f}, {row['last_lon']:.5f})<br>
                        🛣️ <b>Distance:</b> {row['distance_km']} km
                    </div>
                </div>
                """, unsafe_allow_html=True)

                is_expanded = st.session_state.expanded_target == target
                btn_label   = "▼ Close" if is_expanded else "▶ Detail"
                if st.button(btn_label, key=f"btn_{target}", use_container_width=True):
                    st.session_state.expanded_target = None if is_expanded else target
                    st.rerun()

        row_targets = row_df["target"].tolist()
        if st.session_state.expanded_target in row_targets:
            target = st.session_state.expanded_target
            row    = summary[summary["target"] == target].iloc[0]
            color  = color_map[str(target)]

            st.divider()
            st.markdown(f"#### Target {target} — Detail")
            st.caption(
                f"Full sighting record for Target {target}. "
                f"Movement chart shows distance from first known sighting (left axis) "
                f"and estimated speed between consecutive sightings (right axis, km/h). "
                f"Speed spikes may indicate vehicle use. "
                f"Distance returning toward zero suggests the target is returning to their origin point."
            )

            target_df = df[df["target"] == target].sort_values("last_seen").copy()
            target_df["target"] = target_df["target"].astype(str)
            coords = target_df[["lat", "lon"]].values

            c1, c2, c3 = st.columns([1, 2, 2])

            with c1:
                st.markdown("**Sightings**")
                st.dataframe(
                    target_df[["last_seen", "lat", "lon"]],
                    column_config={
                        "last_seen": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
                        "lat":       st.column_config.NumberColumn("Lat", format="%.5f"),
                        "lon":       st.column_config.NumberColumn("Lon", format="%.5f"),
                    },
                    hide_index=True,
                    width="stretch",
                    height=300,
                )

            with c2:
                st.markdown("**Movement**")
                origin_lat, origin_lon = coords[0][0], coords[0][1]
                target_df["dist_m"] = haversine_meters_vectorized(
                    origin_lat, origin_lon,
                    target_df["lat"], target_df["lon"]
                )
                speeds = [None]
                for j in range(1, len(coords)):
                    dist_m = haversine_meters(
                        coords[j-1][0], coords[j-1][1],
                        coords[j][0],   coords[j][1]
                    )
                    dt_hrs = (
                        target_df["last_seen"].iloc[j] - target_df["last_seen"].iloc[j-1]
                    ).total_seconds() / 3600
                    speeds.append(round(dist_m / 1000 / dt_hrs, 2) if dt_hrs > 0 else 0)
                target_df["speed_kmh"] = speeds

                fig_m = go.Figure()
                fig_m.add_trace(go.Scatter(
                    x=target_df["last_seen"],
                    y=target_df["dist_m"],
                    name="Dist (m)",
                    mode="lines+markers",
                    line=dict(color=color, width=2),
                    yaxis="y1",
                ))
                fig_m.add_trace(go.Scatter(
                    x=target_df["last_seen"],
                    y=target_df["speed_kmh"],
                    name="Speed (km/h)",
                    mode="lines+markers",
                    line=dict(color="rgba(255,200,50,0.8)", width=2, dash="dot"),
                    yaxis="y2",
                ))
                fig_m.update_layout(
                    height=300,
                    margin={"t": 5, "b": 5, "l": 5, "r": 5},
                    yaxis=dict(title="Dist (m)"),
                    yaxis2=dict(
                        title="Speed (km/h)",
                        overlaying="y",
                        side="right",
                        showgrid=False,
                    ),
                    legend=dict(orientation="h", y=-0.35),
                )
                st.plotly_chart(fig_m, width="stretch")

            with c3:
                st.markdown("**Map**")
                fig_map = px.scatter_map(
                    target_df,
                    lat="lat",
                    lon="lon",
                    color="target",
                    color_discrete_map=color_map,
                    hover_data={"lat": True, "lon": True, "last_seen": True},
                    zoom=12,
                    height=300,
                )
                fig_map.update_layout(
                    map_style="carto-darkmatter",
                    margin={"r": 0, "t": 0, "l": 0, "b": 0},
                    showlegend=False,
                )
                st.plotly_chart(fig_map, width="stretch")

            st.divider()


def render_charts():
    st.markdown("## Sightings Analysis")
    st.markdown("""
    Comprehensive geographic and temporal analysis of all target sightings.
    Use the filters below to focus on specific targets. The map style applies across all map-based tabs.
    
    Tabs cover: raw sighting positions, timeline, movement paths, animated path replay, 
    density heatmap, and convergence detection between targets.
    """)

    df = load_data()
    all_targets = sorted(df["target"].unique())

    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.multiselect(
            "Filter by Target",
            options=all_targets,
            default=st.session_state["charts_selected"],
            format_func=lambda x: f"Target {x}",
            key="charts_selected",
        )
    with col2:
        map_styles = {
            "Street":  "open-street-map",
            "Dark":    "carto-darkmatter",
            "Light":   "carto-positron",
            "Blank":   "white-bg",
        }
        style_choice = st.selectbox(
            "Map Style",
            options=list(map_styles.keys()),
            index=list(map_styles.keys()).index(st.session_state["map_style"]),
            key="map_style",
        )

    filtered  = df[df["target"].isin(selected)].copy() if selected else df.copy()
    filtered["target"] = filtered["target"].astype(str)
    color_map = assign_target_colors([str(t) for t in all_targets])

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📍 Map", "📈 Timeline", "🛤️ Paths", "▶️ Animate", "🌡️ Heatmap", "🔴 Convergence"
    ])

    # ── Tab 1 — Sightings map ─────────────────────────────────────────────
    with tab1:
        st.markdown("#### Sightings Map")
        st.markdown("""
        All recorded sightings plotted by geographic position. Each target has a unique color.
        
        **Home Range overlay** — when enabled, draws each target's normal movement area based on 
        historical sightings. Sightings that fall outside this range are flagged as anomalies.
        - **IQR Box** — bounding box built from the 10th–90th percentile of weighted lat/lon values. 
          Simple and fast. Good for targets with roughly rectangular movement patterns.
        - **DBSCAN** — density-based clustering that finds the tightest region where the target 
          most frequently appears, then draws a convex hull around it. Better for irregular patterns.
        - **Recency Decay** — how much weight to give recent vs older sightings when computing 
          the home range. Higher = older sightings fade out faster.
        - **Anomaly Sensitivity** — controls how far outside the normal range a sighting must be 
          before it is flagged. Conservative (3σ) = only extreme outliers. Aggressive (1σ) = 
          flags subtle deviations. Based on each target's own movement standard deviation, 
          so thresholds adapt per target automatically.
        """)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            show_range = st.toggle(
                "Show Home Range",
                value=st.session_state["show_home_range"],
                key="show_home_range",
            )
        with col2:
            range_method = st.radio(
                "Method", options=["IQR Box", "DBSCAN"],
                horizontal=True,
                index=["IQR Box", "DBSCAN"].index(st.session_state["range_method"]),
                key="range_method",
                disabled=not show_range,
            )
        with col3:
            decay_rate = st.slider(
                "Recency Decay",
                min_value=0.01, max_value=0.20, step=0.01,
                value=st.session_state["decay_rate"],
                help="Higher = older sightings matter less",
                key="decay_rate",
                disabled=not show_range,
            )
        with col4:
            sensitivity = st.select_slider(
                "Anomaly Sensitivity",
                options=["Conservative", "Moderate", "Aggressive"],
                value=st.session_state["sensitivity"],
                key="sensitivity",
                disabled=not show_range,
            )

        sensitivity_map = {"Conservative": 3.0, "Moderate": 2.0, "Aggressive": 1.0}
        n_std = sensitivity_map[sensitivity]

        fig = px.scatter_map(
            filtered, lat="lat", lon="lon",
            color="target", color_discrete_map=color_map,
            hover_data={"lat": True, "lon": True, "last_seen": True, "target": True},
            zoom=12, height=550,
            title="Target Sightings — Washington DC",
        )

        if show_range:
            home_ranges = get_target_home_range(filtered, decay_rate=decay_rate)

            if range_method == "IQR Box":
                iqr_boxes = get_iqr_box(filtered, decay_rate=decay_rate)
                for target, box in iqr_boxes.items():
                    color = color_map.get(str(target), "#ffffff")
                    lats  = [box["lat_low"], box["lat_low"],  box["lat_high"], box["lat_high"], box["lat_low"]]
                    lons  = [box["lon_low"], box["lon_high"], box["lon_high"], box["lon_low"],  box["lon_low"]]
                    fig.add_trace(go.Scattermap(
                        lat=lats, lon=lons, mode="lines", fill="toself",
                        fillcolor=color.replace(")", ",0.10)").replace("rgb", "rgba"),
                        line=dict(color=color, width=1.5),
                        name=f"T{target} Range", legendgroup=f"range_{target}",
                        showlegend=True, hoverinfo="skip",
                    ))

            elif range_method == "DBSCAN":
                hulls = get_dbscan_hulls(filtered, decay_rate=decay_rate)
                for target, polygon in hulls.items():
                    if polygon is None:
                        continue
                    color = color_map.get(str(target), "#ffffff")
                    lats  = [p[0] for p in polygon]
                    lons  = [p[1] for p in polygon]
                    fig.add_trace(go.Scattermap(
                        lat=lats, lon=lons, mode="lines", fill="toself",
                        fillcolor=color.replace(")", ",0.10)").replace("rgb", "rgba"),
                        line=dict(color=color, width=1.5),
                        name=f"T{target} Range", legendgroup=f"range_{target}",
                        showlegend=True, hoverinfo="skip",
                    ))

            anomalies = get_anomalies(filtered, home_ranges, n_std=n_std)
            if not anomalies.empty:
                anomalies["target"] = anomalies["target"].astype(str)
                fig.add_trace(go.Scattermap(
                    lat=anomalies["lat"], lon=anomalies["lon"],
                    mode="markers",
                    marker=dict(size=14, color="red", symbol="cross"),
                    name="⚠ Anomaly",
                    hovertemplate=(
                        "<b>⚠ Anomaly</b><br>"
                        "Target: %{customdata[0]}<br>"
                        "Time: %{customdata[1]}<br>"
                        "Dist from center: %{customdata[2]}m<br>"
                        "Normal range: %{customdata[3]}m ± %{customdata[4]}m<br>"
                        "Threshold: %{customdata[5]}m<extra></extra>"
                    ),
                    customdata=anomalies[[
                        "target", "last_seen", "dist_from_center",
                        "mean_dist_m", "std_dist_m", "threshold_m"
                    ]].round({"dist_from_center": 1}).values,
                ))
                st.warning(f"⚠ **{len(anomalies)} anomalous sighting(s)** detected.")
                st.markdown("##### Anomalous Sightings")
                st.caption("Sightings outside each target's adaptive normal movement range, sorted by distance from center.")
                st.dataframe(
                    anomalies[[
                        "target", "last_seen", "lat", "lon",
                        "dist_from_center", "mean_dist_m", "threshold_m"
                    ]].sort_values("dist_from_center", ascending=False),
                    column_config={
                        "target":           st.column_config.NumberColumn("Target"),
                        "last_seen":        st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
                        "lat":              st.column_config.NumberColumn("Lat", format="%.6f"),
                        "lon":              st.column_config.NumberColumn("Lon", format="%.6f"),
                        "dist_from_center": st.column_config.NumberColumn("Dist from Center (m)", format="%.1f"),
                        "mean_dist_m":      st.column_config.NumberColumn("Normal Range (m)"),
                        "threshold_m":      st.column_config.NumberColumn("Threshold (m)"),
                    },
                    hide_index=True, width="stretch",
                )
            else:
                st.success("✓ No anomalies detected at current sensitivity.")

        fig.update_layout(
            map_style=map_styles[style_choice],
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            legend_title_text="Target",
        )
        st.plotly_chart(fig, width="stretch")

    # ── Tab 2 — Timeline ──────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Sighting Timeline")
        st.markdown("""
        Each dot represents a single sighting, plotted by time (x-axis) and target (y-axis).
        Useful for identifying active periods, gaps in sightings, and whether multiple targets 
        are active simultaneously — which may indicate coordinated movement.
        Hover over any point to see full sighting details.
        """)
        fig2 = px.scatter(
            filtered, x="last_seen", y="target",
            color="target", color_discrete_map=color_map,
            hover_data={"lat": True, "lon": True, "last_seen": True, "target": True},
            height=400, title="Sighting Timeline by Target",
        )
        fig2.update_layout(
            yaxis=dict(tickmode="linear", dtick=1),
            margin={"t": 40}, legend_title_text="Target",
        )
        st.plotly_chart(fig2, width="stretch")

    # ── Tab 3 — Paths ─────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### Target Movement Paths")
        st.markdown("""
        Lines connect each target's sightings in chronological order, showing the sequence 
        of movement over time. Dots mark individual sighting points.
        
        Note: lines represent the order of sightings, not actual routes taken — 
        the target may have taken any path between two recorded points.
        Click a target in the legend to toggle its path on or off.
        """)
        path_df = filtered.sort_values(["target", "last_seen"])
        fig3    = go.Figure()

        for target_id, group in path_df.groupby("target"):
            color = color_map[str(target_id)]
            fig3.add_trace(go.Scattermap(
                lat=group["lat"], lon=group["lon"], mode="lines",
                line=dict(width=2, color=color),
                name=f"Target {target_id}", legendgroup=f"target_{target_id}",
                showlegend=False,
            ))
            fig3.add_trace(go.Scattermap(
                lat=group["lat"], lon=group["lon"], mode="markers",
                marker=dict(size=8, color=color),
                name=f"Target {target_id}", legendgroup=f"target_{target_id}",
                showlegend=True,
                hovertemplate=(
                    "<b>Target %{customdata[0]}</b><br>"
                    "Time: %{customdata[1]}<br>"
                    "Lat: %{lat:.6f}<br>"
                    "Lon: %{lon:.6f}<extra></extra>"
                ),
                customdata=group[["target", "last_seen"]].values,
            ))

        fig3.update_layout(
            map_style=map_styles[style_choice],
            map=dict(center=dict(lat=filtered["lat"].mean(), lon=filtered["lon"].mean()), zoom=12),
            height=550, margin={"r": 0, "t": 10, "l": 0, "b": 0},
            legend_title_text="Target",
        )
        st.plotly_chart(fig3, width="stretch")

    # ── Tab 4 — Animation ─────────────────────────────────────────────────
    with tab4:
        st.markdown("#### Target Path Animation")
        st.markdown("""
        Watch sightings accumulate over time as an animation. Each frame adds the next recorded 
        sighting, drawing the path as it builds. 
        
        Select multiple targets simultaneously to look for **convergence patterns** — 
        moments where two targets appear in the same area at the same time.
        
        - **Date Range** — narrow the animation to a specific period
        - **Speed** — controls milliseconds per frame. Lower = faster playback
        - Use ▶ Play to start, ⏸ Pause to stop, or drag the slider to any point in time
        """)

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            anim_targets = st.multiselect(
                "Select Targets",
                options=all_targets, default=[all_targets[0]],
                format_func=lambda x: f"Target {x}",
                key="anim_targets",
            )
        with col2:
            anim_df_full = df[df["target"].isin(anim_targets)].copy() if anim_targets else df.copy()
            min_date = anim_df_full["last_seen"].min().date()
            max_date = anim_df_full["last_seen"].max().date()
            date_range = st.date_input(
                "Date Range", value=(min_date, max_date),
                min_value=min_date, max_value=max_date,
                key="anim_date_range",
            )
        with col3:
            speed_ms = st.slider(
                "Speed (ms/frame)",
                min_value=100, max_value=2000, step=100,
                value=st.session_state["anim_speed"],
                key="anim_speed",
            )

        if not anim_targets:
            st.info("Select at least one target to animate.")
        elif len(date_range) < 2:
            st.info("Select a start and end date.")
        else:
            start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            anim_df = anim_df_full[
                (anim_df_full["last_seen"] >= start_date) &
                (anim_df_full["last_seen"] <= end_date)
            ].copy()
            anim_df["target"] = anim_df["target"].astype(str)
            anim_df = anim_df.sort_values("last_seen").reset_index(drop=True)

            if anim_df.empty:
                st.warning("No sightings in selected date range.")
            else:
                # ── Build guard — frame construction is expensive ─────────
                # Building one Plotly frame per unique timestamp can take
                # 20-30s on large datasets. Only runs when explicitly requested.
                # Resets automatically when targets or date range change.
                anim_key = f"anim_{str(anim_targets)}_{str(date_range)}"
                if st.session_state.get("anim_key") != anim_key:
                    st.session_state.anim_built = False
                    st.session_state.anim_key   = anim_key

                n_frames = len(anim_df["last_seen"].unique())
                build_anim = st.button(
                    f"Build Animation  ({n_frames:,} frames)",
                    type="primary",
                    help="Builds one Plotly frame per unique timestamp. "
                         "May take a moment for large date ranges.",
                )
                if build_anim:
                    st.session_state.anim_built = True

                if not st.session_state.get("anim_built"):
                    st.info(
                        f"Ready — {len(anim_df):,} sightings · "
                        f"{anim_df['target'].nunique()} targets · "
                        f"{n_frames:,} frames. "
                        f"Click **Build Animation** to render."
                    )
                else:
                    timestamps    = sorted(anim_df["last_seen"].unique())
                    frames        = []
                    for ts in timestamps:
                        slice_df = anim_df[anim_df["last_seen"] <= ts].copy()
                        slice_df["frame"] = str(ts)
                        frames.append(slice_df)
                    animated_df   = pd.concat(frames).reset_index(drop=True)
                    target_colors = {str(t): color_map[str(t)] for t in anim_targets}
                    first_frame   = animated_df[animated_df["frame"] == str(timestamps[0])]
                    fig4 = go.Figure()

                    for t in [str(t) for t in anim_targets]:
                        color = target_colors[t]
                        grp   = first_frame[first_frame["target"] == t]
                        fig4.add_trace(go.Scattermap(
                            lat=grp["lat"], lon=grp["lon"], mode="lines",
                            line=dict(width=2, color=color),
                            name=f"Target {t}", legendgroup=f"t_{t}", showlegend=False,
                        ))
                        fig4.add_trace(go.Scattermap(
                            lat=grp["lat"], lon=grp["lon"], mode="markers",
                            marker=dict(size=8, color=color),
                            name=f"Target {t}", legendgroup=f"t_{t}", showlegend=True,
                            hovertemplate=(
                                "<b>Target %{customdata[0]}</b><br>"
                                "Time: %{customdata[1]}<br>"
                                "Lat: %{lat:.6f}<br>"
                                "Lon: %{lon:.6f}<extra></extra>"
                            ),
                            customdata=grp[["target", "last_seen"]].values,
                        ))

                    plotly_frames = []
                    for ts in timestamps:
                        frame_df   = animated_df[animated_df["frame"] == str(ts)]
                        frame_data = []
                        for t in [str(t) for t in anim_targets]:
                            color = target_colors[t]
                            grp   = frame_df[frame_df["target"] == t]
                            frame_data.append(go.Scattermap(
                                lat=grp["lat"], lon=grp["lon"], mode="lines",
                                line=dict(width=2, color=color),
                            ))
                            frame_data.append(go.Scattermap(
                                lat=grp["lat"], lon=grp["lon"], mode="markers",
                                marker=dict(size=8, color=color),
                                customdata=grp[["target", "last_seen"]].values,
                            ))
                        plotly_frames.append(go.Frame(data=frame_data, name=str(ts)))

                    fig4.frames = plotly_frames
                    fig4.update_layout(
                        map_style=map_styles[style_choice],
                        map=dict(center=dict(lat=anim_df["lat"].mean(), lon=anim_df["lon"].mean()), zoom=12),
                        height=580, margin={"r": 0, "t": 10, "l": 0, "b": 0},
                        legend_title_text="Target",
                        updatemenus=[dict(
                            type="buttons", showactive=False,
                            y=-0.05, x=0.5, xanchor="center",
                            buttons=[
                                dict(label="▶ Play", method="animate",
                                     args=[None, {"frame": {"duration": speed_ms, "redraw": True},
                                                  "fromcurrent": True, "transition": {"duration": 0}}]),
                                dict(label="⏸ Pause", method="animate",
                                     args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}]),
                            ]
                        )],
                        sliders=[dict(
                            steps=[dict(method="animate", args=[[str(ts)], {
                                "frame": {"duration": speed_ms, "redraw": True}, "mode": "immediate",
                            }], label=str(ts)) for ts in timestamps],
                            x=0.0, y=-0.12, len=1.0,
                            currentvalue=dict(prefix="Time: ", visible=True, xanchor="center"),
                        )]
                    )
                    st.plotly_chart(fig4, width="stretch")

    # ── Tab 5 — Heatmap ───────────────────────────────────────────────────
    with tab5:
        st.markdown("#### Sighting Density Heatmap")
        st.markdown("""
        A density map showing where targets spend the most time collectively. 
        Brighter, hotter areas indicate higher concentrations of sightings.
        
        Useful for identifying shared hotspots across all targets — areas that are 
        frequently visited regardless of which target is being tracked.
        
        - **Heat Radius** — controls how far each sighting point bleeds into its neighbors. 
          Larger radius = smoother, broader blobs. Smaller = tighter, more precise hotspots.
        
        The bar chart below breaks down sighting counts per target so you can see 
        if one target is driving the density or if it is evenly distributed.
        """)

        radius_px = st.slider(
            "Heat Radius",
            min_value=5, max_value=50, step=5,
            value=st.session_state["heatmap_radius"],
            key="heatmap_radius",
        )

        heat_df = get_heatmap_data(df, targets=selected if selected else None)

        if heat_df.empty:
            st.warning("No data for selected targets.")
        else:
            grid_df = build_heatmap_grid(heat_df)
            fig5h = go.Figure()
            fig5h.add_trace(go.Densitymap(
                lat=grid_df["lat"], lon=grid_df["lon"],
                z=grid_df["weight"],
                radius=radius_px,
                colorscale="Inferno", showscale=True,
                colorbar=dict(title="Density"),
                hoverinfo="skip",
            ))
            fig5h.update_layout(
                map_style=map_styles[style_choice],
                map=dict(center=dict(lat=heat_df["lat"].mean(), lon=heat_df["lon"].mean()), zoom=12),
                height=500, margin={"r": 0, "t": 10, "l": 0, "b": 0},
            )
            st.plotly_chart(fig5h, width="stretch")

            st.markdown("#### Sighting Count by Target")
            counts = (
                heat_df.groupby("target").size()
                .reset_index(name="sightings")
                .sort_values("sightings", ascending=False)
            )
            counts["target_str"] = counts["target"].astype(str)
            fig5b = px.bar(
                counts, x="target_str", y="sightings",
                color="target_str", color_discrete_map=color_map,
                labels={"target_str": "Target", "sightings": "Sightings"},
                height=280,
            )
            fig5b.update_layout(
                showlegend=False, margin={"t": 10},
                xaxis_title="Target", yaxis_title="Total Sightings",
            )
            st.plotly_chart(fig5b, width="stretch")

            st.markdown("#### Activity by Hour of Day")
            st.caption("Collective view — when are targets most active across all sightings?")

            heat_df["hour"] = pd.to_datetime(
                df[df["target"].isin(selected if selected else all_targets)]["last_seen"]
            ).dt.hour.values

            hourly = (
                heat_df.groupby("hour")
                .size()
                .reset_index(name="sightings")
            )

            fig5c = px.bar(
                hourly, x="hour", y="sightings",
                labels={"hour": "Hour of Day", "sightings": "Total Sightings"},
                height=250,
                color_discrete_sequence=["#4f8ef7"],
            )
            fig5c.update_layout(
                margin={"t": 10},
                xaxis=dict(tickmode="linear", dtick=1),
            )
            st.plotly_chart(fig5c, width="stretch")

    # ── Tab 6 — Convergence ───────────────────────────────────────────────
    with tab6:
        st.markdown("#### Convergence Detection")
        st.markdown("""
        Identifies moments when two targets were recorded at the same location within 
        a defined time window — a potential meeting or coordinated movement event.
        
        Two conditions must both be true for a convergence to be flagged:
        - **Distance** — the two sightings must be within X meters of each other
        - **Time Delta** — the two sightings must be within X minutes of each other
        
        A sighting at the same location 3 days apart is **not** convergence — 
        both spatial and temporal proximity are required simultaneously.
        
        - **Max Distance** — how close the two sightings must be geographically (meters)
        - **Max Time Delta** — how close in time the two sightings must be (minutes)
        
        The map plots each convergence event at the midpoint between the two sightings. 
        Dot size reflects proximity (smaller = closer). 
        Color reflects time delta (darker red = closer in time = higher confidence event).

        Set your distance and time thresholds above, then click **Apply** to run the detection.
        Results persist when switching tabs — you will not lose them by navigating away.
        """)

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            max_meters = st.slider(
                "Max Distance (meters)",
                min_value=10, max_value=500, step=10,
                value=st.session_state["max_meters"],
                key="max_meters",
            )
        with col2:
            max_minutes = st.slider(
                "Max Time Delta (minutes)",
                min_value=15, max_value=240, step=15,
                value=st.session_state["max_minutes"],
                key="max_minutes",
            )
        with col3:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            run_conv = st.button("Apply", use_container_width=True, type="primary")

        if "conv_df" not in st.session_state:
            st.session_state.conv_df = None

        if run_conv:
            st.session_state.conv_df = get_convergences(
                df, max_meters=max_meters, max_minutes=max_minutes
            )

        conv_df = st.session_state.conv_df
        if conv_df is None:
            st.info("Set parameters above then click **Apply** to run convergence detection.")
        else:
            if conv_df.empty:
                st.warning("No convergence events found. Try increasing distance or time window.")
            else:
                st.success(f"**{len(conv_df)} convergence event(s) detected.**")
                st.markdown("##### Events")
                st.dataframe(
                    conv_df[[
                        "target_a", "target_b", "time_a", "time_b",
                        "dt_minutes", "distance_m", "lat", "lon"
                    ]].sort_values("dt_minutes"),
                    column_config={
                        "target_a":   st.column_config.NumberColumn("Target A"),
                        "target_b":   st.column_config.NumberColumn("Target B"),
                        "time_a":     st.column_config.DatetimeColumn("Time A", format="YYYY-MM-DD HH:mm"),
                        "time_b":     st.column_config.DatetimeColumn("Time B", format="YYYY-MM-DD HH:mm"),
                        "dt_minutes": st.column_config.NumberColumn("Δ Minutes"),
                        "distance_m": st.column_config.NumberColumn("Distance (m)"),
                        "lat":        st.column_config.NumberColumn("Lat", format="%.6f"),
                        "lon":        st.column_config.NumberColumn("Lon", format="%.6f"),
                    },
                    hide_index=True, width="stretch",
                )

                st.markdown("##### Convergence Locations")
                fig6 = px.scatter_map(
                    conv_df, lat="lat", lon="lon",
                    size="distance_m", color="dt_minutes",
                    color_continuous_scale="Reds_r",
                    hover_data={
                        "target_a": True, "target_b": True,
                        "dt_minutes": True, "distance_m": True,
                        "lat": True, "lon": True,
                    },
                    zoom=12, height=450,
                    title="Convergence Locations — smaller dot = closer proximity",
                )
                fig6.update_layout(
                    map_style=map_styles[style_choice],
                    margin={"r": 0, "t": 40, "l": 0, "b": 0},
                    coloraxis_colorbar=dict(title="Δ Minutes"),
                )
                st.plotly_chart(fig6, width="stretch")


def render_temporal():
    st.markdown("## Temporal Analysis")
    st.markdown("""
    Time-based behavioral analysis across all tracked targets. This section answers:
    
    - **When** are targets active — which hours, which days of the week?
    - **What routines exist** — repeated presence at the same place at the same time?
    
    The **Hour × Day heatmap** can be viewed per target or combined across all targets. 
    Per-target reveals individual schedules. Combined reveals collective hotspots and 
    whether multiple targets share active periods — a potential indicator of coordination.
    
    The **Routines** tab is the most actionable output — it flags confirmed behavioral 
    patterns you can act on predictively.
    
    Use the target filter below to focus on a subset across both tabs.
    """)

    df        = load_data()
    color_map = assign_target_colors([str(t) for t in sorted(df["target"].unique())])
    all_targets = sorted(df["target"].unique())

    selected = st.multiselect(
        "Filter by Target",
        options=all_targets,
        default=st.session_state["temporal_selected"],
        format_func=lambda x: f"Target {x}",
        key="temporal_selected",
    )
    filtered = df[df["target"].isin(selected)].copy() if selected else df.copy()

    tab1, tab2 = st.tabs(["⏰ Hour × Day", "🔁 Routines"])

    with tab1:
        st.markdown("#### Activity Pattern — Hour × Day of Week")
        st.markdown("""
        Each cell represents a **hour + day of week combination**. 
        Color intensity = number of sightings at that time slot. 
        Numbers inside each cell show the exact count.
        
        **What to look for:**
        - **Bright clusters** — the target is consistently active at that hour on that day. High-confidence routine.
        - **Isolated bright cells** — one-off activity at an unusual time. Potentially anomalous.
        - **Dark rows or columns** — the target is never active on a given day or hour range.
        - **Combined view** — if two targets share the same bright cells, they are active at the 
          same times. Cross-reference with Convergence Detection to see if they were also 
          at the same location.
        
        Weekend rows (Saturday, Sunday) are lightly shaded.
        """)

        col1, col2 = st.columns([2, 1])
        with col1:
            view_mode = st.radio(
                "View",
                options=["Per Target", "Combined"],
                horizontal=True,
                key="hour_dow_mode",
            )
        with col2:
            focus_target = None
            if view_mode == "Per Target":
                focus_target = st.selectbox(
                    "Select Target",
                    options=selected if selected else all_targets,
                    format_func=lambda x: f"Target {x}",
                    key="hour_dow_target",
                )

        plot_df = (
            filtered[filtered["target"] == focus_target].copy()
            if view_mode == "Per Target" and focus_target is not None
            else filtered.copy()
        )

        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        heatmap_df = (
            plot_df
            .assign(
                hour=plot_df["last_seen"].dt.hour,
                dow=plot_df["last_seen"].dt.strftime("%A"),
            )
            .groupby(["dow", "hour"])
            .size()
            .reset_index(name="sightings")
        )

        if heatmap_df.empty:
            st.info("No data for selected target.")
        else:
            fig1 = px.density_heatmap(
                heatmap_df,
                x="hour", y="dow", z="sightings",
                category_orders={"dow": day_order},
                color_continuous_scale="Greens",
                height=400,
                labels={"hour": "Hour of Day", "dow": "Day of Week", "sightings": "Sightings"},
                text_auto=True,
            )
            fig1.update_layout(
                margin={"t": 10},
                xaxis=dict(tickmode="linear", dtick=1, title="Hour of Day"),
                yaxis_title="Day of Week",
                coloraxis_colorbar=dict(title="Sightings"),
            )

            for day in ["Saturday", "Sunday"]:
                fig1.add_hrect(
                    y0=day_order.index(day) - 0.5,
                    y1=day_order.index(day) + 0.5,
                    fillcolor="rgba(255,255,255,0.03)",
                    layer="below", line_width=0,
                )

            st.plotly_chart(fig1, width="stretch")

    with tab2:
        st.markdown("#### Detected Routines")
        st.markdown("""
        Automatically surfaces behavioral patterns — cases where a target was seen 
        at the **same location**, during the **same 2-hour time block**, on the **same day of week**, 
        a minimum number of times.
        
        This is the most actionable output in this section. A confirmed routine means 
        you can predict where a target will be before they get there.
        
        **How it works:**
        - Sightings are clustered by location within the radius you set
        - Each sighting is bucketed into a 2-hour time block (e.g. 08:00–10:00)
        - Each sighting is tagged with its day of week
        - Any combination of target + location + time block + day that repeats 
          at or above the minimum threshold is flagged
        
        **Controls:**
        - **Minimum Occurrences** — how many times the pattern must repeat to be flagged. 
          Lower = more patterns, higher noise. Higher = only strong confirmed patterns.
        - **Location Cluster Radius** — filters which routines are shown based on location 
          proximity. The underlying clustering was fixed at pipeline time (10m radius). 
          Increasing this slider broadens which location groups are included — it does not 
          recompute how sightings are grouped.
        
        Each card: target · location · time block · day of week · occurrences.
        """)

        col1, col2 = st.columns(2)
        with col1:
            min_occ = st.slider(
                "Minimum Occurrences",
                min_value=2, max_value=10, step=1,
                value=st.session_state["routine_min"],
                key="routine_min",
            )
        with col2:
            cluster_r = st.slider(
                "Location Cluster Radius (m)",
                min_value=10, max_value=200, step=10,
                value=st.session_state["routine_radius"],
                key="routine_radius",
            )

        routines = get_routines(filtered, max_meters=cluster_r, min_occurrences=min_occ)

        if routines.empty:
            st.warning("No routines detected. Try lowering minimum occurrences or increasing cluster radius.")
        else:
            st.success(f"**{len(routines)} routine(s) detected.**")

            rcol1, rcol2 = st.columns([3, 1])
            with rcol1:
                st.caption(f"Showing top 10 of {len(routines)} routines by occurrences.")
            with rcol2:
                show_all_routines = st.toggle("Show All", key="show_all_routines", value=False)

            display_routines = routines if show_all_routines else routines.head(10)

            with st.container(height=500):
                for _, row in display_routines.iterrows():
                    color = color_map[str(row["target"])]
                    st.markdown(f"""
                    <div style="
                        border-left: 3px solid {color};
                        padding: 10px 16px;
                        margin-bottom: 10px;
                        background: rgba(255,255,255,0.02);
                        border-radius: 4px;
                    ">
                        <span style="color:{color}; font-weight:700;">Target {row['target']}</span>
                        &nbsp;·&nbsp;
                        <span style="color:#e4e6f0;">📍 {row['location_label']}</span>
                        &nbsp;·&nbsp;
                        <span style="color:#aaa;">🕐 {row['hour_range']}</span>
                        &nbsp;·&nbsp;
                        <span style="color:#aaa;">📅 {row['dow']}</span>
                        &nbsp;·&nbsp;
                        <span style="color:#f0c040;">🔁 {row['occurrences']}x</span>
                    </div>
                    """, unsafe_allow_html=True)


def network():
    st.markdown("## Location Intelligence")
    st.markdown("""
    Location-based analysis across all targets. This section answers two questions:
    
    - **Where does each target repeatedly return?** — Dwell detection flags locations 
      visited above a minimum threshold, suggesting home bases, meeting points, or routine stops.
    - **Which locations are shared between targets?** — The shared location table and network 
      graph show places visited by more than one target — a key indicator of relationship 
      or coordination. The table gives the details, the graph makes the relationships visible.
    
    These two views build on each other: dwell identifies important locations per target, 
    shared locations identify overlap between targets.
    """)

    df          = load_data()
    all_targets = sorted(df["target"].unique())
    color_map   = assign_target_colors([str(t) for t in all_targets])

    selected_targets = st.multiselect(
        "Filter by Target",
        options=all_targets,
        default=st.session_state["location_selected"],
        format_func=lambda x: f"Target {x}",
        key="location_selected",
    )
    filtered_df  = df[df["target"].isin(selected_targets)].copy() if selected_targets else df.copy()
    clustered_df = cluster_locations(filtered_df, max_meters=10)

    tab1, tab2 = st.tabs(["📍 Dwell Detection", "🔗 Shared Locations & Network"])

    with tab1:
        st.markdown("#### Dwell Detection")
        st.markdown("""
        Flags locations where a single target was observed repeatedly — above the minimum 
        visit threshold you set. A dwell location suggests a place of significance: 
        a home address, workplace, regular meeting point, or routine stop.
        
        **Controls:**
        - **Minimum Visits** — how many times a target must appear at a location to be flagged. 
          Lower = more locations flagged, higher noise. Higher = only the most significant spots.
        - **Cluster Radius** — filters results to locations clustered within this radius. 
          Note: the underlying location grouping was computed at pipeline time using a 10m radius. 
          Increasing this slider surfaces locations across a wider area — it does not regroup 
          raw GPS points.
        
        Dot size on the map scales with visit count — larger dots are higher-frequency locations.
        """)

        col1, col2 = st.columns(2)
        with col1:
            min_visits = st.slider(
                "Minimum Visits to Flag",
                min_value=2, max_value=10, step=1,
                value=st.session_state["dwell_min_visits"],
                key="dwell_min_visits",
            )
        with col2:
            cluster_radius = st.slider(
                "Cluster Radius (meters)",
                min_value=5, max_value=100, step=5,
                value=st.session_state["dwell_cluster_radius"],
                key="dwell_cluster_radius",
            )

        dwell_df = get_dwell_locations(filtered_df, min_visits=min_visits, max_meters=cluster_radius)

        if dwell_df.empty:
            st.warning("No dwell locations found. Try lowering minimum visits or increasing cluster radius.")
        else:
            st.success(f"**{len(dwell_df)} dwell location(s) detected across {dwell_df['target'].nunique()} target(s).**")

            dwell_targets  = sorted(dwell_df["target"].unique())
            dwell_selected = st.multiselect(
                "Filter by Target",
                options=dwell_targets,
                default=dwell_targets,
                format_func=lambda x: f"Target {x}",
                key="dwell_targets",
            )
            dwell_filtered = (
                dwell_df[dwell_df["target"].isin(dwell_selected)].copy()
                if dwell_selected else dwell_df.copy()
            )

            dcol1, dcol2 = st.columns([3, 1])
            with dcol1:
                st.caption(f"Showing top 10 of {len(dwell_filtered)} locations by visit count.")
            with dcol2:
                show_all_dwell = st.toggle("Show All", key="show_all_dwell", value=False)

            display_dwell = dwell_filtered if show_all_dwell else dwell_filtered.head(10)

            st.dataframe(
                display_dwell[["target", "location_label", "visit_count", "first_seen", "last_seen"]],
                column_config={
                    "target":         st.column_config.NumberColumn("Target"),
                    "location_label": st.column_config.TextColumn("Location (lat, lon)"),
                    "visit_count":    st.column_config.NumberColumn("Visits"),
                    "first_seen":     st.column_config.DatetimeColumn("First Seen", format="YYYY-MM-DD HH:mm"),
                    "last_seen":      st.column_config.DatetimeColumn("Last Seen",  format="YYYY-MM-DD HH:mm"),
                },
                hide_index=True, width="stretch", height=500,
            )

            dwell_filtered["target_str"] = dwell_filtered["target"].astype(str)
            fig1 = px.scatter_map(
                dwell_filtered,
                lat="lat", lon="lon",
                color="target_str",
                color_discrete_map=color_map,
                size="visit_count", size_max=30,
                hover_data={
                    "target_str":     True,
                    "location_label": True,
                    "visit_count":    True,
                    "first_seen":     True,
                    "last_seen":      True,
                    "lat":            True,
                    "lon":            True,
                },
                zoom=12, height=480,
            )
            fig1.update_layout(
                map_style="carto-darkmatter",
                margin={"r": 0, "t": 10, "l": 0, "b": 0},
                legend_title_text="Target",
            )
            st.plotly_chart(fig1, width="stretch")

    with tab2:
        st.markdown("#### Shared Location Analysis")
        st.markdown("""
        Locations visited by **more than one target**, shown as both a table and a network graph.
        
        The table gives precise details — which targets were seen there, total visit count, 
        and the time range of recorded sightings at that location.
        The network graph below makes the relationships immediately visible.
        
        **Note:** a shared location does not confirm a meeting — targets may have visited 
        at different times. Cross-reference with **Convergence Detection** to confirm 
        whether visits were temporally close enough to constitute a meeting.
        """)

        shared_locs = get_shared_locations_table(clustered_df)

        if shared_locs.empty:
            st.info("No shared locations detected within 10 meters.")
        else:
            st.success(f"**{len(shared_locs)} shared location(s) detected.**")

            slcol1, slcol2 = st.columns([3, 1])
            with slcol1:
                st.caption(f"Showing top 10 of {len(shared_locs)} shared locations by visit count.")
            with slcol2:
                show_all_shared = st.toggle("Show All", key="show_all_shared", value=False)

            display_shared = shared_locs if show_all_shared else shared_locs.head(10)

            st.dataframe(
                display_shared,
                column_config={
                    "location_label": st.column_config.TextColumn("Location (lat, lon)"),
                    "targets":        st.column_config.TextColumn("Targets Present"),
                    "visit_count":    st.column_config.NumberColumn("Total Visits"),
                    "first_seen":     st.column_config.DatetimeColumn("First Seen", format="YYYY-MM-DD HH:mm"),
                    "last_seen":      st.column_config.DatetimeColumn("Last Seen",  format="YYYY-MM-DD HH:mm"),
                },
                hide_index=True, width="stretch", height=500,
            )

        st.markdown("#### Target–Location Network")
        st.markdown("""
        A force-directed network graph connecting targets to every location where they were sighted.
        
        - **Colored circles** — targets, each with a unique color matching the rest of the app
        - **Yellow diamonds** — location clusters (points within 10 meters grouped as one node)
        - **Edges** — a line between a target and a location means that target was seen there
        
        **What to look for:**
        - **Two targets connected to the same location node** — they share that location. 
          The more shared nodes, the stronger the implied relationship.
        - **Highly connected location nodes** — hotspots visited by many targets.
        - **Isolated target nodes** — targets with no shared locations, operating independently.
        
        Drag nodes to rearrange. Scroll to zoom. Hover for details.
        """)
        render_network(clustered_df, color_map)


def main():
    apply_config()
    render_header()
    st.caption(pipeline_age_label())
    init_session_state()
    render_target_intel()
    st.divider()
    render_charts()
    st.divider()
    render_temporal()
    st.divider()
    network()
    st.divider()
    render_footer()


if __name__ == "__main__":
    main()