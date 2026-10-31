"""Tab 2: Futures Curve & Divergence (CFD Proxy — Brent-WTI spread)."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from data.fetcher_refineries import get_refinery_capacity, get_refinery_utilization
from analysis.curve_analysis import compute_driver

AREA_LABELS = {
    "NUS": "US", "R10": "East Coast", "R20": "Midwest",
    "R30": "Gulf Coast", "R40": "Rocky Mt", "R50": "West Coast",
}


def render_curve_tab(market_data):
    st.subheader("Curve & Divergence")

    curve = market_data.get("curve")
    wti = market_data.get("wti")
    brent = market_data.get("brent")

    if not wti or not brent:
        st.warning("No curve data available.")
        return

    wti_dates = [pd.to_datetime(d) for d in wti["dates"]]
    brent_dates = [pd.to_datetime(d) for d in brent["dates"]]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.6, 0.4],
        subplot_titles=("WTI vs Brent", "Brent-WTI Spread (CFD Proxy)"),
    )

    fig.add_trace(
        go.Scatter(x=wti_dates, y=wti["close"], mode="lines",
                   name="WTI", line=dict(color="#FF9800", width=2)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=brent_dates, y=brent["close"], mode="lines",
                   name="Brent", line=dict(color="#00BCD4", width=2)),
        row=1, col=1,
    )

    if curve and curve.get("brent_wti_spread") and curve.get("spread_dates"):
        spread_dates = [pd.to_datetime(d) for d in curve["spread_dates"]]
        spread_vals = curve["brent_wti_spread"]

        colors = ["#4CAF50" if v > 0 else "#F44336" for v in spread_vals]
        fig.add_trace(
            go.Bar(x=spread_dates, y=spread_vals, name="Brent-WTI Spread",
                   marker_color=colors, opacity=0.7),
            row=2, col=1,
        )
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5, row=2, col=1)

        avg_spread = sum(spread_vals) / len(spread_vals) if spread_vals else 0
        fig.add_hline(y=avg_spread, line_dash="dash", line_color="white", opacity=0.3,
                      annotation_text=f"Avg: ${avg_spread:.1f}", row=2, col=1)

    fig.update_layout(
        height=550,
        showlegend=True,
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
        template="plotly_dark",
        dragmode="pan",
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })

    _render_driver_panel(wti, brent)

    st.markdown("---")
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **Brent and WTI** are the two most important types of crude oil. Brent is the global benchmark (mined in the North Sea), and WTI is the US benchmark. They usually trade close together, but the gap between them tells you a lot.

        **What the spread means:**
        - When Brent is more expensive than WTI (spread > 0), the global market is tight. Buyers are willing to pay a premium for Brent. This is called **backwardation** and is generally bullish.
        - When WTI catches up or exceeds Brent (spread < 0), it sometimes means paper traders are bidding up WTI faster than physical buyers can absorb it. This is called **contango** and can be a warning sign.

        **Bottom chart — the spread as colored bars:**
        - Green = Brent premium (normal/tight market).
        - Red = WTI premium (unusual — pay attention).
        - The white dashed line is the average spread. When the current spread is far from average, it may revert back.
        """)

    # Interpretation
    st.markdown("### Interpretation")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Spread > 0 (Backwardation proxy)**
        - Physical crude commanding a premium
        - Physical market tighter than paper suggests
        - Bullish signal for near-term pricing
        """)
    with col2:
        st.markdown("""
        **Spread < 0 (Contango proxy)**
        - Paper bidding above physical reality
        - Speculation may be driving price
        - Fragile — watch for unwind
        """)

    if curve and curve.get("brent_wti_spread"):
        current = curve["brent_wti_spread"][-1] if curve["brent_wti_spread"] else 0
        st.metric("Current Brent-WTI Spread", f"${current:.2f}")

    st.markdown("---")
    st.markdown("### Who Produces vs Who Refines")

    _render_crude_table(
        "WTI — US benchmark (Cushing, OK)",
        "Producers, refineries and origin countries are independent lists — a producer's crude "
        "is sold on the open market and can go to any refinery that buys it.",
        producers=[
            "ExxonMobil", "Chevron", "ConocoPhillips", "Occidental",
            "EOG Resources", "Devon Energy", "Diamondback Energy",
        ],
        refineries=[
            "Motiva Port Arthur (US)", "ExxonMobil Baton Rouge (US)",
            "Marathon Garyville (US)", "Valero Port Arthur (US)",
            "Chevron Pascagoula (US)", "PBF Chalmette (US)",
        ],
        countries=["United States (Texas, New Mexico, North Dakota, Oklahoma)"],
    )

    _render_crude_table(
        "Brent — North Sea global benchmark",
        "Producers, refineries and origin countries are independent lists — a producer's crude "
        "is sold on the open market and can go to any refinery that buys it.",
        producers=[
            "Equinor", "Shell", "BP", "TotalEnergies",
            "Harbour Energy", "Ithaca Energy",
        ],
        refineries=[
            "Shell Pernis (Netherlands)", "BP Rotterdam (Netherlands)",
            "TotalEnergies Antwerp (Belgium)", "INEOS Grangemouth (UK)",
            "ExxonMobil Fawley (UK)",
        ],
        countries=["United Kingdom", "Norway"],
    )

    st.markdown("---")
    st.markdown("### US Refinery Capacity & Utilization")
    _render_refinery_capacity()
    _render_refinery_utilization()


def _render_crude_table(title, caption, producers, refineries, countries):
    """Render one producer/refinery/origin reference table (independent lists)."""
    from itertools import zip_longest

    rows = [
        {"producers": p, "refineries": r, "countries": c}
        for p, r, c in zip_longest(producers, refineries, countries, fillvalue="")
    ]
    st.markdown(f"#### {title}")
    st.dataframe(
        pd.DataFrame(rows),
        column_config={
            "producers": "Producers",
            "refineries": "Refineries",
            "countries": "Countries of Origin",
        },
        use_container_width=True,
    )
    st.caption(caption)


def _render_refinery_capacity():
    rows = get_refinery_capacity()
    if not rows:
        st.caption("Refinery capacity data unavailable (annual EIA report).")
        return

    total = sum(r["capacity_bpd"] for r in rows)
    states = sorted({r["state"] for r in rows if r["state"]})
    c1, c2, c3 = st.columns(3)
    c1.metric("Refineries", f"{len(rows):,}")
    c2.metric("Total capacity", f"{total / 1e6:.1f}M bbl/day")
    c3.metric("States", len(states))

    df = pd.DataFrame(rows)
    df = df[["company", "site", "state", "padd", "capacity_bpd"]]
    df.columns = ["Company", "Site", "State", "PADD", "Capacity (bbl/day)"]
    st.dataframe(df, use_container_width=True)
    st.caption("Source: EIA Refinery Capacity Report (annual). All US refineries with "
               "crude-distillation capacity; WTI is processed by most refiners with "
               "pipeline access to Cushing.")


def _render_refinery_utilization():
    util = get_refinery_utilization()
    if not util["available"]:
        st.caption("Weekly refinery utilization unavailable.")
        return

    dates = [pd.to_datetime(d) for d in util["dates"]]
    pct = util["utilization_pct"]

    latest_pct = {area: vals[-1] for area, vals in pct.items() if vals}
    if latest_pct:
        us_pct = latest_pct.get("NUS")
        if us_pct is not None:
            st.metric("US Refinery Utilization", f"{us_pct:.1f}%")
        cols = st.columns(5)
        for col, area in zip(cols, ["R10", "R20", "R30", "R40", "R50"]):
            val = latest_pct.get(area)
            col.metric(AREA_LABELS.get(area, area),
                       f"{val:.1f}%" if val is not None else "—")

    fig = go.Figure()
    for area, vals in pct.items():
        if not vals:
            continue
        label = AREA_LABELS.get(area, area)
        fig.add_trace(go.Scatter(
            x=dates, y=vals, mode="lines", name=label,
        ))
    fig.update_layout(
        title="Refinery utilization % (weekly)",
        height=320, template="plotly_dark",
        hovermode="x unified", dragmode="pan",
        yaxis=dict(range=[60, 105]),
    )
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })
    st.caption("Source: EIA weekly refinery inputs & utilization. Utilization = crude "
               "inputs ÷ operable capacity.")


def _render_driver_panel(wti, brent):
    """Who is driving the recent Brent-WTI divergence (pain-thread view)."""
    st.markdown("### Who's Driving the Divergence")
    window = st.selectbox("Lookback window", [5, 20, 60], index=0,
                          help="How many trading days of move to compare.")
    result = compute_driver(wti, brent, window=window)

    if result["driver"] == "insufficient":
        st.caption("Not enough price history to determine the driver.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("WTI move", f"{result['wti_move_pct']:+.2f}%",
              f"{result['wti_old']:.2f} → {result['wti_new']:.2f}")
    c2.metric("Brent move", f"{result['brent_move_pct']:+.2f}%",
              f"{result['brent_old']:.2f} → {result['brent_new']:.2f}")
    c3.metric("Spread change", f"{result['spread_change']:+.2f}")

    driver = result["driver"]
    if driver == "brent":
        color, label = "#00BCD4", "BRENT"
        desc = ("Brent is moving the spread. The divergence is a GLOBAL story — "
                "Iran/geopolitics, OPEC, shipping, or European/Asian demand. "
                "Investigate international supply and risk events, not US domestic.")
    elif driver == "wti":
        color, label = "#FF9800", "WTI"
        desc = ("WTI is moving the spread. The divergence is a US story — Cushing "
                "logistics, pipelines, exports, shale supply, or US tariffs. "
                "Investigate domestic infrastructure and US inventory changes.")
    else:
        color, label = "#9E9E9E", "TIED"
        desc = "Both benchmarks moved about equally — the spread is stable relative to the legs."

    st.markdown(
        f"<span style='color:{color};font-weight:bold;font-size:22px'>DRIVER: {label}</span>",
        unsafe_allow_html=True,
    )
    st.caption(desc)

    # Direction of the driver tells us whether the move is up or down.
    if driver in ("brent", "wti"):
        move = result["brent_move_pct"] if driver == "brent" else result["wti_move_pct"]
        if move > 0:
            st.markdown(f"**{label} is rising** — the spread is being pushed by strength.")
        elif move < 0:
            st.markdown(f"**{label} is falling** — the spread is being pushed by weakness.")
        else:
            st.markdown(f"**{label} is flat** relative to the window start.")