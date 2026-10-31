"""Tab 4: EIA Weekly Inventory Changes."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from analysis.eia_analysis import compute_eia_analysis
from analysis.inventory_levels import (
    mbbl_to_million_bbl,
    spr_projection,
    weeks_of_supply,
)
from data.fetcher_refineries import get_refinery_utilization


def render_inventory_tab(eia_data):
    st.subheader("Inventories — Weekly Changes")

    if not eia_data:
        st.warning("No EIA inventory data available. This requires an EIA API key.")
        st.caption("Set EIA_API_KEY in .env and click Refresh All Data.")
        return

    crude = eia_data.get("crude")
    gasoline = eia_data.get("gasoline")
    distillate = eia_data.get("distillate")
    spr = eia_data.get("spr")
    spr_level = eia_data.get("spr_level")

    if not crude and not gasoline and not distillate and not spr:
        st.warning("EIA inventory data unavailable. Verify your API key is valid.")
        return

    # EIA Analysis summary
    analysis = compute_eia_analysis(eia_data)
    if analysis["by_product"]:
        signal_labels = {1: "🟢 Bullish", -1: "🔴 Bearish", 0: "⬜ Neutral"}
        st.markdown(f"### EIA Report Summary — Composite Score: **{analysis['composite_score']:+d}**")
        cols = st.columns(4)
        for col, (key, prod) in zip(cols, analysis["by_product"].items()):
            label = signal_labels.get(prod["signal"], "")
            change = prod["current_change"]
            display = f"{change:+.1f} M" if change is not None else "N/A"
            col.metric(f"{label} {key.title()}", display, prod["trend_label"])
        if analysis["strongest_reading"]:
            dev = analysis["by_product"][analysis["strongest_reading"]]["deviation"]
            dev_str = f"{abs(dev):.1f} M" if dev is not None else "N/A"
            st.caption(f"Strongest signal: **{analysis['strongest_reading'].title()}** — deviation is {dev_str} from 4-week trend")
        st.markdown("---")

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Crude Oil Stocks Change (M bbl)",
            "Gasoline Stocks Change (M bbl)",
            "Distillate Stocks Change (M bbl)",
            "Strategic Petroleum Reserve Change (M bbl)",
        ),
    )

    def _plot_inventory(fig, data, row, name, color_neg, color_pos):
        if not data or not data.get("dates"):
            return
        dates = [pd.to_datetime(d) for d in data["dates"]]
        changes = data.get("changes", [])
        if not changes:
            return

        colors = [color_neg if c < 0 else color_pos for c in changes]
        fig.add_trace(
            go.Bar(x=dates, y=changes, name=name,
                   marker_color=colors, opacity=0.8),
            row=row, col=1,
        )
        fig.add_hline(y=0, line_dash="solid", line_color="gray",
                      opacity=0.3, row=row, col=1)

    _plot_inventory(fig, crude, 1, "Crude", "#4CAF50", "#F44336")
    _plot_inventory(fig, gasoline, 2, "Gasoline", "#4CAF50", "#F44336")
    _plot_inventory(fig, distillate, 3, "Distillate", "#4CAF50", "#F44336")
    _plot_inventory(fig, spr, 4, "SPR", "#FF9800", "#FF9800")

    fig.update_layout(
        height=750,
        showlegend=False,
        template="plotly_dark",
        hovermode="x unified",
        dragmode="pan",
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })

    st.markdown("### Key Levels")
    col1, col2, col3, col4 = st.columns(4)

    def _latest_change(data, label, col):
        if data and data.get("changes"):
            last = data["changes"][0]
            if last is not None and not pd.isna(last):
                col.metric(label, f"{last:+.1f} M bbl")
            else:
                col.metric(label, "N/A")
        else:
            col.metric(label, "N/A")

    _latest_change(crude, "Crude", col1)
    _latest_change(gasoline, "Gasoline", col2)
    _latest_change(distillate, "Distillate", col3)

    if spr_level and spr_level.get("values"):
        current = spr_level["values"][0]
        if current is not None and not pd.isna(current):
            col4.metric("SPR Level", f"{current / 1000:.0f} M bbl")
        else:
            col4.metric("SPR Level", "N/A")
    else:
        col4.metric("SPR Level", "N/A")

    st.markdown("---")
    _render_level_charts(eia_data)
    _render_weeks_of_supply(eia_data)
    _render_spr_projection(eia_data)

    st.markdown("---")
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **What is EIA data?**
        Every Wednesday morning, the US Energy Information Administration releases the Weekly Petroleum Status Report. It tells us how much crude oil, gasoline, and distillate (diesel/heating oil) is sitting in US storage tanks.

        **What the charts show:**
        - **Green bars** = inventories went DOWN (a "draw"). Bullish for oil prices — demand is outpacing supply.
        - **Red bars** = inventories went UP (a "build"). Bearish — supply is outpacing demand.
        - The taller the bar, the bigger the surprise versus expectations.

        **The three products:**
        1. **Crude Oil** — The raw stuff. A big draw means refineries are processing a lot. A big build means oil is backing up.
        2. **Gasoline** — Made from crude. Big draw during summer = people driving a lot (bullish for crude demand). Big build in winter = normal seasonal pattern.
        3. **Distillate** — Diesel, jet fuel, heating oil. A big draw can signal strong industrial activity or cold weather.

        **Strategic Petroleum Reserve (bottom chart):**
        - Shows how much oil the US government is adding or removing from the SPR — the nation's emergency stockpile.
        - **Orange bars** — Government released oil (draw). Adds supply to the market, bearish for prices.
        - **Orange bars upward** — Government is buying back oil (refill). Takes supply off the market, bullish.
        - The "SPR Level" metric shows the total barrels remaining in the reserve. Full capacity is ~714 million barrels.
        - In a supply crisis (war, OPEC cuts), large SPR releases are a major intervention. When you see big orange bars, the government is trying to cap prices.
        - Post-crisis refill programs create a steady demand floor as the government buys back barrels.
        - If SPR gets too low (under 400M), the cushion for future emergencies shrinks — adds risk premium to oil prices.

        **How to use it:**
        - A large crude draw + rising gasoline demand = strong fundamental support for higher prices.
        - A large crude build + falling product demand = weak fundamentals, be careful buying.
        - The "Key Levels" metrics show the most recent week's change in millions of barrels.
        """)


def _render_level_charts(eia_data):
    """Actual inventory LEVELS (not weekly changes) for each product + SPR."""
    series = [
        ("Crude Oil Stocks", eia_data.get("crude")),
        ("Gasoline Stocks", eia_data.get("gasoline")),
        ("Distillate Stocks", eia_data.get("distillate")),
        ("Strategic Petroleum Reserve", eia_data.get("spr")),
    ]

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        subplot_titles=(
            "Crude Level (M bbl)", "Gasoline Level (M bbl)",
            "Distillate Level (M bbl)", "SPR Level (M bbl)",
        ),
    )
    for i, (label, data) in enumerate(series, start=1):
        if not data or not data.get("dates") or not data.get("values"):
            continue
        dates = [pd.to_datetime(d) for d in data["dates"]]
        levels = mbbl_to_million_bbl(data["values"])
        fig.add_trace(
            go.Scatter(x=dates, y=levels, mode="lines", name=label,
                       line=dict(width=2)),
            row=i, col=1,
        )

    fig.update_layout(
        height=750, showlegend=False, template="plotly_dark",
        hovermode="x unified", dragmode="pan",
    )
    st.markdown("### Inventory Levels")
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })
    st.caption("Actual stock levels (M bbl), not weekly changes — the trend of the "
               "level tells you whether supply is building or drawing over time.")


def _render_weeks_of_supply(eia_data):
    """Weeks of crude cover = commercial crude stocks / refinery inputs."""
    st.markdown("### Weeks of Crude Supply")
    crude = eia_data.get("crude")
    util = get_refinery_utilization(weeks=4)

    inputs_mbpd = None
    if util["available"] and util["crude_inputs"].get("NUS"):
        raw = util["crude_inputs"]["NUS"]
        for v in reversed(raw):
            if v is not None:
                inputs_mbpd = v / 1000.0  # thousand bbl/day -> million bbl/day
                break

    if not crude or not crude.get("values"):
        st.caption("No crude inventory data.")
        return

    latest = crude["values"][0]
    if latest is None or pd.isna(latest):
        st.caption("No current crude level.")
        return
    stocks_mbbl = latest / 1000.0

    weeks = weeks_of_supply(stocks_mbbl, inputs_mbpd)
    c1, c2 = st.columns(2)
    if weeks is not None:
        c1.metric("Weeks of crude supply", f"{weeks:.1f}")
    else:
        c1.metric("Weeks of crude supply", "N/A")
        st.info("Weeks-of-supply needs refinery crude inputs (EIA 'Refining and "
                "Processing' subscription). Stock level shown separately.")
    c2.metric("Crude level", f"{stocks_mbbl:.0f} M bbl")
    st.caption("Weeks of supply = commercial crude stocks ÷ refinery crude inputs "
               "per day ÷ 7. Lower weeks = tighter supply cushion (bullish backdrop).")


def _render_spr_projection(eia_data):
    """SPR depletion/refill timeline from the SPR level series."""
    st.markdown("### SPR Depletion Projection")
    spr = eia_data.get("spr")
    if not spr or not spr.get("values"):
        st.caption("No SPR data.")
        return

    levels_mbbl = mbbl_to_million_bbl(spr["values"])
    if not levels_mbbl:
        st.caption("No valid SPR level data.")
        return
    proj = spr_projection(levels_mbbl)

    c1, c2, c3 = st.columns(3)
    c1.metric("SPR level", f"{levels_mbbl[0]:.0f} M bbl")
    if proj["mode"] == "depleting":
        c2.metric("Weekly draw", f"{proj['rate_mbbl_per_wk']:.1f} M bbl")
        c3.metric("Weeks to 400M floor",
                  f"{proj['weeks_to_floor']:.0f}" if proj["weeks_to_floor"] is not None else "N/A")
    elif proj["mode"] == "refilling":
        c2.metric("Weekly refill", f"{proj['rate_mbbl_per_wk']:.1f} M bbl")
        c3.metric("Weeks to full (714M)",
                  f"{proj['weeks_to_full']:.0f}" if proj["weeks_to_full"] is not None else "N/A")
    elif proj["mode"] == "flat":
        c2.metric("Weekly change", "~0")
        c3.metric("Timeline", "Flat")
    else:
        c2.metric("Weekly change", "N/A")
        c3.metric("Timeline", "N/A")
    st.caption("Rate is the average weekly SPR change. Depleting = weeks until the "
               "400M floor; refilling = weeks to reach nominal 714M capacity.")
