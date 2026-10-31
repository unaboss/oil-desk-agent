from analysis.eia_analysis import compute_eia_analysis
from data.fetcher_eia import get_weekly_changes


def test_weekly_changes_newest_first_with_real_latest():
    """Latest week must be at index 0 with a real value (not NaN)."""
    data = {"dates": ["2026-08-07", "2026-07-31", "2026-07-24"],
            "values": [424410.0, 406987.0, 404508.0]}
    result = get_weekly_changes(data)
    assert result["changes"][0] == 17423.0   # 424410 - 406987
    assert result["changes"][1] == 2479.0    # 406987 - 404508
    import pandas as pd
    assert pd.isna(result["changes"][2])     # oldest has no prior week


def test_weekly_changes_none_input():
    assert get_weekly_changes(None) is None


def _eia_mock(crude_ch, gasoline_ch, distillate_ch, spr_ch):
    def _wrap(ch):
        n = len(ch)
        return {"dates": [str(20260000 + i) for i in range(n)], "values": [0]*n, "changes": list(ch)}
    return {
        "crude": _wrap(crude_ch),
        "gasoline": _wrap(gasoline_ch),
        "distillate": _wrap(distillate_ch),
        "spr": _wrap(spr_ch),
    }


def test_crude_accelerating_draw_is_bullish():
    data = _eia_mock(
        crude_ch=[-4.5, -1.0, -1.2, -0.8, -1.5],
        gasoline_ch=[0.5, 0.3, 0.4, 0.2, 0.5],
        distillate_ch=[0.1, 0.0, -0.2, -0.1, 0.1],
        spr_ch=[0, 0, 0, 0, 0],
    )
    result = compute_eia_analysis(data)
    assert result["by_product"]["crude"]["signal"] == 1
    assert result["by_product"]["crude"]["trend_label"] == "Accelerating draw"


def test_gasoline_accelerating_build_is_bearish():
    data = _eia_mock(
        crude_ch=[0.5, 0.3, 0.4, 0.2, 0.5],
        gasoline_ch=[2.1, 0.3, 0.4, 0.2, 0.5],
        distillate_ch=[0.1, 0.0, -0.2, -0.1, 0.1],
        spr_ch=[0, 0, 0, 0, 0],
    )
    result = compute_eia_analysis(data)
    assert result["by_product"]["gasoline"]["signal"] == -1
    assert "build" in result["by_product"]["gasoline"]["trend_label"].lower()


def test_spr_release_is_bearish():
    data = _eia_mock(
        crude_ch=[0.5]*5,
        gasoline_ch=[0.5]*5,
        distillate_ch=[0.1]*5,
        spr_ch=[-3.0, -0.5, -0.4, -0.6, -0.5],
    )
    result = compute_eia_analysis(data)
    assert result["by_product"]["spr"]["signal"] == -1


def test_spr_refill_is_bullish():
    data = _eia_mock(
        crude_ch=[0.5]*5,
        gasoline_ch=[0.5]*5,
        distillate_ch=[0.1]*5,
        spr_ch=[3.0, 0.5, 0.4, 0.6, 0.5],
    )
    result = compute_eia_analysis(data)
    assert result["by_product"]["spr"]["signal"] == 1


def test_all_flat_composite_zero():
    data = _eia_mock(
        crude_ch=[0.3]*5,
        gasoline_ch=[0.5]*5,
        distillate_ch=[0.1]*5,
        spr_ch=[0.1]*5,
    )
    result = compute_eia_analysis(data)
    assert result["composite_score"] == 0


def test_composite_score_sum():
    data = _eia_mock(
        crude_ch=[-4.5, -1.0, -1.2, -0.8, -1.5],
        gasoline_ch=[2.1, 0.3, 0.4, 0.2, 0.5],
        distillate_ch=[-2.0, -0.1, -0.2, -0.1, 0.1],
        spr_ch=[-3.0, -0.5, -0.4, -0.6, -0.5],
    )
    result = compute_eia_analysis(data)
    assert result["composite_score"] == result["by_product"]["crude"]["signal"] + result["by_product"]["gasoline"]["signal"] + result["by_product"]["distillate"]["signal"] + result["by_product"]["spr"]["signal"]


def test_bullish_and_bearish_lists():
    data = _eia_mock(
        crude_ch=[-4.5, -1.0, -1.2, -0.8, -1.5],
        gasoline_ch=[2.1, 0.3, 0.4, 0.2, 0.5],
        distillate_ch=[0.1]*5,
        spr_ch=[0]*5,
    )
    result = compute_eia_analysis(data)
    assert "crude" in result["bullish_products"]
    assert "gasoline" in result["bearish_products"]


def test_strongest_reading():
    data = _eia_mock(
        crude_ch=[-4.5, -1.0, -1.2, -0.8, -1.5],
        gasoline_ch=[0.5]*5,
        distillate_ch=[0.1]*5,
        spr_ch=[0]*5,
    )
    result = compute_eia_analysis(data)
    assert result["strongest_reading"] == "crude"


def test_empty_data_returns_defaults():
    result = compute_eia_analysis(None)
    assert result["composite_score"] == 0
    assert result["bullish_products"] == []
