"""Curve/spread driver analysis — which benchmark is moving the divergence.

The Brent-WTI spread can widen because Brent is rising/falling (global forces:
Iran, OPEC, shipping) OR because WTI is (US forces: Cushing logistics, exports,
shale). This computes each benchmark's % move over a window and attributes the
spread change to whichever moved more. Pure functions — no I/O.
"""


def compute_driver(wti, brent, window=5):
    """Return who drove the most recent spread change.

    wti/brent: {"dates": [...], "close": [...]} newest-first.
    window: number of trading days to measure the move over.

    Returns {"driver": "brent"|"wti"|"tie"|"insufficient",
             "wti_move_pct", "brent_move_pct", "spread_change",
             "wti_old", "wti_new", "brent_old", "brent_new"}
    """
    def _last_n(data, n):
        closes = [c for c in data.get("close", []) if c is not None]
        return closes[-n:] if len(closes) >= n else closes

    wti_window = _last_n(wti, window)
    brent_window = _last_n(brent, window)

    if len(wti_window) < 2 or len(brent_window) < 2:
        return {
            "driver": "insufficient", "wti_move_pct": None, "brent_move_pct": None,
            "spread_change": None, "wti_old": None, "wti_new": None,
            "brent_old": None, "brent_new": None,
        }

    wti_old, wti_new = wti_window[0], wti_window[-1]
    brent_old, brent_new = brent_window[0], brent_window[-1]
    if wti_old in (0, None) or brent_old in (0, None):
        return {
            "driver": "insufficient", "wti_move_pct": None, "brent_move_pct": None,
            "spread_change": None, "wti_old": None, "wti_new": None,
            "brent_old": None, "brent_new": None,
        }

    wti_move_pct = (wti_new - wti_old) / wti_old * 100.0
    brent_move_pct = (brent_new - brent_old) / brent_old * 100.0
    spread_change = (brent_new - wti_new) - (brent_old - wti_old)

    if abs(wti_move_pct) >= abs(brent_move_pct):
        driver = "wti"
    elif abs(brent_move_pct) > abs(wti_move_pct):
        driver = "brent"
    else:
        driver = "tie"

    return {
        "driver": driver,
        "wti_move_pct": round(wti_move_pct, 2),
        "brent_move_pct": round(brent_move_pct, 2),
        "spread_change": round(spread_change, 2),
        "wti_old": round(wti_old, 2),
        "wti_new": round(wti_new, 2),
        "brent_old": round(brent_old, 2),
        "brent_new": round(brent_new, 2),
    }
