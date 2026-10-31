"""Tab 9: Research & Narrative — Trump event study, bot-mention proxy, losing
traders, officials/military tracker, statements-vs-price.

A navigable research tool. Five inner sub-tabs, each self-contained with a
methodology note. All data is free/manual (curated CSVs + Google Trends) or
fetched from public RSS mirrors (officials & military tracker).
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots

from analysis.trump_event_study import compute_trump_event_study
from analysis.bot_narrative import compute_bot_narrative
from analysis.losing_traders import compute_losing_traders
from analysis.officials_tracker import (
    count_mentions_per_source,
    group_mentions_by_date,
    extract_iran_mentions,
)
from analysis.statement_returns import (
    aggregate_returns,
    classify_direction,
    compute_statement_returns,
    map_statement_dates,
)

CATEGORY_COLORS = {
    "officials": "#4CAF50",
    "military": "#F44336",
    "energy": "#FFC107",
    "state": "#2196F3",
    "unknown": "#9E9E9E",
}


CLASS_COLORS = {
    "Lagging": "#FFC107",
    "Pre-reversal": "#F44336",
    "Confirmation": "#4CAF50",
    "No signal": "#9E9E9E",
}


def render_research_tab(market_data, bot_trends_data, start=None, end=None, statements_data=None):
    st.subheader("Research & Narrative")
    with st.expander("Methodology & caveats", expanded=False):
        st.markdown(
            "**Trump oil narrative** — event study on WTI. For each curated "
            "statement we measure the return *before* he spoke (5d) and *after* "
            "(3d). 'Lagging' = big pre-move, little after → announced after the "
            "move was done. 'Pre-reversal' = post-move reverses direction. "
            "Source: manually curated `data/trump_oil_statements.csv`."
        )
        st.markdown(
            "**Bot mentions** — NARRATIVE PROXY only: Google Trends search "
            "interest in bot/platform terms (MetaTrader, TradingView, 3Commas…). "
            "It is NOT a count of bots actually trading oil."
        )
        st.markdown(
            "**Losing oil traders** — anonymous/aggregate proxy from public CTA "
            "databases and social-copy leaderboards (`data/losing_traders.csv`). "
            "Individual retail P&L is private; named entities are public funds."
        )
        st.markdown(
            "**Officials & military** — Truth Social has no public post API, so "
            "we track public statements via mirror sources: Google News RSS (one "
            "query per official) + official DOE/DoD/State press-release feeds. "
            "Officials items are kept when they touch oil topics; military items "
            "are kept only when they mention Iran. This is a statement tracker, "
            "not a transcript feed."
        )

    tab_trump, tab_bots, tab_traders, tab_officials, tab_statements = st.tabs([
        "Trump Oil Narrative",
        "Bot Mentions",
        "Losing Oil Traders",
        "Officials & Military",
        "Statements & Price",
    ])

    with tab_trump:
        _render_trump(market_data, start, end)

    with tab_bots:
        _render_bots(bot_trends_data, market_data)

    with tab_traders:
        _render_traders()

    with tab_officials:
        _render_officials(market_data, statements_data)

    with tab_statements:
        _render_statements_price(market_data, statements_data)

    st.markdown("---")
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **Trump Oil Narrative (inner tab):**
        - Studies how WTI price moved before and after Trump's oil-related statements.
        - **Lagging** — Big move happened BEFORE he spoke. He's commenting on something that already happened, not creating news. The market already priced it in.
        - **Pre-reversal** — Price reversed direction after he spoke. His statement may have changed market expectations.
        - **Confirmation** — Price kept moving in the same direction after he spoke. His statement aligned with what the market was already doing.
        - **No signal** — Neither window had a significant move. Statement had little impact.
        - The scatter plot puts each statement on a grid: x-axis = what happened before, y-axis = what happened after.

        **Bot Mentions (inner tab):**
        - Tracks Google searches for terms like "oil trading bot", "MetaTrader oil", etc.
        - This is a proxy — it doesn't count actual bots trading, just people searching for bot tools.
        - When the bot-mention index spikes, it may mean more algorithmic/automated trading is entering the oil market. More bots = more unpredictable short-term moves.
        - The correlation with WTI volatility tells you if bot activity and price turbulence are moving together.

        **Losing Oil Traders (inner tab):**
        - Shows the performance of tracked oil traders from public data (CTA funds, social-copy leaderboards).
        - When most tracked traders are losing money, it can be a contrarian signal. If everyone who's usually right is struggling, the market may be in an unusual phase.
        - Use this as context, not as a trade signal by itself.

        **Officials & Military (inner tab):**
        - Tracks public statements by oil-relevant officials (SecEnergy, SecInterior, SecState, SecDefense, EPA, FERC, EIA) and the military.
        - Mirror sources: Google News RSS + official DOE/DoD/State feeds (Truth Social has no public post API).
        - Officials items appear when the statement touches oil topics (oil, crude, sanctions, pipeline, etc.).
        - Military items appear ONLY when they mention Iran — this is the military/Iran signal feed.
        - The two-panel chart stacks statement counts (top) over WTI price (bottom) on one timeline, so you can read statement bursts against the price move — like a price/volume chart.
        - More statements in the feed = more public chatter on oil policy; a spike can precede policy moves.

        **Statements & Price (inner tab):**
        - Plots WTI price with a marker at every captured statement date, color-coded by category.
        - Measures what WTI did 1, 3 and 5 trading days AFTER each statement (forward returns).
        - Green markers = officials, red = military, amber = energy/DOE, blue = state.
        - Use it to see whether statements tend to land at tops, bottoms, or mid-move — and whether the market tends to rise or fall after each category.
        - This is the evidence base for building a statement-based trading indicator.
        """)


def _render_trump(market_data, start, end):
    study = compute_trump_event_study(market_data, start=start, end=end)

    if study["total"] == 0:
        st.info("No statements matched the current date range / WTI data.")
        return

    col_lag, col_sum = st.columns([1, 2])
    with col_lag:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=study["lag_rate"],
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#FFC107"},
                "steps": [
                    {"range": [0, 50], "color": "rgba(76,175,80,0.3)"},
                    {"range": [50, 100], "color": "rgba(255,193,7,0.3)"},
                ],
            },
            title={"text": "% Lagging (announced after move)"},
        ))
        fig.update_layout(height=220, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True, config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
        })
        st.caption(f"{study['classified']} classified of {study['total']} statements")

    with col_sum:
        s = study["summary"]
        fig = go.Figure(go.Bar(
            x=list(s.keys()),
            y=list(s.values()),
            marker_color=[CLASS_COLORS.get(k, "#9E9E9E") for k in s.keys()],
        ))
        fig.update_layout(
            title="Statement classification",
            height=220,
            template="plotly_dark",
            yaxis_title="count",
            dragmode="pan",
        )
        st.plotly_chart(fig, use_container_width=True, config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
        })

    events = study["events"]
    if events:
        fig = go.Figure()
        for klass, color in CLASS_COLORS.items():
            pts = [e for e in events if e["classification"] == klass]
            if not pts:
                continue
            fig.add_trace(go.Scatter(
                x=[e["pre_return_pct"] for e in pts],
                y=[e["fwd_return_pct"] for e in pts],
                mode="markers",
                name=klass,
                text=[f"{e['date']}: {e['statement']}" for e in pts],
                marker=dict(color=color, size=10),
            ))
        fig.add_hline(y=0, line=dict(color="#666", width=1))
        fig.add_vline(x=0, line=dict(color="#666", width=1))
        fig.update_layout(
            title="Pre-statement return (x) vs post-statement return (y)",
            height=420,
            template="plotly_dark",
            xaxis_title="5d return BEFORE statement (%)",
            yaxis_title="3d return AFTER statement (%)",
            hovermode="closest",
            dragmode="pan",
        )
        st.plotly_chart(fig, use_container_width=True, config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        })

    st.markdown("#### Statements")
    for e in events:
        color = CLASS_COLORS.get(e["classification"], "#9E9E9E")
        st.markdown(
            f"**{e['date']}** — <span style='color:{color}'>"
            f"{e['classification']}</span> — pre {e['pre_return_pct']:+.1f}% / "
            f"post {e['fwd_return_pct']:+.1f}%",
            unsafe_allow_html=True,
        )
        st.caption(e["statement"])


def _render_bots(bot_trends_data, market_data):
    narrative = compute_bot_narrative(bot_trends_data, market_data)

    if not narrative["available"]:
        st.info("Google Trends bot-mention data unavailable (rate-limited). Try refreshing later.")
        return

    dates = [pd.to_datetime(d) for d in narrative["dates"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=narrative["index"], mode="lines",
        name="Bot-mention index", line=dict(color="#00BCD4", width=2),
    ))
    fig.update_layout(
        title="Bot-Mention Index (normalized avg of search interest)",
        height=350,
        template="plotly_dark",
        hovermode="x unified",
        dragmode="pan",
    )
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.03))
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })

    col1, col2, col3 = st.columns(3)
    col1.metric("Latest index", narrative["latest_index"])
    col2.metric("Peak date", narrative["peak_date"] or "—")
    col3.metric("Corr. with WTI vol",
                f"{narrative['corr_vol']:.2f}" if narrative["corr_vol"] is not None else "—")

    st.markdown("#### Search interest by term")
    fig2 = go.Figure()
    for kw in narrative["keywords"]:
        vals = bot_trends_data["values"].get(kw, [])
        fig2.add_trace(go.Scatter(
            x=dates, y=vals, mode="lines", name=kw,
        ))
    fig2.update_layout(height=350, template="plotly_dark", hovermode="x unified", dragmode="pan")
    fig2.update_xaxes(rangeslider=dict(visible=True, thickness=0.03))
    st.plotly_chart(fig2, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })
    st.caption("Narrative proxy only — search interest, not actual bot trading volume.")


def _render_traders():
    data = compute_losing_traders()
    if not data["available"]:
        st.info("No losing-traders data found (data/losing_traders.csv).")
        return

    stats = data["stats"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tracked", stats["total"])
    c2.metric("Negative YTD", stats["negative"])
    c3.metric("Median YTD %", f"{stats['median_ytd']:+.1f}")
    c4.metric("Median drawdown %", f"{stats['median_drawdown']:.1f}")

    rows = data["rows"]
    names = [r["name"] for r in rows]
    ytd = [r["ytd_return_pct"] for r in rows]
    dd = [r["max_drawdown_pct"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names, x=ytd, orientation="h", name="YTD %",
        marker=dict(color=["#F44336" if v < 0 else "#4CAF50" for v in ytd]),
    ))
    fig.add_trace(go.Bar(
        y=names, x=dd, orientation="h", name="Max DD %",
        marker=dict(color="#9C27B0"),
    ))
    fig.update_layout(
        title="YTD return & max drawdown (worst at top)",
        height=420, template="plotly_dark", barmode="group",
        xaxis_title="%", yaxis=dict(autorange="reversed"),
        dragmode="pan",
    )
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
    })

    st.markdown("#### Detail")
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    st.caption("Anonymous/aggregate proxy from public CTA & social-copy data. Named rows are public funds only.")


def _render_statements_over_wti(items, market_data):
    """Two-panel chart: statement counts (top) + WTI price (bottom), shared axis.

    Mirrors the classic price+volume layout so you can read statement activity
    against the price move on the same timeline.
    """
    series = group_mentions_by_date(items)
    wti = market_data.get("wti", {})
    wti_dates = wti.get("dates", [])
    wti_close = wti.get("close", [])

    if not series["dates"]:
        st.info("No statements with dates to plot.")
        return

    if not wti_dates or not wti_close:
        st.warning("WTI price data unavailable for this date range — statement bars shown without the price overlay.")

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.6, 0.4],
    )

    for cat, vals in series["categories"].items():
        fig.add_trace(go.Bar(
            x=[pd.to_datetime(d) for d in series["dates"]],
            y=vals, name=cat,
            marker_color=CATEGORY_COLORS.get(cat, "#9E9E9E"),
            legendgroup=cat,
        ), row=1, col=1)

    if wti_dates and wti_close:
        fig.add_trace(go.Scatter(
            x=[pd.to_datetime(d) for d in wti_dates],
            y=wti_close, mode="lines", name="WTI close",
            line=dict(color="#90A4AE", width=1.5),
            legendgroup="WTI",
        ), row=2, col=1)

    fig.update_layout(
        title="Statements over time (top) vs WTI price (bottom)",
        height=520, template="plotly_dark", barmode="stack",
        showlegend=True, hovermode="x unified", dragmode="pan",
    )
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_yaxes(title_text="statements", row=1, col=1)
    fig.update_yaxes(title_text="WTI ($)", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })


def _render_officials(market_data, statements_data):
    if not statements_data or not statements_data.get("available"):
        st.info("No officials/military statement data yet. Refresh to fetch from Google News RSS + agency feeds.")
        return

    items = statements_data["items"]
    store_items = statements_data.get("store_items", items)
    counts = count_mentions_per_source(items)
    store_counts = count_mentions_per_source(store_items)
    categories = counts["categories"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Officials statements", categories.get("officials", 0))
    c2.metric("Military / Iran", categories.get("military", 0))
    c3.metric("Agency statements",
              sum(categories.get(k, 0) for k in ("energy", "state")))
    c4.metric("Total captured (all-time)", store_counts["total"])

    view = st.radio(
        "Show", ["Current window", "All captured"], horizontal=True,
        label_visibility="collapsed",
    )
    shown_items = store_items if view == "All captured" else items

    _render_statements_over_wti(shown_items, market_data)

    st.markdown("#### Military / Iran feed")
    iran_items = extract_iran_mentions(shown_items)
    if not iran_items:
        st.caption("No military statements mentioning Iran in the current window.")
    for item in iran_items[:10]:
        st.markdown(
            f":red[**{item['source']}**] — {item.get('date', '')[:16]}  "
            f"[{item['title']}]({item['link']})"
        )
        if item.get("description"):
            st.caption(item["description"][:300])

    st.markdown("#### All tracked statements")
    if shown_items:
        df = pd.DataFrame(shown_items)
        df = df[["date", "category", "source", "title", "link", "description"]]
        st.dataframe(df, use_container_width=True)
    st.caption("Officials: Google News RSS per official + DOE/DoD/State feeds. Military items are Iran-filtered. "
               "All captured statements are stored permanently in data/officials_statements.csv.")


def _render_statements_price(market_data, statements_data):
    if not statements_data or not statements_data.get("available"):
        st.info("No statement data yet — capture statements first (Tab 9 → Officials & Military).")
        return

    wti = market_data.get("wti", {})
    if not wti.get("dates") or not wti.get("close"):
        st.info("No WTI price data available for this date range.")
        return

    items = statements_data.get("store_items") or statements_data.get("items") or []
    mapped = map_statement_dates(items, wti)
    if not mapped["available"]:
        st.info("No statements overlap the WTI date range.")
        return

    markers = mapped["markers"]
    price_dates = [pd.to_datetime(d) for d in wti["dates"]]
    price_close = wti["close"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=price_dates, y=price_close, mode="lines",
        name="WTI", line=dict(color="#90A4AE", width=1.5),
    ))

    for cat in sorted({m["category"] for m in markers}):
        cat_markers = [m for m in markers if m["category"] == cat]
        fig.add_trace(go.Scatter(
            x=[pd.to_datetime(m["date"]) for m in cat_markers],
            y=[m["close"] for m in cat_markers],
            mode="markers",
            name=cat,
            marker=dict(
                color=CATEGORY_COLORS.get(cat, "#9E9E9E"),
                size=9, symbol="circle",
            ),
            text=[f"{m['source']}: {m['title'][:80]}" for m in cat_markers],
            hovertemplate="%{x}<br>%{text}<br>WTI %{y:.2f}<extra></extra>",
        ))

    fig.update_layout(
        title="WTI price with statement dates (markers colored by category)",
        height=420, template="plotly_dark",
        hovermode="closest", dragmode="pan",
        xaxis_title="", yaxis_title="WTI close ($)",
    )
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })
    st.caption(f"{len(markers)} statements mapped onto WTI over {len(price_dates)} trading days.")

    study = compute_statement_returns(items, wti)
    if not study["available"]:
        st.info("No statements have a complete forward-return window yet.")
        return
    events = study["events"]

    st.markdown("#### Mean forward return after statement (by category)")
    agg = aggregate_returns(events)
    rows = []
    categories = list(agg["categories"].keys())
    for horizon in ("fwd_1d", "fwd_3d", "fwd_5d"):
        row = {"horizon": horizon}
        for cat in categories:
            stats = agg["categories"][cat][horizon]
            row[cat] = stats["mean"] if stats["mean"] is not None else None
        rows.append(row)

    fig2 = go.Figure()
    for cat in categories:
        fig2.add_trace(go.Bar(
            x=[r["horizon"] for r in rows],
            y=[r[cat] if r[cat] is not None else 0 for r in rows],
            name=cat, marker_color=CATEGORY_COLORS.get(cat, "#9E9E9E"),
        ))
    fig2.update_layout(
        title="Mean forward return after statement (%)",
        height=320, template="plotly_dark", barmode="group",
        yaxis_title="mean %",
    )
    st.plotly_chart(fig2, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
    })

    st.markdown("#### Direction hit-rates (3-day horizon)")
    classified = classify_direction(events, horizon=3)
    rate_rows = []
    for cat, rate in classified["hit_rates"].items():
        rate_rows.append({
            "category": cat,
            "up %": rate["up"],
            "down %": rate["down"],
            "flat %": rate["flat"],
            "count": rate["count"],
        })
    rate_rows.append({
        "category": "overall",
        "up %": classified["overall"]["up"],
        "down %": classified["overall"]["down"],
        "flat %": classified["overall"]["flat"],
        "count": classified["overall"]["count"],
    })
    st.dataframe(pd.DataFrame(rate_rows), use_container_width=True)

    st.markdown("#### Detail")
    detail = pd.DataFrame(events)
    detail = detail[["date", "category", "source", "title", "fwd_1d", "fwd_3d", "fwd_5d"]]
    st.dataframe(detail, use_container_width=True)
