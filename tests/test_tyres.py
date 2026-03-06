import pytest
from src.lib.tyres import get_tyre_compound_int, get_tyre_compound_str


class TestGetTyreCompoundInt:
    @pytest.mark.parametrize("compound,expected", [
        ("SOFT", 0),
        ("MEDIUM", 1),
        ("HARD", 2),
        ("INTERMEDIATE", 3),
        ("WET", 4),
    ])
    def test_all_compounds(self, compound, expected):
        assert get_tyre_compound_int(compound) == expected

    @pytest.mark.parametrize("compound", ["soft", "Soft", "sOfT"])
    def test_case_insensitive(self, compound):
        assert get_tyre_compound_int(compound) == 0

    def test_unknown_compound(self):
        assert get_tyre_compound_int("UNKNOWN_COMPOUND") == -1


class TestGetTyreCompoundStr:
    @pytest.mark.parametrize("int_val,expected", [
        (0, "SOFT"),
        (1, "MEDIUM"),
        (2, "HARD"),
        (3, "INTERMEDIATE"),
        (4, "WET"),
    ])
    def test_all_ints(self, int_val, expected):
        assert get_tyre_compound_str(int_val) == expected

    @pytest.mark.parametrize("int_val", [-1, 99, 5])
    def test_unknown_int(self, int_val):
        assert get_tyre_compound_str(int_val) == "UNKNOWN"
