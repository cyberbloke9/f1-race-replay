"""Tests for the lap time evolution accumulation logic.

Tests the LapTimeAccumulator pure-data class without any Qt/Matplotlib
dependency (same pattern as TestLeaderboardPrecomputedGaps in test_gaps.py).
"""

import pytest

from src.insights.lap_time_evolution_window import LapTimeAccumulator, CompletedLap


# ── Helpers ──

def _make_frame(
    drivers: dict[str, dict],
    session_t: float,
    leader_lap: int = 1,
    track_status: str = "GREEN",
) -> dict:
    """Build a minimal telemetry frame dict."""
    return {
        "frame_index": 0,
        "frame": {
            "t": session_t,
            "lap": leader_lap,
            "drivers": drivers,
        },
        "track_status": track_status,
    }


class TestLapTimeAccumulation:
    """Test basic lap time computation from sequential frames."""

    def test_basic_lap_time_computation(self):
        """Feed 3 frames with increasing laps -> should record lap 2 and 3."""
        acc = LapTimeAccumulator()

        # Lap 1 at t=0
        acc.process_frame(_make_frame(
            {"VER": {"lap": 1, "tyre": 0}}, session_t=0.0
        ))
        # Lap 2 at t=90 (lap 1 completed in 90s — but lap 1 is skipped)
        acc.process_frame(_make_frame(
            {"VER": {"lap": 2, "tyre": 0}}, session_t=90.0
        ))
        # Lap 3 at t=180 (lap 2 completed in 90s)
        acc.process_frame(_make_frame(
            {"VER": {"lap": 3, "tyre": 0}}, session_t=180.0
        ))

        laps = acc.completed_laps["VER"]
        assert len(laps) == 1  # Only lap 2 recorded (lap 1 skipped)
        assert laps[0].lap_num == 2
        assert laps[0].lap_time_s == pytest.approx(90.0)
        assert laps[0].compound_int == 0

    def test_lap_1_is_skipped(self):
        """Lap 1 (formation/out lap) should not be recorded."""
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 1, "tyre": 0}}, session_t=0.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 2, "tyre": 0}}, session_t=120.0
        ))

        laps = acc.completed_laps.get("VER", [])
        # Lap 1 transition happened but lap_num=1 < 2 so not recorded
        assert len(laps) == 0

    def test_multiple_laps_accumulated(self):
        """Multiple lap transitions produce the right number of records."""
        acc = LapTimeAccumulator()

        times = [0.0, 95.0, 185.0, 275.0, 365.0]  # 5 frames, laps 1-5
        for i, t in enumerate(times):
            acc.process_frame(_make_frame(
                {"VER": {"lap": i + 1, "tyre": 0}}, session_t=t
            ))

        laps = acc.completed_laps["VER"]
        # Laps 2, 3, 4 recorded (lap 1 skipped, lap 5 not completed yet)
        assert len(laps) == 3
        assert [l.lap_num for l in laps] == [2, 3, 4]

    def test_outlier_laps_filtered(self):
        """Laps > 150s (pit laps, red flags) should be filtered."""
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 1, "tyre": 0}}, session_t=0.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 2, "tyre": 0}}, session_t=90.0
        ))
        # Lap 2 takes 200s (outlier)
        acc.process_frame(_make_frame(
            {"VER": {"lap": 3, "tyre": 0}}, session_t=290.0
        ))
        # Lap 3 takes 85s (normal)
        acc.process_frame(_make_frame(
            {"VER": {"lap": 4, "tyre": 0}}, session_t=375.0
        ))

        laps = acc.completed_laps["VER"]
        lap_nums = [l.lap_num for l in laps]
        # Lap 2 (200s) should be filtered out
        assert 2 not in lap_nums
        # Lap 3 (85s) should be kept
        assert 3 in lap_nums


class TestCompoundTracking:
    """Test tyre compound detection and pit stop marking."""

    def test_compound_change_marks_pit_stop(self):
        """Changing compound between laps marks the new-compound lap as pit stop.

        When a driver pits at the end of lap 2 and starts lap 3 on new tyres,
        lap 3 is marked as pit stop (the first lap on the new compound).
        """
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 1, "tyre": 0}}, session_t=0.0  # SOFT
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 2, "tyre": 0}}, session_t=90.0  # SOFT
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 3, "tyre": 1}}, session_t=180.0  # MEDIUM (pit at end of lap 2)
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 4, "tyre": 1}}, session_t=270.0  # MEDIUM
        ))

        laps = acc.completed_laps["VER"]
        assert len(laps) == 2  # laps 2 and 3

        lap2 = next(l for l in laps if l.lap_num == 2)
        lap3 = next(l for l in laps if l.lap_num == 3)

        # Lap 2 was driven on SOFT — no pit (compound hadn't changed yet)
        assert lap2.compound_int == 0
        assert lap2.is_pit_stop is False

        # Lap 3 is the first lap on MEDIUM — marked as pit stop
        assert lap3.compound_int == 1
        assert lap3.is_pit_stop is True

    def test_same_compound_no_pit_stop(self):
        """Same compound across laps should not be a pit stop."""
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 1, "tyre": 1}}, session_t=0.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 2, "tyre": 1}}, session_t=90.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 3, "tyre": 1}}, session_t=180.0
        ))

        laps = acc.completed_laps["VER"]
        assert len(laps) == 1
        assert laps[0].is_pit_stop is False

    def test_compound_stored_on_completed_lap(self):
        """Compound should reflect what the driver ran during the completed lap."""
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 1, "tyre": 2}}, session_t=0.0  # HARD
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 2, "tyre": 2}}, session_t=90.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 3, "tyre": 2}}, session_t=180.0
        ))

        laps = acc.completed_laps["VER"]
        assert laps[0].compound_int == 2  # HARD

    def test_get_pit_stop_laps(self):
        """get_pit_stop_laps should return correct lap numbers.

        Pit stop is marked on the first lap driven on new tyres:
        - Lap 3 starts on MEDIUM (pit at end of lap 2) -> lap 3 is pit
        - Lap 5 starts on HARD (pit at end of lap 4) -> lap 5 is pit
        """
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame({"VER": {"lap": 1, "tyre": 0}}, 0.0))
        acc.process_frame(_make_frame({"VER": {"lap": 2, "tyre": 0}}, 90.0))
        acc.process_frame(_make_frame({"VER": {"lap": 3, "tyre": 1}}, 180.0))  # pit -> lap 3 on MEDIUM
        acc.process_frame(_make_frame({"VER": {"lap": 4, "tyre": 1}}, 270.0))
        acc.process_frame(_make_frame({"VER": {"lap": 5, "tyre": 2}}, 360.0))  # pit -> lap 5 on HARD

        pit_laps = acc.get_pit_stop_laps("VER")
        # Lap 3 is completed (recorded), should be pit
        assert 3 in pit_laps
        # Lap 5 is not completed yet (no transition to lap 6)
        assert 5 not in pit_laps

        # Complete lap 5 -> now it should appear
        acc.process_frame(_make_frame({"VER": {"lap": 6, "tyre": 2}}, 450.0))
        pit_laps = acc.get_pit_stop_laps("VER")
        assert 5 in pit_laps


class TestSafetyCarDetection:
    """Test SC and VSC period detection from track status."""

    def test_sc_period_detected(self):
        """track_status '4' should create an SC period."""
        acc = LapTimeAccumulator()

        # Green running
        acc.process_frame(_make_frame(
            {"VER": {"lap": 5, "tyre": 0}}, session_t=400.0,
            leader_lap=5, track_status="GREEN"
        ))
        # SC deployed at lap 6
        acc.process_frame(_make_frame(
            {"VER": {"lap": 6, "tyre": 0}}, session_t=490.0,
            leader_lap=6, track_status="4"
        ))
        # SC ends at lap 8
        acc.process_frame(_make_frame(
            {"VER": {"lap": 8, "tyre": 0}}, session_t=670.0,
            leader_lap=8, track_status="GREEN"
        ))

        assert len(acc.sc_periods) == 1
        sc = acc.sc_periods[0]
        assert sc.start_lap == 6
        assert sc.end_lap == 8
        assert sc.is_vsc is False

    def test_vsc_period_detected(self):
        """track_status '6' or '7' should create a VSC period."""
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 3, "tyre": 0}}, session_t=200.0,
            leader_lap=3, track_status="GREEN"
        ))
        # VSC deployed
        acc.process_frame(_make_frame(
            {"VER": {"lap": 4, "tyre": 0}}, session_t=290.0,
            leader_lap=4, track_status="6"
        ))
        # VSC ends
        acc.process_frame(_make_frame(
            {"VER": {"lap": 5, "tyre": 0}}, session_t=380.0,
            leader_lap=5, track_status="GREEN"
        ))

        assert len(acc.sc_periods) == 1
        vsc = acc.sc_periods[0]
        assert vsc.start_lap == 4
        assert vsc.end_lap == 5
        assert vsc.is_vsc is True

    def test_vsc_status_7(self):
        """track_status '7' should also be detected as VSC."""
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 10, "tyre": 0}}, session_t=800.0,
            leader_lap=10, track_status="GREEN"
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 11, "tyre": 0}}, session_t=890.0,
            leader_lap=11, track_status="7"
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 12, "tyre": 0}}, session_t=980.0,
            leader_lap=12, track_status="GREEN"
        ))

        assert len(acc.sc_periods) == 1
        assert acc.sc_periods[0].is_vsc is True

    def test_multiple_sc_periods(self):
        """Multiple SC/VSC periods should all be tracked."""
        acc = LapTimeAccumulator()

        # SC period 1
        acc.process_frame(_make_frame({"VER": {"lap": 2, "tyre": 0}}, 90.0, 2, "GREEN"))
        acc.process_frame(_make_frame({"VER": {"lap": 3, "tyre": 0}}, 180.0, 3, "4"))
        acc.process_frame(_make_frame({"VER": {"lap": 5, "tyre": 0}}, 360.0, 5, "GREEN"))

        # VSC period 2
        acc.process_frame(_make_frame({"VER": {"lap": 10, "tyre": 0}}, 810.0, 10, "6"))
        acc.process_frame(_make_frame({"VER": {"lap": 11, "tyre": 0}}, 900.0, 11, "GREEN"))

        assert len(acc.sc_periods) == 2
        assert acc.sc_periods[0].is_vsc is False
        assert acc.sc_periods[1].is_vsc is True


class TestMultiDriverAccumulation:
    """Test that multiple drivers accumulate independently."""

    def test_two_drivers_independent(self):
        """Two drivers should have separate lap time records."""
        acc = LapTimeAccumulator()

        # Frame 1: both on lap 1
        acc.process_frame(_make_frame(
            {
                "VER": {"lap": 1, "tyre": 0},
                "HAM": {"lap": 1, "tyre": 1},
            },
            session_t=0.0,
        ))

        # Frame 2: VER on lap 2, HAM still lap 1
        acc.process_frame(_make_frame(
            {
                "VER": {"lap": 2, "tyre": 0},
                "HAM": {"lap": 1, "tyre": 1},
            },
            session_t=88.0,
        ))

        # Frame 3: both on lap 2
        acc.process_frame(_make_frame(
            {
                "VER": {"lap": 2, "tyre": 0},
                "HAM": {"lap": 2, "tyre": 1},
            },
            session_t=92.0,
        ))

        # Frame 4: both on lap 3
        acc.process_frame(_make_frame(
            {
                "VER": {"lap": 3, "tyre": 0},
                "HAM": {"lap": 3, "tyre": 1},
            },
            session_t=180.0,
        ))

        ver_laps = acc.completed_laps["VER"]
        ham_laps = acc.completed_laps["HAM"]

        # VER: lap 2 completed (88->180 = 92s)
        assert len(ver_laps) == 1
        assert ver_laps[0].lap_num == 2
        assert ver_laps[0].lap_time_s == pytest.approx(92.0)  # 180 - 88
        assert ver_laps[0].compound_int == 0  # SOFT

        # HAM: lap 2 completed (92->180 = 88s)
        assert len(ham_laps) == 1
        assert ham_laps[0].lap_num == 2
        assert ham_laps[0].lap_time_s == pytest.approx(88.0)  # 180 - 92
        assert ham_laps[0].compound_int == 1  # MEDIUM

    def test_different_compounds_per_driver(self):
        """Each driver's compound should be tracked independently."""
        acc = LapTimeAccumulator()

        acc.process_frame(_make_frame(
            {"VER": {"lap": 1, "tyre": 0}, "HAM": {"lap": 1, "tyre": 2}}, 0.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 2, "tyre": 0}, "HAM": {"lap": 2, "tyre": 2}}, 90.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 3, "tyre": 0}, "HAM": {"lap": 3, "tyre": 2}}, 180.0
        ))

        ver_laps = acc.completed_laps["VER"]
        ham_laps = acc.completed_laps["HAM"]

        assert ver_laps[0].compound_int == 0  # SOFT
        assert ham_laps[0].compound_int == 2  # HARD

    def test_empty_frame_no_crash(self):
        """Empty or missing frame data should not crash."""
        acc = LapTimeAccumulator()

        acc.process_frame({})
        acc.process_frame({"frame": None})
        acc.process_frame({"frame": {}})
        acc.process_frame({"frame": {"drivers": {}}})

        assert len(acc.completed_laps) == 0

    def test_driver_appears_mid_race(self):
        """A driver joining mid-race should be handled gracefully."""
        acc = LapTimeAccumulator()

        # Only VER at first
        acc.process_frame(_make_frame({"VER": {"lap": 5, "tyre": 0}}, 400.0))
        acc.process_frame(_make_frame({"VER": {"lap": 6, "tyre": 0}}, 490.0))

        # HAM appears
        acc.process_frame(_make_frame(
            {"VER": {"lap": 7, "tyre": 0}, "HAM": {"lap": 5, "tyre": 1}}, 580.0
        ))
        acc.process_frame(_make_frame(
            {"VER": {"lap": 8, "tyre": 0}, "HAM": {"lap": 6, "tyre": 1}}, 670.0
        ))

        assert "VER" in acc.completed_laps
        assert "HAM" in acc.completed_laps
        # HAM should have lap 5 recorded (670 - 580 = 90s)
        ham_laps = acc.completed_laps["HAM"]
        assert len(ham_laps) == 1
        assert ham_laps[0].lap_num == 5
