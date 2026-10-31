"""Replay the agent over past days on a LOCAL chain with demo-mode SAMPLE data.

For screenshots and the demo video only. It never touches mainnet: it refuses to
run unless the RPC is localhost. Usage (after `HH_INITIAL_DATE=... npx hardhat node`
and a localhost deploy):

    OIL_DESK_DEMO=1 python agent/demo_history.py --from 2026-08-04 --every 2
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "oil_dashboard"))
os.environ.setdefault("OIL_DESK_DEMO", "1")

import pandas as pd  # noqa: E402
from eth_account import Account  # noqa: E402
from web3 import Web3  # noqa: E402

from data import demo_mode  # noqa: E402
from agent import brain, chain, oil_view  # noqa: E402

HARDHAT_KEY0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
START = "2025-12-01"


def truncate(d, day):
    if not d or "dates" not in d:
        return d
    keep = [i for i, x in enumerate(d["dates"]) if x <= day]
    return {k: ([v[i] for i in keep] if isinstance(v, list) and len(v) == len(d["dates"]) else v) for k, v in d.items()}


_CTX = {}


def _view_for(day):
    m = {k: truncate(v, day) for k, v in _CTX["market"].items()}
    e = {k: truncate(v, day) for k, v in _CTX["eia"].items()}
    return oil_view.build_view(m, e, _CTX["cot"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2026-08-04")
    ap.add_argument("--to", dest="end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--every", type=int, default=2, help="decide every N business days")
    ap.add_argument("--mandate-test", dest="mandate_test", default=None,
                    help="on this day, first send a deliberately oversized BUY to show the vault refusing it")
    args = ap.parse_args()

    rpc = os.getenv("RPC_URL", "http://127.0.0.1:8545")
    if "127.0.0.1" not in rpc and "localhost" not in rpc:
        sys.exit("demo_history only runs against a local node")
    demo_mode.install()
    from data.fetcher_yfinance import get_all_market_data
    from data.fetcher_eia import get_all_eia_data
    import data.fetcher_cot as fc

    market = get_all_market_data(start=START, end=args.end)
    eia = get_all_eia_data(start=START, end=args.end)
    cot = fc.get_cot_data()

    dep = json.loads((ROOT / "deployments" / "localhost.json").read_text())
    w3, vault = chain.connect(rpc, dep["vault"])
    acct = Account.from_key(os.getenv("AGENT_KEY", HARDHAT_KEY0))

    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range(args.start, args.end)][:: args.every]
    # The market view doesn't depend on the book, so build all of them in parallel first
    # (the dashboard's audit makes each one slow), then replay the calls in order.
    _CTX.update(market=market, eia=eia, cot=cot)
    from multiprocessing import Pool
    with Pool(min(4, os.cpu_count() or 1)) as pool:
        views = pool.map(_view_for, days)
    for day, view in zip(days, views):
        portfolio, mandate = chain.read_state(vault)
        if day == args.mandate_test:
            ts = int(datetime.fromisoformat(f"{day}T14:55:00+00:00").timestamp())
            w3.provider.make_request("evm_setNextBlockTimestamp", [ts])
            test = {"action": "BUY", "fraction": 1.0, "confidence": 99, "reason": ""}
            big = mandate["maxTradeQuote"] * 3
            p8 = int(round(view["wti_price"] * 1e8))
            exp = big * 10**8 // p8
            why = "[mandate test] Deliberate order for 3x the per-trade cap, sent to show the vault refuses it."
            h = Web3.keccak(text=json.dumps({"day": day, "mandate_test": True, "amount_in": str(big)}, sort_keys=True))
            rc = chain.submit(w3, vault, acct, test, (big, exp, exp), view["wti_price"], h, why)
            print(day, "MANDATE TEST", "ok" if rc["status"] == 1 else "FAILED")
        decision, model, _ = brain.decide(view, [], portfolio)
        amounts = chain.size_order(decision, view["wti_price"], portfolio, mandate)
        decision, amounts = chain.finalise(decision, amounts)
        ts = int(datetime.fromisoformat(f"{day}T15:00:00+00:00").timestamp())
        w3.provider.make_request("evm_setNextBlockTimestamp", [ts])
        h = Web3.keccak(text=json.dumps({"day": day, "view": view, "decision": decision}, sort_keys=True))
        rc = chain.submit(w3, vault, acct, decision, amounts, view["wti_price"], h, f"[{model}] {decision['reason']}")
        print(day, decision["action"], f"{view['wti_price']:.2f}", "ok" if rc["status"] == 1 else "FAILED")


if __name__ == "__main__":
    main()
