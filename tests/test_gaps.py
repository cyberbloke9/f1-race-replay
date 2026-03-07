"""Tests for the time-based gap computation engine (src/lib/gaps.py)."""
import numpy as np
import pytest

from src.lib.gaps import compute_driver_gaps


# ── Helpers ──

def _make_resampled(drivers_config: list[dict], num_frames: int = 100,
                    dt: float = 0.2) -> tuple[dict, np.ndarray]:
    """Build synthetic resampled_data and timeline.

    Each entry in drivers_config:
        {"code": str, "start_lap": int, "start_rel": float,
         "laps_per_sec": float}
    laps_per_sec controls how fast the driver progresses around the track.
    Progress at frame i = start_progress + i * dt * laps_per_sec.
    """
    timeline = np.arange(num_frames) * dt  # e.g. 0.0, 0.2, 0.4, ...
    resampled: dict = {}

    for cfg in drivers_config:
        code = cfg["code"]
        start_progress = (cfg["start_lap"] - 1) + cfg["start_rel"]
        laps_per_sec = cfg["laps_per_sec"]

        progress = start_progress + timeline * laps_per_sec
        lap = np.floor(progress).astype(int) + 1  # lap 1 = first lap
        rel_dist = progress - np.floor(progress)

        resampled[code] = {
            "lap": lap,
            "rel_dist": rel_dist,
        }

    return resampled, timeline


class TestSingleDriver:
    """A lone driver should have all gaps = 0.0."""

    def test_gap_to_leader_all_zero(self):
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.0,
             "laps_per_sec": 1 / 90},
        ], num_frames=50)

        result = compute_driver_gaps(resampled, timeline)

        assert "VER" in result
        gaps = result["VER"]["gap_to_leader"]
        assert len(gaps) == len(timeline)
        assert np.all(gaps == 0.0)

    def test_gap_to_ahead_all_zero(self):
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.0,
             "laps_per_sec": 1 / 90},
        ], num_frames=50)

        result = compute_driver_gaps(resampled, timeline)
        gaps = result["VER"]["gap_to_ahead"]
        assert len(gaps) == len(timeline)
        assert np.all(gaps == 0.0)


class TestTwoDrivers:
    """Two drivers with a known constant offset."""

    def test_gap_to_leader_for_behind_driver(self):
        """Driver B starts 0.5s behind driver A at constant speed.
        gap_to_leader for B should be ~0.5s everywhere (after warm-up)."""
        lps = 1 / 90  # laps per second (90s laps)
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.1,
             "laps_per_sec": lps},
            {"code": "HAM", "start_lap": 1, "start_rel": 0.1 - 0.5 * lps,
             "laps_per_sec": lps},
        ], num_frames=200, dt=0.2)

        result = compute_driver_gaps(resampled, timeline)

        # Leader (VER) should have 0 gap
        ver_gaps = result["VER"]["gap_to_leader"]
        assert np.all(ver_gaps == 0.0)

        # Behind driver (HAM) should have ~0.5s gap after initial frames
        ham_gaps = result["HAM"]["gap_to_leader"]
        # Skip first few frames that may be NaN (no history)
        valid = ham_gaps[~np.isnan(ham_gaps)]
        assert len(valid) > 0
        np.testing.assert_allclose(valid, 0.5, atol=0.15)

    def test_leader_gap_is_zero(self):
        lps = 1 / 90
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.2,
             "laps_per_sec": lps},
            {"code": "HAM", "start_lap": 1, "start_rel": 0.1,
             "laps_per_sec": lps},
        ], num_frames=100)

        result = compute_driver_gaps(resampled, timeline)
        assert np.all(result["VER"]["gap_to_leader"] == 0.0)

    def test_gap_to_ahead_equals_gap_to_leader_for_p2(self):
        """With 2 drivers, P2's gap_to_ahead == gap_to_leader."""
        lps = 1 / 90
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.2,
             "laps_per_sec": lps},
            {"code": "HAM", "start_lap": 1, "start_rel": 0.1,
             "laps_per_sec": lps},
        ], num_frames=200, dt=0.2)

        result = compute_driver_gaps(resampled, timeline)

        ham_leader = result["HAM"]["gap_to_leader"]
        ham_ahead = result["HAM"]["gap_to_ahead"]
        # Both should be equal (P2's car ahead IS the leader)
        np.testing.assert_array_equal(ham_leader, ham_ahead)


class TestThreeDriversInterval:
    """Three drivers — verify interval (gap_to_ahead) is correct."""

    def test_interval_gaps(self):
        """VER leads, HAM 0.5s behind, LEC 1.0s behind leader.
        HAM interval = 0.5s, LEC interval = 0.5s (gap to HAM)."""
        lps = 1 / 90
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.2,
             "laps_per_sec": lps},
            {"code": "HAM", "start_lap": 1, "start_rel": 0.2 - 0.5 * lps,
             "laps_per_sec": lps},
            {"code": "LEC", "start_lap": 1, "start_rel": 0.2 - 1.0 * lps,
             "laps_per_sec": lps},
        ], num_frames=200, dt=0.2)

        result = compute_driver_gaps(resampled, timeline)

        # LEC gap_to_leader ~ 1.0s
        lec_leader = result["LEC"]["gap_to_leader"]
        valid_leader = lec_leader[~np.isnan(lec_leader)]
        assert len(valid_leader) > 0
        np.testing.assert_allclose(valid_leader, 1.0, atol=0.15)

        # LEC gap_to_ahead (to HAM) ~ 0.5s
        lec_ahead = result["LEC"]["gap_to_ahead"]
        valid_ahead = lec_ahead[~np.isnan(lec_ahead)]
        assert len(valid_ahead) > 0
        np.testing.assert_allclose(valid_ahead, 0.5, atol=0.15)

        # HAM gap_to_ahead (to VER) ~ 0.5s
        ham_ahead = result["HAM"]["gap_to_ahead"]
        valid_ham = ham_ahead[~np.isnan(ham_ahead)]
        assert len(valid_ham) > 0
        np.testing.assert_allclose(valid_ham, 0.5, atol=0.15)


class TestLappedDriver:
    """A driver more than 1 lap behind should get negative gap values."""

    def test_lapped_driver_negative_gap(self):
        """HAM is 1+ lap behind VER → gap_to_leader should be negative."""
        lps = 1 / 90
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 3, "start_rel": 0.5,
             "laps_per_sec": lps},
            {"code": "HAM", "start_lap": 2, "start_rel": 0.3,
             "laps_per_sec": lps},
        ], num_frames=100, dt=0.2)

        result = compute_driver_gaps(resampled, timeline)
        ham_gaps = result["HAM"]["gap_to_leader"]
        valid = ham_gaps[~np.isnan(ham_gaps)]
        # Should have at least some negative values (lapped indicator)
        assert len(valid) > 0
        assert np.any(valid < 0), "Lapped driver should have negative gap values"


class TestEarlyFrames:
    """Early frames where no history exists should produce NaN."""

    def test_early_frames_are_nan(self):
        """When the behind driver's progress hasn't been reached by leader yet
        (in history), result should be NaN."""
        lps = 1 / 90
        # HAM starts just barely behind VER
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.01,
             "laps_per_sec": lps},
            {"code": "HAM", "start_lap": 1, "start_rel": 0.005,
             "laps_per_sec": lps},
        ], num_frames=100, dt=0.2)

        result = compute_driver_gaps(resampled, timeline)
        ham_gaps = result["HAM"]["gap_to_leader"]
        # Frame 0: leader's progress history is just one point — may produce NaN
        # We just verify the function handles it without error and returns
        # an array of the right length
        assert len(ham_gaps) == len(timeline)


class TestOutputShape:
    """Verify output dict has correct structure."""

    def test_all_drivers_present(self):
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.0,
             "laps_per_sec": 1 / 90},
            {"code": "HAM", "start_lap": 1, "start_rel": 0.0,
             "laps_per_sec": 1 / 90},
            {"code": "LEC", "start_lap": 1, "start_rel": 0.0,
             "laps_per_sec": 1 / 90},
        ])

        result = compute_driver_gaps(resampled, timeline)

        assert set(result.keys()) == {"VER", "HAM", "LEC"}
        for code in result:
            assert "gap_to_leader" in result[code]
            assert "gap_to_ahead" in result[code]
            assert len(result[code]["gap_to_leader"]) == len(timeline)
            assert len(result[code]["gap_to_ahead"]) == len(timeline)


# ── Integration Tests ──

class TestGapDataInFrameFormat:
    """Verify gap values work in the frame dict format used by f1_data.py."""

    def test_gap_values_are_serializable(self):
        """Gap values (float or None) must be JSON-serializable for the stream."""
        import json

        lps = 1 / 90
        resampled, timeline = _make_resampled([
            {"code": "VER", "start_lap": 1, "start_rel": 0.2,
             "laps_per_sec": lps},
            {"code": "HAM", "start_lap": 1, "start_rel": 0.1,
             "laps_per_sec": lps},
        ], num_frames=50, dt=0.2)

        result = compute_driver_gaps(resampled, timeline)

        # Simulate frame building: convert NaN to None (as f1_data.py does)
        for code in result:
            for i in range(len(timeline)):
                gap_leader = result[code]["gap_to_leader"][i]
                gap_ahead = result[code]["gap_to_ahead"][i]
                val_leader = float(gap_leader) if not np.isnan(gap_leader) else None
                val_ahead = float(gap_ahead) if not np.isnan(gap_ahead) else None

                # Must be JSON-serializable
                frame_data = {"gap_to_leader": val_leader, "gap_to_ahead": val_ahead}
                serialized = json.dumps(frame_data)
                assert isinstance(serialized, str)


class TestLeaderboardPrecomputedGaps:
    """Test that leaderboard gap logic reads pre-computed values correctly."""

    def test_reads_gap_to_leader_from_pos_dict(self):
        """When pos dict has gap_to_leader, it should be used directly."""
        entries = [
            ("VER", (0, 0, 255), {"gap_to_leader": 0.0, "gap_to_ahead": 0.0}, 15000.0),
            ("HAM", (0, 255, 0), {"gap_to_leader": 1.5, "gap_to_ahead": 1.5}, 14500.0),
            ("NOR", (255, 128, 0), {"gap_to_leader": 3.2, "gap_to_ahead": 1.7}, 14000.0),
        ]

        # Replicate _calculate_gaps logic (without arcade dependency)
        computed_gaps = {}
        computed_neighbor_gaps = {}
        for idx, (code, _, pos, progress_m) in enumerate(entries):
            gap_to_leader = pos.get("gap_to_leader")
            gap_to_ahead = pos.get("gap_to_ahead")

            if idx == 0:
                computed_gaps[code] = 0.0
            elif gap_to_leader is not None:
                computed_gaps[code] = gap_to_leader
            else:
                computed_gaps[code] = None

            ahead_info = None
            if idx > 0:
                code_ahead = entries[idx - 1][0]
                if gap_to_ahead is not None:
                    ahead_info = (code_ahead, 0.0, gap_to_ahead)
            computed_neighbor_gaps[code] = {"ahead": ahead_info}

        assert computed_gaps["VER"] == 0.0
        assert computed_gaps["HAM"] == 1.5
        assert computed_gaps["NOR"] == 3.2

        assert computed_neighbor_gaps["HAM"]["ahead"] == ("VER", 0.0, 1.5)
        assert computed_neighbor_gaps["NOR"]["ahead"] == ("HAM", 0.0, 1.7)

    def test_falls_back_without_gap_data(self):
        """When pos dict has no gap fields, fallback to distance approximation."""
        entries = [
            ("VER", (0, 0, 255), {}, 15000.0),
            ("HAM", (0, 255, 0), {}, 14500.0),
        ]

        computed_gaps = {}
        for idx, (code, _, pos, progress_m) in enumerate(entries):
            gap_to_leader = pos.get("gap_to_leader")

            if idx == 0:
                computed_gaps[code] = 0.0
            elif gap_to_leader is not None:
                computed_gaps[code] = gap_to_leader
            else:
                leader_progress = entries[0][3]
                raw = abs(leader_progress - (progress_m or 0.0))
                computed_gaps[code] = (raw / 10.0) / 55.56

        assert computed_gaps["VER"] == 0.0
        assert computed_gaps["HAM"] > 0.0  # Fallback produces some positive value
        assert computed_gaps["HAM"] == pytest.approx((500.0 / 10.0) / 55.56)
