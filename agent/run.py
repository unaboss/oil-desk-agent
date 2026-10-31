"""One Oil Desk cycle: view -> crowd -> decide -> size -> record on-chain.

Env: RPC_URL, VAULT_ADDRESS (or deployments/<NETWORK>.json), AGENT_KEY,
     LLM_API_KEY / LLM_BASE_URL / LLM_MODEL (optional), EIA_API_KEY,
     RECORDS_DIR (default records/), OFFLINE_VIEW=path.json for tests.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eth_account import Account  # noqa: E402
from web3 import Web3  # noqa: E402

from agent import brain, chain, crowd, oil_view  # noqa: E402


def vault_address():
    if os.getenv("VAULT_ADDRESS"):
        return os.environ["VAULT_ADDRESS"]
    net = os.getenv("NETWORK", "hashkey")
    return json.loads((ROOT / "deployments" / f"{net}.json").read_text())["vault"]


def main():
    rpc = os.getenv("RPC_URL", "https://mainnet.hsk.xyz")
    w3, vault = chain.connect(rpc, vault_address())
    account = Account.from_key(os.environ["AGENT_KEY"])

    if os.getenv("OFFLINE_VIEW"):
        view = json.loads(Path(os.environ["OFFLINE_VIEW"]).read_text())
        crowd_view = view.pop("_crowd", [])
    else:
        view = oil_view.fetch_view()
        crowd_view = crowd.fetch_crowd()

    portfolio, mandate = chain.read_state(vault)
    decision, model, raw = brain.decide(view, crowd_view, portfolio)
    amounts = chain.size_order(decision, view["wti_price"], portfolio, mandate)

    record = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "view": view, "crowd": crowd_view, "portfolio": portfolio,
        "decision": decision, "model": model, "raw_model_output": raw,
        "order": {"amountIn": str(amounts[0]), "expectedOut": str(amounts[1]), "minOut": str(amounts[2])},
    }
    blob = json.dumps(record, sort_keys=True, separators=(",", ":"))
    h = Web3.keccak(text=blob)
    rec_dir = Path(os.getenv("RECORDS_DIR", ROOT / "records"))
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / f"{h.hex().removeprefix('0x')}.json").write_text(blob)

    short = f"[{model}] {decision['reason']}"[:300]
    rc = chain.submit(w3, vault, account, decision, amounts, view["wti_price"], h, short)
    print(json.dumps({"tx": rc["transactionHash"].to_0x_hex(), "status": rc["status"], "action": decision["action"],
                      "confidence": decision["confidence"], "wti": view["wti_price"], "hash": h.to_0x_hex()}))
    return 0 if rc["status"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
