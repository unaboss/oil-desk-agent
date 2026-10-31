"""Tab 0: Oil Desk Agent, the on-chain decision log and its verifiable track record."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))  # so `agent.chain` imports when Streamlit runs app.py
EXPLORER = os.getenv("HSK_EXPLORER", "https://hashkey.blockscout.com")
RECORDS_URL = os.getenv("RECORDS_URL", "https://github.com/unaboss/oil-desk-agent/blob/main/records")
ACTIONS = {0: "HOLD", 1: "BUY", 2: "SELL"}
E18 = 10**18


def _deployment():
    net = os.getenv("NETWORK", "hashkey")
    p = REPO_ROOT / "deployments" / f"{net}.json"
    if os.getenv("VAULT_ADDRESS"):
        return {"vault": os.environ["VAULT_ADDRESS"], "deployBlock": int(os.getenv("DEPLOY_BLOCK", "0"))}
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data(ttl=120, show_spinner=False)
def load_onchain(rpc, vault_addr, from_block):
    from web3 import Web3
    from agent.chain import ABI

    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    v = w3.eth.contract(address=Web3.to_checksum_address(vault_addr), abi=ABI)
    latest = w3.eth.block_number
    dec, rej = [], []
    step = 50_000
    for start in range(from_block, latest + 1, step):
        end = min(latest, start + step - 1)
        dec += v.events.Decision.get_logs(from_block=start, to_block=end)
        rej += v.events.Rejected.get_logs(from_block=start, to_block=end)
    times = {}
    rows = []
    rejected = {e["args"]["id"]: (ACTIONS[e["args"]["action"]], e["args"]["reason"]) for e in rej}
    for e in dec:
        bn = e["blockNumber"]
        if bn not in times:
            times[bn] = w3.eth.get_block(bn)["timestamp"]
        a = e["args"]
        rows.append({
            "id": a["id"],
            "time": datetime.fromtimestamp(times[bn], tz=timezone.utc),
            "action": rejected[a["id"]][0] if a["id"] in rejected else ACTIONS[a["action"]],
            "blocked": rejected[a["id"]][1] if a["id"] in rejected else None,
            "amount_in": a["amountIn"] / E18,
            "amount_out": a["amountOut"] / E18,
            "confidence": a["confidence"],
            "wti": a["priceE8"] / 1e8,
            "reason": a["rationale"],
            "hash": a["rationaleHash"].hex() if isinstance(a["rationaleHash"], bytes) else str(a["rationaleHash"]),
            "tx": e["transactionHash"].to_0x_hex(),
        })
    base, quote = v.functions.balances().call()
    m = v.functions.mandate().call()
    return rows, base / E18, quote / E18, m


def score_calls(rows, market_data, horizon_days=3):
    """A call is right if WTI moved its way `horizon_days` trading days later. HOLDs aren't scored."""
    wti = market_data.get("wti") or {}
    s = pd.Series(wti.get("close", []), index=pd.to_datetime(wti.get("dates", [])), dtype=float).dropna()
    out = []
    for r in rows:
        if r["action"] == "HOLD" or r["blocked"] or s.empty:
            out.append(None)
            continue
        day = pd.Timestamp(r["time"].date())
        later = s[s.index > day]
        if len(later) < horizon_days:
            out.append(None)  # too early to judge
            continue
        move = later.iloc[horizon_days - 1] / r["wti"] - 1
        out.append(move > 0 if r["action"] == "BUY" else move < 0)
    return out


def render_agent_tab(market_data):
    st.subheader("Oil Desk Agent: every call on-chain before the outcome is known")
    dep = _deployment()
    if not dep:
        st.info("The agent vault isn't deployed yet. Once it is, this tab shows every decision from HashKey Chain.")
        return
    rpc = os.getenv("RPC_URL", "https://mainnet.hsk.xyz")
    try:
        rows, bbl, usd, m = load_onchain(rpc, dep["vault"], int(dep.get("deployBlock", 0)))
    except Exception as e:  # chain unreachable should never break the dashboard
        st.warning(f"Couldn't read HashKey Chain right now: {e}")
        return

    wti_now = (market_data.get("wti") or {}).get("close", [None])[-1] or (rows[-1]["wti"] if rows else 0)
    value = usd + bbl * (wti_now or 0)
    start_value = 10_000.0
    verdicts = score_calls(rows, market_data)
    judged = [v for v in verdicts if v is not None]
    hit = (sum(judged) / len(judged)) if judged else None

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Decisions on-chain", len(rows))
    c2.metric("Book (paper)", f"{bbl:,.1f} bbl + ${usd:,.0f}")
    c3.metric("Book value", f"${value:,.0f}", f"{(value / start_value - 1):+.1%} vs $10k start")
    c4.metric("Verified hit rate (3-day)", f"{hit:.0%}" if hit is not None else "too early", f"{len(judged)} calls judged")
    c5.metric("Blocked by mandate", sum(1 for r in rows if r["blocked"]))
    st.caption(
        f"Mandate (enforced by the contract): max buy ${m[0] / E18:,.0f}, max sell {m[1] / E18:,.0f} bbl, "
        f"daily ${m[2] / E18:,.0f} / {m[3] / E18:,.0f} bbl, slippage {m[4] / 100:.2f}%"
        + (" · **PAUSED**" if m[5] else "")
        + f" · Vault [{dep['vault'][:10]}…]({EXPLORER}/address/{dep['vault']})"
    )

    if not rows:
        st.write("No decisions yet.")
        return
    table = pd.DataFrame([{
        "#": r["id"],
        "When (UTC)": r["time"].strftime("%Y-%m-%d %H:%M"),
        "Call": f"BLOCKED {r['action']}" if r["blocked"] else r["action"],
        "Size": "–" if r["blocked"] else (f"${r['amount_in']:,.0f} → {r['amount_out']:,.1f} bbl" if r["action"] == "BUY"
                 else f"{r['amount_in']:,.1f} bbl → ${r['amount_out']:,.0f}" if r["action"] == "SELL" else "–"),
        "WTI": f"${r['wti']:.2f}",
        "Conf.": r["confidence"],
        "Right?": {True: "✅", False: "❌", None: "–"}[v],
        "Agent's reasoning (on-chain)": r["reason"] + (f"  ⛔ {r['blocked']}" if r["blocked"] else ""),
        "Proof": f"{EXPLORER}/tx/{r['tx']}",
        "Full record": f"{RECORDS_URL}/{r['hash'].removeprefix('0x')}.json",
    } for r, v in zip(rows, verdicts)][::-1])
    st.dataframe(table, hide_index=True, use_container_width=True, column_config={
        "Proof": st.column_config.LinkColumn(display_text="tx ↗"),
        "Full record": st.column_config.LinkColumn(display_text="json ↗"),
    })
    st.caption("Each call's full input (signals, crowd odds, model output) is hashed with keccak256 and the hash is written "
               "on-chain in the same transaction. Anyone can re-hash the JSON record and check it matches.")
