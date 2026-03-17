import streamlit as st
import pandas as pd
import plotly.express as px
from utils.streamlit_config import apply_config, render_header, render_footer

@st.cache_data
def load_ingest_data():
    df = pd.read_csv("data/daily_ingest_data.csv", parse_dates=["datetime", "date"])
    return df

def render_kpis(df):
    total      = df["data_count"].sum()
    daily_avg  = int(df["data_count"].mean())
    peak       = df["data_count"].max()
    peak_date  = df.loc[df["data_count"].idxmax(), "date"].strftime("%b %d")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Records",  f"{total:,}")
    c2.metric("Daily Average",  f"{daily_avg:,}")
    c3.metric("Peak Day",       f"{peak:,}")
    c4.metric("Peak Date",      peak_date)

def render_ingest_chart(df):
    st.markdown("## Daily Data Ingest")
    st.markdown("""
    Daily record count over the last 90 days. 
    Weekends naturally trend lower. Spikes may indicate 
    batch loads or upstream anomalies worth investigating.
    """)

    # ── KPIs ──────────────────────────────────────────────────────────
    render_kpis(df)
    st.divider()

    # ── Date range filter ──────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        date_range = st.date_input(
            "Date Range",
            value=(df["date"].min(), df["date"].max()),
            min_value=df["date"].min(),
            max_value=df["date"].max(),
            key="ingest_date_range",
        )
    with col2:
        show_weekend = st.toggle("Highlight Weekends", value=True)

    if len(date_range) < 2:
        st.info("Select a start and end date.")
        return

    start, end   = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered     = df[(df["date"] >= start) & (df["date"] <= end)].copy()

    if filtered.empty:
        st.warning("No data in selected range.")
        return

    # ── Line chart ────────────────────────────────────────────────────
    fig = px.line(
        filtered,
        x="date",
        y="data_count",
        labels={"date": "Date", "data_count": "Records Ingested"},
        height=420,
    )

    fig.update_traces(
        line=dict(color="#4f8ef7", width=2),
        mode="lines+markers",
        marker=dict(size=4, color="#4f8ef7"),
    )

    avg = filtered["data_count"].mean()

    fig.add_hline(
        y=avg,
        line_dash="dot",
        line_color="rgba(255,200,50,0.6)",
        line_width=1.5,
        annotation_text=f"Avg: {avg:,.0f}",
        annotation_position="top right",
        annotation_font=dict(color="rgba(255,200,50,0.8)", size=12),
    )

    # Weekend shading
    if show_weekend:
        weekends = filtered[filtered["is_weekend"] == True]
        for _, row in weekends.iterrows():
            fig.add_vrect(
                x0=str(row["date"]),
                x1=str(row["date"]),
                fillcolor="rgba(255,255,255,0.04)",
                layer="below",
                line_width=6,
                line_color="rgba(255,255,255,0.08)",
            )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Records"),
        hovermode="x unified",
    )

    st.plotly_chart(fig, width="stretch")

    # ── Raw data toggle ───────────────────────────────────────────────
    with st.expander("View Raw Data"):
        st.dataframe(
            filtered[["date", "day_of_week", "data_count", "is_weekend"]],
            column_config={
                "date":        st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "day_of_week": st.column_config.TextColumn("Day"),
                "data_count":  st.column_config.NumberColumn("Records", format="%d"),
                "is_weekend":  st.column_config.CheckboxColumn("Weekend"),
            },
            hide_index=True,
            width="stretch",
        )

def main():
    apply_config()
    render_header(title="Stats")
    render_ingest_chart(load_ingest_data())
    render_footer()

if __name__ == "__main__":
    main()