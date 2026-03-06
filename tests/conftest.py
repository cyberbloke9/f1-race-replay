import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

from src.lib.settings import SettingsManager


# ── Fixture 1: Reset SettingsManager singleton between tests ──

@pytest.fixture(autouse=True)
def reset_settings_singleton():
    """Reset the SettingsManager singleton before and after each test."""
    SettingsManager._instance = None
    yield
    SettingsManager._instance = None


# ── Fixture 2: Mock telemetry DataFrame factory ──

@pytest.fixture
def mock_telemetry_df():
    """Factory that creates a small DataFrame mimicking FastF1 telemetry."""
    def _make(num_rows=10, start_time_s=60.0, lap_distance=5000.0):
        time_values = [pd.Timedelta(seconds=start_time_s + i * 0.24) for i in range(num_rows)]
        distances = np.linspace(0, lap_distance, num_rows)
        return pd.DataFrame({
            "SessionTime": pd.to_timedelta(time_values),
            "X": np.linspace(-500, 500, num_rows),
            "Y": np.linspace(-300, 300, num_rows),
            "Distance": distances,
            "RelativeDistance": distances / lap_distance,
            "Speed": np.linspace(200, 340, num_rows),
            "nGear": np.random.choice([3, 4, 5, 6, 7, 8], size=num_rows),
            "DRS": np.random.choice([0, 1, 10, 12, 14], size=num_rows),
            "Throttle": np.linspace(50, 100, num_rows),
            "Brake": np.random.choice([0.0, 0.0, 0.0, 1.0], size=num_rows),
        })
    return _make


# ── Fixture 3: Mock lap factory ──

@pytest.fixture
def mock_lap(mock_telemetry_df):
    """Factory that creates a MagicMock mimicking a FastF1 Lap object."""
    def _make(lap_number=1, compound="SOFT", tyre_life=1, telemetry_df=None,
              start_time_s=None):
        if start_time_s is None:
            start_time_s = 60.0 + (lap_number - 1) * 90.0
        if telemetry_df is None:
            telemetry_df = mock_telemetry_df(start_time_s=start_time_s)

        lap = MagicMock()
        lap.LapNumber = lap_number
        lap.Compound = compound
        lap.TyreLife = tyre_life
        lap.LapTime = pd.Timedelta(seconds=90.0)
        lap.get_telemetry.return_value = telemetry_df
        return lap
    return _make


# ── Fixture 4: Mock laps collection ──

@pytest.fixture
def mock_laps(mock_lap):
    """Creates a MagicMock mimicking FastF1 Laps (extended DataFrame) with 2 drivers."""
    # Build laps for driver '1' (SOFT, 3 laps) and driver '44' (MEDIUM, 3 laps)
    driver_1_laps = [
        mock_lap(lap_number=i, compound="SOFT", tyre_life=i, start_time_s=60.0 + (i - 1) * 90.0)
        for i in range(1, 4)
    ]
    driver_44_laps = [
        mock_lap(lap_number=i, compound="MEDIUM", tyre_life=i, start_time_s=60.0 + (i - 1) * 90.0)
        for i in range(1, 4)
    ]

    all_laps = {"1": driver_1_laps, "44": driver_44_laps}

    def make_driver_laps(driver_no):
        """Return a mock Laps object filtered for a specific driver."""
        laps = all_laps.get(str(driver_no), [])
        filtered = MagicMock()
        filtered.empty = len(laps) == 0

        if laps:
            lap_numbers = [lap.LapNumber for lap in laps]
            max_mock = MagicMock()
            max_mock.max.return_value = max(lap_numbers)
            filtered.LapNumber = max_mock
        else:
            filtered.LapNumber = MagicMock()
            filtered.LapNumber.max.return_value = 0

        def iterlaps():
            for idx, lap in enumerate(laps):
                yield idx, lap

        filtered.iterlaps = iterlaps
        return filtered

    laps_mock = MagicMock()
    laps_mock.empty = False
    laps_mock.pick_drivers = make_driver_laps

    # Top-level LapNumber.max() across all drivers
    laps_mock.LapNumber = MagicMock()
    laps_mock.LapNumber.max.return_value = 3

    return laps_mock


# ── Fixture 5: Full mock FastF1 session ──

@pytest.fixture
def mock_session(mock_laps):
    """Creates a full mock FastF1 Session object."""
    session = MagicMock()
    session.laps = mock_laps
    session.total_laps = 3

    # Weather data
    session.weather_data = pd.DataFrame({
        "TrackTemp": [45.0, 46.0, 47.0],
        "AirTemp": [28.0, 28.5, 29.0],
        "Humidity": [42.0, 43.0, 44.0],
        "WindSpeed": [3.2, 3.5, 3.8],
        "Rainfall": [0.0, 0.0, 0.0],
    })

    # Results
    session.results = pd.DataFrame({
        "DriverNumber": ["1", "44"],
        "Abbreviation": ["VER", "HAM"],
        "TeamName": ["Red Bull Racing", "Mercedes"],
        "TeamColor": ["3671C6", "6CD3BF"],
        "Position": [1, 2],
    })

    # Event
    session.event = {"EventName": "Test GP", "Location": "Test Circuit"}

    return session


# ── Fixture 6: Sample telemetry stream frame ──

@pytest.fixture
def sample_telemetry_frame():
    """Dict matching the TCP stream protocol format for telemetry broadcasting."""
    return {
        "frame_index": 0,
        "total_frames": 1000,
        "playback_speed": 1.0,
        "is_paused": False,
        "circuit_length_m": 5412.0,
        "track_status": {"status": "1", "message": "AllClear"},
        "frame": {
            "drivers": {
                "1": {
                    "x": 100.0, "y": 200.0,
                    "speed": 310.5, "gear": 7, "drs": 12,
                    "throttle": 98.0, "brake": 0.0,
                    "lap": 5, "tyre_compound": 0, "tyre_life": 5,
                    "relative_distance": 0.45,
                },
                "44": {
                    "x": 150.0, "y": 250.0,
                    "speed": 305.2, "gear": 6, "drs": 0,
                    "throttle": 100.0, "brake": 0.0,
                    "lap": 5, "tyre_compound": 1, "tyre_life": 5,
                    "relative_distance": 0.43,
                },
            },
            "weather": {
                "TrackTemp": 45.0, "AirTemp": 28.0,
                "Humidity": 42.0, "WindSpeed": 3.2,
                "Rainfall": 0.0,
            },
        },
    }


# ── Fixture 7: Isolated settings using tmp_path ──

@pytest.fixture
def tmp_settings(tmp_path):
    """SettingsManager that uses a temp file instead of the real settings path."""
    settings_file = tmp_path / "test_settings.json"

    with patch.object(SettingsManager, "_get_settings_file_path", return_value=settings_file):
        SettingsManager._instance = None
        manager = SettingsManager()
        yield manager
        SettingsManager._instance = None
