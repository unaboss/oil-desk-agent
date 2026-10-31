"""Export everything the public Oil Desk page shows into site/data/oildesk.json.

Runs after each agent cycle in GitHub Actions (live data), or locally with
OIL_DESK_DEMO=1 against a local node (sample data, flagged on the page).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "oil_dashboard"))

from agent import chain, crowd, oil_view, track  # noqa: E402

PAPER_START_USD = 10_000.0
SAMPLE_CROWD = [
    {"question": "Will WTI close above $65 by end of November?", "odds": {"Yes": 0.31, "No": 0.69}, "volume_usd": 0, "ends": None},
    {"question": "Will crude oil hit $50 in 2026?", "odds": {"Yes": 0.08, "No": 0.92}, "volume_usd": 0, "ends": None},
]


def _deployment(network):
    if os.getenv("VAULT_ADDRESS"):
        return {"vault": os.environ["VAULT_ADDRESS"], "deployBlock": int(os.getenv("DEPLOY_BLOCK", "0"))}
    p = ROOT / "deployments" / f"{network}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _market(sample):
    from data import demo_mode
    if sample:
        demo_mode.install()
    from data.fetcher_yfinance import get_all_market_data
    from data.fetcher_eia import get_all_eia_data
    import data.fetcher_cot as fc

    end = datetime.now(timezone.utc)
    start = "2025-12-01" if sample else (end - timedelta(days=200)).strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")
    market = get_all_market_data(start=start, end=end_s)
    try:
        eia = get_all_eia_data(start=start, end=end_s)
    except Exception:
        eia = {}
    try:
        cot = fc.get_cot_data()
    except Exception:
        cot = {}
    return market, eia, cot


def build(network="hashkey", rpc=None, sample=False):
    explorer = os.getenv("HSK_EXPLORER", "https://hashkey.blockscout.com" if network == "hashkey" else "https://testnet-explorer.hsk.xyz")
    market, eia, cot = _market(sample)
    view = oil_view.build_view(market, eia, cot)
    crowd_now = SAMPLE_CROWD if sample else crowd.fetch_crowd()
    closes = track.close_series(market)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample": sample,
        "network": network,
        "explorer": explorer,
        "repo": os.getenv("REPO_URL", "https://github.com/unaboss/oil-desk-agent"),
        "streamlit": os.getenv("STREAMLIT_URL", ""),
        "now": {"view": view, "crowd": crowd_now},
        "wti": [{"d": d.strftime("%Y-%m-%d"), "c": round(float(c), 3)} for d, c in closes.tail(130).items()],
        "vault": None, "mandate": None, "book": None, "stats": None, "decisions": [],
    }

    dep = _deployment(network)
    if dep:
        w3, vault = chain.connect(rpc or os.getenv("RPC_URL", "https://mainnet.hsk.xyz"), dep["vault"])
        rows = track.load_decisions(w3, vault, int(dep.get("deployBlock", 0)))
        verdicts = track.score(rows, closes)
        portfolio, mandate = chain.read_state(vault)
        last_px = float(closes.iloc[-1]) if not closes.empty else (rows[-1]["wti"] if rows else 0.0)
        value = portfolio["usd"] + portfolio["barrels"] * last_px
        judged = [v for v in verdicts if v is not None]
        out["vault"] = dep["vault"]
        out["mandate"] = {
            "max_buy_usd": mandate["maxTradeQuote"] / 1e18, "max_sell_bbl": mandate["maxTradeBase"] / 1e18,
            "daily_usd": mandate["dailyCapQuote"] / 1e18, "daily_bbl": mandate["dailyCapBase"] / 1e18,
            "slippage_pct": mandate["maxSlippageBps"] / 100, "paused": mandate["paused"],
        }
        out["book"] = {"barrels": portfolio["barrels"], "usd": portfolio["usd"], "value": value,
                       "start": PAPER_START_USD, "mark_price": last_px}
        out["stats"] = {"calls": len(rows), "trades": sum(1 for r in rows if r["action"] != "HOLD" and not r["blocked"]),
                        "judged": len(judged), "hits": sum(judged),
                        "hit_rate": (sum(judged) / len(judged)) if judged else None,
                        "blocked": sum(1 for r in rows if r["blocked"])}
        out["decisions"] = [{**{k: v for k, v in r.items() if k != "time"}, "time": r["time"].isoformat(), "right": v}
                            for r, v in zip(rows, verdicts)]
    return out


def main():
    network = os.getenv("NETWORK", "hashkey")
    sample = os.getenv("OIL_DESK_DEMO") == "1"
    data = build(network=network, rpc=os.getenv("RPC_URL"), sample=sample)
    dest = Path(os.getenv("SITE_DATA", ROOT / "site" / "data" / "oildesk.json"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=1, default=str))
    print(f"wrote {dest} ({len(data['decisions'])} decisions, sample={sample})")


if __name__ == "__main__":
    main()
