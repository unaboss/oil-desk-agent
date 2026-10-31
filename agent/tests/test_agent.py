import json

import numpy as np
import pytest

from agent import brain, chain, crowd, oil_view

DATES = ["2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04", "2025-12-05", "2025-12-08"]


def market(bullish=True):
    up = bullish
    return {
        "wti": {"dates": DATES, "close": [68.5, 69.1, 68.8, 69.5, 70.0, 71.0 if up else 67.0]},
        "volume_anomaly": {"dates": DATES, "volume_ratio": [1.5] * 6 if up else [0.5] * 6},
        "crack": {"dates": DATES, "crack": [18.0] * 6 if up else [12.0] * 6, "crack_5ma": [np.nan] * 5 + [15.0]},
        "curve": {"spread_dates": DATES, "brent_wti_spread": [4.0] * 6 if up else [-4.0] * 6},
        "dxy": {"dates": DATES, "close": [106, 105.8, 105.5, 105.2, 104.9, 104.5] if up else [104, 104.2, 104.5, 104.8, 105, 105.5]},
        "ovx": {"dates": DATES, "close": [30, 31, 32, 33, 34, 35]},
    }


EIA_BULL = {"crude": {"dates": ["2025-12-03"], "changes": [-2.5]}}
COT_OK = {"net_long": 50000}


def test_build_view_bullish():
    v = oil_view.build_view(market(True), EIA_BULL, COT_OK)
    assert v["wti_price"] == 71.0
    assert v["confluence_direction"] == "bullish"
    assert v["confluence_total"] >= 2
    assert v["oil_volatility_ovx"] == 35


def test_build_view_bearish():
    v = oil_view.build_view(market(False), {"crude": {"dates": ["2025-12-03"], "changes": [3.0]}}, {"net_long": 200000})
    assert v["confluence_direction"] == "bearish"


def view(direction="bullish", total=4, price=70.0):
    return {"wti_price": price, "confluence_total": total, "confluence_direction": direction, "audit_hit_rate": 0.6}


def test_rules_buy_when_bullish():
    d = brain.rule_decision(view(), {"barrels": 0, "usd": 10000})
    assert d["action"] == "BUY" and d["fraction"] == 1.0


def test_rules_never_sell_when_flat():
    d = brain.rule_decision(view("bearish", -4), {"barrels": 0, "usd": 10000})
    assert d["action"] == "HOLD"


def test_rules_sell_when_long_and_bearish():
    d = brain.rule_decision(view("bearish", -2), {"barrels": 10, "usd": 0})
    assert d["action"] == "SELL" and d["fraction"] == 0.5


def test_no_key_uses_rules(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    d, model, raw = brain.decide(view(), [], {"barrels": 0, "usd": 1000})
    assert model == "rules" and d["action"] == "BUY"


def test_parse_llm_json_strips_thinking_and_clamps():
    d = brain.parse_llm_json('<think>hmm {"x":1}</think> ok {"action":"buy","fraction":3,"confidence":140,"reason":"r"}')
    assert d == {"action": "BUY", "fraction": 1.0, "confidence": 100, "reason": "r"}


def test_parse_llm_json_rejects_bad_action():
    with pytest.raises(ValueError):
        brain.parse_llm_json('{"action":"SHORT"}')


def test_llm_error_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9")
    d, model, raw = brain.decide(view(), [], {"barrels": 0, "usd": 1000})
    assert model.startswith("rules (llm error") and d["action"] == "BUY"


MANDATE = {"maxTradeQuote": 2500 * 10**18, "maxTradeBase": 40 * 10**18, "dailyCapQuote": 5000 * 10**18,
           "dailyCapBase": 80 * 10**18, "maxSlippageBps": 50, "paused": False}


def test_size_buy():
    a, e, m = chain.size_order({"action": "BUY", "fraction": 0.5}, 62.5, {"barrels": 0, "usd": 10000}, MANDATE)
    assert a == 1250 * 10**18
    assert e == 20 * 10**18
    assert m * 10_000 >= e * (10_000 - 50)


def test_size_sell_capped_by_holdings():
    a, e, _ = chain.size_order({"action": "SELL", "fraction": 1.0}, 50.0, {"barrels": 10, "usd": 0}, MANDATE)
    assert a == 10 * 10**18 and e == 500 * 10**18


def test_size_hold():
    assert chain.size_order({"action": "HOLD", "fraction": 0}, 70, {"barrels": 0, "usd": 1}, MANDATE) == (0, 0, 0)


def test_crowd_summary_filters_and_sorts():
    events = [{"id": 1, "title": "Oil", "markets": [
        {"question": "Will WTI close above $80 in November?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.22","0.78"]', "volume": "5000"},
        {"question": "Will crude oil hit $50?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.05","0.95"]', "volume": "90000"},
        {"question": "Will it rain?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.5","0.5"]', "volume": "1"},
        {"question": "Will WTI close above $90?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.01","0.99"]', "closed": True},
    ]}]
    out = crowd.summarise_markets(events)
    assert [o["question"] for o in out] == ["Will crude oil hit $50?", "Will WTI close above $80 in November?"]
    assert out[1]["odds"] == {"Yes": 0.22, "No": 0.78}


def test_hit_rate_percent_normalised():
    assert oil_view._hit_fraction(58.0) == pytest.approx(0.58)
    assert oil_view._hit_fraction(0.4) == 0.4
    assert oil_view._hit_fraction(None) is None


def test_finalise_turns_empty_buy_into_hold():
    d, a = chain.finalise({"action": "BUY", "fraction": 1, "confidence": 70, "reason": "bullish"}, (0, 0, 0))
    assert d["action"] == "HOLD" and d["reason"].startswith("(fully invested") and a == (0, 0, 0)


def test_finalise_keeps_real_orders():
    d, a = chain.finalise({"action": "SELL", "fraction": 1, "confidence": 70, "reason": "x"}, (5, 6, 6))
    assert d["action"] == "SELL" and a == (5, 6, 6)


def test_size_order_never_exceeds_balance_after_float_roundtrip():
    # 20 bbl sold at 62.5 leaves 1250 USD in wei; the float view of it must not oversize the buy
    quote_wei = 20 * 10**18 * 6_250_000_000 // 10**8
    usd = quote_wei / 1e18
    book = {"barrels": 0, "usd": usd, "_barrels_wei": 0, "_usd_wei": quote_wei}
    a, _, _ = chain.size_order({"action": "BUY", "fraction": 0.5}, 62.44, book, MANDATE)
    assert a == quote_wei
    a, _, _ = chain.size_order({"action": "BUY", "fraction": 0.5}, 62.44, {**book, "_usd_wei": quote_wei - 1}, MANDATE)
    assert a == quote_wei - 1


def test_size_skips_dust_trades():
    # $62 of cash left: below a tenth of the $2,500 ticket, so no trade
    assert chain.size_order({"action": "BUY", "fraction": 1.0}, 66.0, {"barrels": 150, "usd": 62.0}, MANDATE) == (0, 0, 0)
    assert chain.size_order({"action": "SELL", "fraction": 1.0}, 66.0, {"barrels": 1.5, "usd": 0}, MANDATE) == (0, 0, 0)
