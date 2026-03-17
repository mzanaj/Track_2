"""
app/utils/timing.py
-------------------
Lightweight timing logger for Streamlit.

Tracks how long each named operation takes within a single page render.
Displayed as a collapsible panel at the bottom of the page.

Usage:
    from utils.timing import timer

    with timer("Load data"):
        df = load_data()

    with timer("Build scatter map"):
        fig = px.scatter_map(...)

    # At end of page:
    render_timing_log()
"""

import time
import streamlit as st
from contextlib import contextmanager


def _get_log() -> list:
    if "_timing_log" not in st.session_state:
        st.session_state._timing_log = []
    return st.session_state._timing_log


def reset_timing_log():
    """Call at the start of each render to clear previous run's timings."""
    st.session_state._timing_log = []


@contextmanager
def timer(label: str):
    """Context manager — measures the block and appends to the log."""
    start = time.perf_counter()
    yield
    elapsed = round(time.perf_counter() - start, 3)
    _get_log().append((label, elapsed))


def render_timing_log():
    """
    Render the timing log as a collapsible expander at the bottom of the page.
    Color-codes entries: green < 0.1s, amber 0.1–1s, red > 1s.
    """
    log = _get_log()
    if not log:
        return

    total = sum(t for _, t in log)

    with st.expander(f"⏱ Performance log — {total:.2f}s total", expanded=False):
        rows = []
        for label, elapsed in log:
            if elapsed < 0.1:
                color = "#2ecc71"   # green
                flag  = ""
            elif elapsed < 1.0:
                color = "#f0c040"   # amber
                flag  = " ⚠"
            else:
                color = "#e74c3c"   # red
                flag  = " 🔴"

            bar_width = min(int(elapsed * 200), 300)  # scale: 1s = 200px, max 300px

            rows.append(f"""
            <div style="display:flex; align-items:center; gap:12px;
                        padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="width:220px; font-size:12px;
                            color:var(--text-color); flex-shrink:0;">
                    {label}{flag}
                </div>
                <div style="background:{color}; height:8px;
                            width:{bar_width}px; border-radius:4px; flex-shrink:0;">
                </div>
                <div style="font-size:12px; color:{color}; flex-shrink:0;">
                    {elapsed:.3f}s
                </div>
            </div>
            """)

        st.markdown(
            "<div style='font-family:monospace'>" + "".join(rows) + "</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Total render time: {total:.3f}s  ·  {len(log)} operations")