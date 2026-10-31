"""MandateVault client (web3.py)."""
from web3 import Web3

E18 = 10**18
ABI = [
    {"type": "function", "name": "decide", "stateMutability": "nonpayable",
     "inputs": [{"name": "action", "type": "uint8"}, {"name": "amountIn", "type": "uint256"},
                {"name": "expectedOut", "type": "uint256"}, {"name": "minOut", "type": "uint256"},
                {"name": "confidence", "type": "uint8"}, {"name": "priceE8", "type": "int256"},
                {"name": "rationaleHash", "type": "bytes32"}, {"name": "rationale", "type": "string"}],
     "outputs": [{"name": "id", "type": "uint256"}, {"name": "amountOut", "type": "uint256"}]},
    {"type": "function", "name": "balances", "stateMutability": "view", "inputs": [],
     "outputs": [{"name": "baseBal", "type": "uint256"}, {"name": "quoteBal", "type": "uint256"}]},
    {"type": "function", "name": "mandate", "stateMutability": "view", "inputs": [],
     "outputs": [{"name": "maxTradeQuote", "type": "uint256"}, {"name": "maxTradeBase", "type": "uint256"},
                 {"name": "dailyCapQuote", "type": "uint256"}, {"name": "dailyCapBase", "type": "uint256"},
                 {"name": "maxSlippageBps", "type": "uint16"}, {"name": "paused", "type": "bool"}]},
    {"type": "function", "name": "decisionCount", "stateMutability": "view", "inputs": [],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "event", "name": "Decision", "anonymous": False,
     "inputs": [{"name": "id", "type": "uint256", "indexed": True}, {"name": "action", "type": "uint8", "indexed": False},
                {"name": "amountIn", "type": "uint256", "indexed": False}, {"name": "amountOut", "type": "uint256", "indexed": False},
                {"name": "confidence", "type": "uint8", "indexed": False}, {"name": "priceE8", "type": "int256", "indexed": False},
                {"name": "rationaleHash", "type": "bytes32", "indexed": False}, {"name": "rationale", "type": "string", "indexed": False}]},
    {"type": "event", "name": "Rejected", "anonymous": False,
     "inputs": [{"name": "id", "type": "uint256", "indexed": True}, {"name": "action", "type": "uint8", "indexed": False},
                {"name": "amountIn", "type": "uint256", "indexed": False}, {"name": "reason", "type": "string", "indexed": False}]},
]
ACTION_CODE = {"HOLD": 0, "BUY": 1, "SELL": 2}
ACTION_NAME = {v: k for k, v in ACTION_CODE.items()}


def connect(rpc, vault):
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    return w3, w3.eth.contract(address=Web3.to_checksum_address(vault), abi=ABI)


def read_state(vault):
    base, quote = vault.functions.balances().call()
    m = vault.functions.mandate().call()
    mandate = dict(zip(["maxTradeQuote", "maxTradeBase", "dailyCapQuote", "dailyCapBase", "maxSlippageBps", "paused"], m))
    # exact balances ride along under "_" keys (kept out of the LLM prompt) so sizing never
    # spends a float-rounded amount the vault doesn't hold
    return {"barrels": base / E18, "usd": quote / E18, "_barrels_wei": base, "_usd_wei": quote}, mandate


def _floor_units(x):
    """Float balance -> 1e18 units, rounded down to a millionth (fallback when exact wei is unknown)."""
    return max(0, int(x * 1e6)) * 10**12


def size_order(decision, price, portfolio, mandate):
    """Convert a decision into (amountIn, expectedOut, minOut) in 1e18 units.

    BUY spends USD (quote) for barrels (base); SELL spends barrels for USD."""
    if decision["action"] == "HOLD" or not price:
        return 0, 0, 0
    p = int(round(price * 1e8))  # USD per barrel, 1e8
    if decision["action"] == "BUY":
        amount_in = mandate["maxTradeQuote"] * int(decision["fraction"] * 1000) // 1000
        amount_in = min(amount_in, portfolio.get("_usd_wei", _floor_units(portfolio["usd"])))
        expected = amount_in * 10**8 // p
    else:
        amount_in = mandate["maxTradeBase"] * int(decision["fraction"] * 1000) // 1000
        amount_in = min(amount_in, portfolio.get("_barrels_wei", _floor_units(portfolio["barrels"])))
        expected = amount_in * p // 10**8
    cap = mandate["maxTradeQuote"] if decision["action"] == "BUY" else mandate["maxTradeBase"]
    if amount_in < cap // 10:  # under a tenth of a full ticket isn't worth a trade (finalise turns it into a HOLD)
        return 0, 0, 0
    bps = mandate["maxSlippageBps"]
    min_out = (expected * (10_000 - bps) + 9_999) // 10_000  # round up: passes the on-chain check exactly
    return amount_in, expected, min_out


def finalise(decision, amounts):
    """A BUY with no cash left, or a SELL with nothing to sell, becomes an honest HOLD."""
    if decision["action"] != "HOLD" and amounts[0] == 0:
        why = "fully invested, too little cash left" if decision["action"] == "BUY" else "too few barrels to sell"
        return {**decision, "action": "HOLD", "fraction": 0.0,
                "reason": f"({why}) {decision['reason']}"[:260]}, (0, 0, 0)
    return decision, amounts


def submit(w3, vault, account, decision, amounts, price, rationale_hash, rationale):
    amount_in, expected, min_out = amounts
    fn = vault.functions.decide(ACTION_CODE[decision["action"]], amount_in, expected, min_out,
                                decision["confidence"], int(round((price or 0) * 1e8)),
                                rationale_hash, rationale)
    # Estimate, then pad: a decision that lands just after UTC midnight takes the
    # daily-counter reset path, which costs more than the estimate made a moment earlier.
    gas = int(fn.estimate_gas({"from": account.address}) * 1.3) + 25_000
    tx = fn.build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": w3.eth.chain_id,
        "gas": gas,
    })
    signed = account.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(h, timeout=180)
