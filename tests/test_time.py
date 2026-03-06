import pytest
from src.lib.time import parse_time_string, format_time


class TestParseTimeString:
    @pytest.mark.parametrize("input_str,expected", [
        ("01:26.123", 86.123),
        ("01:26", 86.0),
        ("00:01:26:123000", 86.123),
        ("00:01:26.123000", 86.123),
        ("0 days 00:01:27.060000", 87.06),
        ("00:00.000", 0.0),
        ("01:30:00.000000", 5400.0),
        ("00:00:01.500000", 1.5),
    ])
    def test_valid_formats(self, input_str, expected):
        result = parse_time_string(input_str)
        assert result == pytest.approx(expected, abs=0.001)

    @pytest.mark.parametrize("input_str", [
        "",
        None,
    ])
    def test_invalid_returns_none(self, input_str):
        assert parse_time_string(input_str) is None

    def test_timedelta_format_with_days(self):
        result = parse_time_string("0 days 00:02:00.000000")
        assert result == pytest.approx(120.0, abs=0.001)


class TestFormatTime:
    @pytest.mark.parametrize("seconds,expected", [
        (86.123, "01:26.123"),
        (0.0, "00:00.000"),
        (5400.0, "90:00.000"),
    ])
    def test_valid_values(self, seconds, expected):
        assert format_time(seconds) == expected

    def test_none_returns_na(self):
        assert format_time(None) == "N/A"

    def test_negative_returns_na(self):
        assert format_time(-1.0) == "N/A"
