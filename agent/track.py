"""Read the on-chain decision log and score it against what WTI actually did."""
from datetime import datetime, timezone

import pandas as pd

from agent.chain import ABI, ACTION_NAME

E18 = 10**18
HORIZON_DAYS = 3


def load_decisions(w3, vault, from_block=0, step=50_000):
    latest = w3.eth.block_number
    dec, rej = [], []
    for start in range(from_block, latest + 1, step):
        end = min(latest, start + step - 1)
        dec += vault.events.Decision.get_logs(from_block=start, to_block=end)
        rej += vault.events.Rejected.get_logs(from_block=start, to_block=end)
    rejected = {e["args"]["id"]: (ACTION_NAME[e["args"]["action"]], e["args"]["reason"]) for e in rej}
    times, rows = {}, []
    for e in dec:
        bn = e["blockNumber"]
        if bn not in times:
            times[bn] = w3.eth.get_block(bn)["timestamp"]
        a = e["args"]
        rh = a["rationaleHash"]
        rows.append({
            "id": a["id"],
            "time": datetime.fromtimestamp(times[bn], tz=timezone.utc),
            "action": rejected[a["id"]][0] if a["id"] in rejected else ACTION_NAME[a["action"]],
            "blocked": rejected[a["id"]][1] if a["id"] in rejected else None,
            "amount_in": a["amountIn"] / E18,
            "amount_out": a["amountOut"] / E18,
            "confidence": a["confidence"],
            "wti": a["priceE8"] / 1e8,
            "reason": a["rationale"],
            "hash": "0x" + (rh.hex() if isinstance(rh, (bytes, bytearray)) else str(rh)).removeprefix("0x"),
            "tx": e["transactionHash"].to_0x_hex(),
            "block": bn,
        })
    rows.sort(key=lambda r: r["id"])
    return rows


def close_series(market_data):
    wti = (market_data or {}).get("wti") or {}
    return pd.Series(wti.get("close", []), index=pd.to_datetime(wti.get("dates", [])), dtype=float).dropna()


def score(rows, closes, horizon_days=HORIZON_DAYS):
    """A BUY is right if WTI is higher `horizon_days` trading days later; a SELL if lower.
    HOLDs and blocked attempts aren't scored; calls too recent to judge return None."""
    out = []
    for r in rows:
        if r["action"] == "HOLD" or r["blocked"] or closes.empty or not r["wti"]:
            out.append(None)
            continue
        later = closes[closes.index > pd.Timestamp(r["time"].date())]
        if len(later) < horizon_days:
            out.append(None)
            continue
        move = later.iloc[horizon_days - 1] / r["wti"] - 1
        out.append(bool(move > 0) if r["action"] == "BUY" else bool(move < 0))
    return out
