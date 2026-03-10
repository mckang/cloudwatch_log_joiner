from __future__ import annotations

import pytest

from logjoiner.time_utils import parse_kst_datetime, to_utc_epoch_ms


def test_parse_kst_datetime_success() -> None:
    dt = parse_kst_datetime("2026-03-10 12:34:56")
    assert dt.tzinfo is not None
    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 10


def test_parse_kst_datetime_invalid_format() -> None:
    with pytest.raises(ValueError):
        parse_kst_datetime("2026/03/10 12:34:56")


def test_to_utc_epoch_ms() -> None:
    dt = parse_kst_datetime("1970-01-01 09:00:01")
    assert to_utc_epoch_ms(dt) == 1000
