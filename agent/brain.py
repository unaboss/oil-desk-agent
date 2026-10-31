"""Decision: an LLM weighs confluence, audit hit rate and crowd odds; rules as fallback."""
import json
import os
import re

import requests

ACTIONS = ("HOLD", "BUY", "SELL")


def rule_decision(view, portfolio):
    """Deterministic fallback straight from the dashboard's confluence thresholds."""
    total, direction = view["confluence_total"], view["confluence_direction"]
    hit = view.get("audit_hit_rate")
    hit_txt = f", audit hit rate {hit:.0%}" if hit is not None else ""
    if direction == "bullish":
        return {"action": "BUY", "fraction": min(1.0, 0.25 * total), "confidence": 50 + 8 * total,
                "reason": f"Confluence {total:+d} bullish{hit_txt}."}
    if direction == "bearish" and portfolio["barrels"] > 0:
        return {"action": "SELL", "fraction": min(1.0, 0.25 * abs(total)), "confidence": 50 + 8 * abs(total),
                "reason": f"Confluence {total:+d} bearish{hit_txt}; cutting long exposure."}
    return {"action": "HOLD", "fraction": 0.0, "confidence": 55,
            "reason": f"Confluence {total:+d} ({direction}){hit_txt}; no edge, staying put."}


PROMPT = """You are Oil Desk, a disciplined WTI crude oil trading agent. You trade a long/flat book
(you can BUY barrels with USD, or SELL barrels you hold; no shorting). An on-chain mandate caps your
size; you choose what fraction of the per-trade cap to use.

Inputs:
1. Confluence engine (6 signals, each -1/0/+1: volume, COT positioning, EIA inventories, crack spread,
   dollar, Brent-WTI curve). total >= +2 is bullish, <= -2 bearish.
2. The engine's own historical audit hit rate (how often its strong calls were right over 3 days).
3. Polymarket crowd odds on oil-price questions (treat as sentiment, not truth).
4. Your current book and mandate.

Rules: if signals conflict or the hit rate is weak, prefer HOLD or a small size. Never invent data.

View: {view}
Crowd: {crowd}
Book: {portfolio}

Reply with JSON only:
{{"action":"BUY"|"SELL"|"HOLD","fraction":0..1,"confidence":0..100,
 "reason":"<= 260 chars, cite the numbers you used"}}"""


def _pick_model(base, key):
    want = os.getenv("LLM_MODEL")
    if want:
        return want
    r = requests.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=20)
    r.raise_for_status()
    ids = [m["id"] for m in r.json().get("data", [])]
    for pref in ("deepseek-v4-flash", "deepseek-v4", "deepseek-v3", "deepseek"):
        for i in ids:
            if pref in i.lower() and "vl" not in i.lower():
                return i
    raise RuntimeError("no DeepSeek model listed; set LLM_MODEL")


def parse_llm_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("no JSON in model reply")
    d = json.loads(m.group(0))
    action = str(d.get("action", "")).upper()
    if action not in ACTIONS:
        raise ValueError(f"bad action {action!r}")
    return {
        "action": action,
        "fraction": max(0.0, min(1.0, float(d.get("fraction") or 0))),
        "confidence": int(max(0, min(100, round(float(d.get("confidence") or 0))))),
        "reason": str(d.get("reason", ""))[:260],
    }


def decide(view, crowd, portfolio):
    """Returns (decision, model_label, raw_text)."""
    key = os.getenv("LLM_API_KEY")
    if not key:
        return rule_decision(view, portfolio), "rules", ""
    base = os.getenv("LLM_BASE_URL", "https://api.tokenfactory.nebius.com/v1").rstrip("/")
    try:
        model = _pick_model(base, key)
        body = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": 600,
            "messages": [{"role": "user", "content": PROMPT.format(
                view=json.dumps(view), crowd=json.dumps(crowd), portfolio=json.dumps({k: round(v, 4) for k, v in portfolio.items() if not k.startswith("_")}))}],
        }
        r = requests.post(f"{base}/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {key}"}, timeout=90)
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"] or ""
        d = parse_llm_json(raw)
        if d["action"] == "SELL" and portfolio["barrels"] <= 0:
            d = {**d, "action": "HOLD", "fraction": 0.0, "reason": ("(flat, cannot sell) " + d["reason"])[:260]}
        return d, model.split("/")[-1], raw
    except Exception as e:  # never let a model outage stop the on-chain log
        d = rule_decision(view, portfolio)
        return d, f"rules (llm error: {str(e)[:50]})", ""
