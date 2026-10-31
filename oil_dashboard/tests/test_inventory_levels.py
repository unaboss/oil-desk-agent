from analysis.inventory_levels import (
    mbbl_to_million_bbl,
    spr_projection,
    weeks_of_supply,
)


class TestWeeksOfSupply:
    def test_computes_weeks(self):
        # 420M bbl stocks / 17M bbl/day / 7 days = 3.5 weeks
        assert weeks_of_supply(420.0, 17.0) == 3.5

    def test_none_when_inputs_missing(self):
        assert weeks_of_supply(None, 17.0) is None
        assert weeks_of_supply(420.0, None) is None

    def test_none_when_non_positive(self):
        assert weeks_of_supply(0.0, 17.0) is None
        assert weeks_of_supply(420.0, 0.0) is None


class TestSprProjection:
    def test_depleting(self):
        levels = [700.0, 710.0, 720.0, 730.0]  # dropping 10 M bbl/wk, newest first
        proj = spr_projection(levels)
        assert proj["mode"] == "depleting"
        assert proj["rate_mbbl_per_wk"] == -10.0
        assert proj["weeks_to_floor"] == 30.0  # (700 - 400) / 10

    def test_refilling(self):
        levels = [650.0, 640.0, 630.0, 620.0]  # +10 M bbl/wk
        proj = spr_projection(levels)
        assert proj["mode"] == "refilling"
        assert proj["rate_mbbl_per_wk"] == 10.0
        assert proj["weeks_to_full"] == 6.4  # (714 - 650) / 10

    def test_flat(self):
        levels = [700.0, 700.0, 700.0, 700.0]
        proj = spr_projection(levels)
        assert proj["mode"] == "flat"

    def test_no_data(self):
        proj = spr_projection([])
        assert proj["mode"] == "no_data"
        proj2 = spr_projection([700.0])
        assert proj2["mode"] == "no_data"


class TestMbblConversion:
    def test_converts_and_drops_nan(self):
        values = [723104.0, 711796.0, None, float("nan")]
        out = mbbl_to_million_bbl(values)
        assert out == [723.104, 711.796]
