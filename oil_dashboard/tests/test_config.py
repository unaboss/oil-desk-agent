from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from config import next_eia_release, next_cot_release


def _freeze(utc_str):
    return datetime.fromisoformat(utc_str).replace(tzinfo=timezone.utc)


@patch("config.datetime")
def test_next_eia_tuesday(mock_dt):
    mock_dt.now.return_value = _freeze("2025-12-02T12:00:00+00:00")  # Tuesday
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    result = next_eia_release()
    assert result.weekday() == 2  # Wednesday
    assert result.day == 3


@patch("config.datetime")
def test_next_eia_wednesday_after_release(mock_dt):
    mock_dt.now.return_value = _freeze("2025-12-03T16:00:00+00:00")  # Wed after 15:30
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    result = next_eia_release()
    assert result.weekday() == 2  # Next Wednesday
    assert result.day == 10


@patch("config.datetime")
def test_next_cot_thursday(mock_dt):
    mock_dt.now.return_value = _freeze("2025-12-04T12:00:00+00:00")  # Thursday
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    result = next_cot_release()
    assert result.weekday() == 4  # Next Friday (tomorrow)
    assert result.day == 5


@patch("config.datetime")
def test_next_cot_friday_after_release(mock_dt):
    mock_dt.now.return_value = _freeze("2025-12-05T21:00:00+00:00")  # Fri after 20:00
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    result = next_cot_release()
    assert result.weekday() == 4  # Next Friday
    assert result.day == 12
