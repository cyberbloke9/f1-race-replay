# Phase 1 Research: Foundation & Testing

## Research Summary

Phase 1 sets up pytest infrastructure with fixtures for mocking FastF1 sessions, tests the data pipeline, utilities, stream server/client, and Bayesian tyre model. Research confirms standard pytest patterns apply — no exotic libraries needed.

## 1. pytest Setup & Configuration

### Standard Stack
- **pytest** — test runner (already in ecosystem, no version concerns)
- **pytest-mock** — thin wrapper around `unittest.mock` for cleaner fixture-based mocking
- **No additional test deps needed** — no pytest-asyncio (no async code), no pytest-qt (we mock PySide6 signals, not test Qt UI)

### conftest.py Structure
```
tests/
├── conftest.py              # Shared fixtures: mock sessions, sample telemetry frames
├── test_time.py             # lib/time.py — parse_time_string, format_time
├── test_tyres.py            # lib/tyres.py — compound mappings
├── test_settings.py         # lib/settings.py — SettingsManager (needs tmp_path)
├── test_f1_data.py          # f1_data.py — data pipeline
├── test_stream.py           # services/stream.py — TCP server/client
└── test_bayesian_tyre.py    # bayesian_tyre_model.py — degradation model
```

### Key Fixtures Needed
1. **`mock_session`** — Mocks `fastf1.Session` with `.laps`, `.weather_data`, `.results`
2. **`mock_laps`** — Fake `Laps` DataFrame with lap times, compounds, tyre life, pit data
3. **`sample_telemetry_frame`** — Dict matching the stream protocol format (20 drivers)
4. **`tmp_settings`** — Isolated SettingsManager using `tmp_path` to avoid touching real settings

## 2. Mocking FastF1 Sessions

### What to Mock
FastF1 `Session` objects are heavy — they download from the F1 API and cache locally. Tests must never hit the network.

**Session attributes used by f1_data.py:**
- `session.laps` → `Laps` (extended DataFrame)
- `session.laps.pick_drivers(driver_no)` → filtered laps
- `lap.get_telemetry()` → DataFrame with columns: SessionTime, X, Y, Distance, RelativeDistance, Speed, nGear, DRS, Throttle, Brake
- `lap.LapNumber`, `lap.Compound`, `lap.TyreLife`
- `session.weather_data` → DataFrame with TrackTemp, AirTemp, Humidity, WindSpeed, Rainfall
- `session.results` → DataFrame with DriverNumber, Abbreviation, TeamName, TeamColor, Position
- `session.event` → dict-like with EventName, Location
- `session.total_laps` → int

### Mocking Pattern
```python
@pytest.fixture
def mock_session():
    session = MagicMock()

    # Build fake laps DataFrame
    laps_data = pd.DataFrame({
        'DriverNumber': ['1', '1', '44', '44'],
        'LapNumber': [1, 2, 1, 2],
        'Compound': ['SOFT', 'SOFT', 'MEDIUM', 'MEDIUM'],
        'TyreLife': [1, 2, 1, 2],
        'LapTime': [pd.Timedelta(seconds=90), pd.Timedelta(seconds=91), ...],
    })

    # Mock pick_drivers to filter by driver number
    session.laps = MagicMock()
    session.laps.pick_drivers = lambda dn: laps_data[laps_data.DriverNumber == dn]

    # Mock iterlaps to yield (index, lap_series) tuples
    # Mock lap.get_telemetry() to return small fake telemetry DataFrames
    ...
    return session
```

### FastF1's Own Testing Approach
From FastF1 docs: they use cached response data and pytest fixtures. They don't mock the Session object — they use real cached data. For our project, we mock because we don't want to depend on cached F1 data in CI.

### Key Insight: Laps vs Lap
- `session.laps` returns a `Laps` object (extended DataFrame)
- `laps.iterlaps()` yields `(index, Lap)` tuples where `Lap` is a Series-like
- `lap.get_telemetry()` returns a `Telemetry` DataFrame
- For mocking: use `MagicMock` for Lap with `.get_telemetry()` returning a real pd.DataFrame

## 3. Testing the Data Pipeline (f1_data.py)

### Functions to Test
1. **`enable_cache()`** — Verify it calls `fastf1.Cache.enable_cache()` with correct path
2. **`_process_single_driver(args)`** — Core telemetry extraction per driver. Test with mock session/laps.
3. **`get_race_telemetry(session)`** — Orchestrates multiprocessing extraction + resampling
4. **`get_quali_telemetry(session)`** — Similar for qualifying
5. **Resampling logic** — NumPy interpolation at 25 FPS

### Testing Multiprocessing
- `multiprocessing.Pool` requires picklable arguments
- For tests: **mock `Pool` to run serially** — `pool.map(fn, args)` → `[fn(a) for a in args]`
- This avoids multiprocessing overhead in tests while testing the same logic

### Pickle Caching
- Test that `computed_data/` files are written and read correctly
- Use `tmp_path` fixture to isolate from real cache

## 4. Testing TCP Stream (services/stream.py)

### Architecture
- `TelemetryStreamServer` — vanilla TCP socket server with threading
- `TelemetryStreamClient` — PySide6 `QThread` with signals

### Testing Approach: Real Sockets on Localhost

**Do NOT mock sockets** for integration tests. Use real localhost sockets:

```python
@pytest.fixture
def stream_server():
    server = TelemetryStreamServer(host='localhost', port=0)  # port=0 = OS picks free port
    server.start()
    yield server
    server.stop()
```

**Problem:** `TelemetryStreamServer` hardcodes port 9999 and doesn't expose the bound port.
**Solution options:**
1. Pass `port=0` and read `server.server_socket.getsockname()[1]` after bind — requires the server to expose the actual port
2. Use a high random port like `19999` to avoid conflicts
3. Best: modify server to support port=0 and expose actual port (tiny refactor)

### Testing the Client (QThread)
The `TelemetryStreamClient` extends `QThread` and uses PySide6 `Signal`. Testing options:
1. **Mock the QThread entirely** — replace `run()` behavior, test `_receive_data()` logic directly
2. **Use `unittest.mock` for Signal** — mock `data_received.emit()` and verify it gets called
3. **Don't test the Qt layer** — test the socket/JSON parsing logic in isolation

**Recommended:** Extract the socket+JSON logic into a testable helper, test that. Mock the QThread signals.

### Protocol Verification
- Messages are newline-delimited JSON: `json.dumps(data).encode('utf-8') + b'\n'`
- Test: send known dict → receive → verify deserialized match

## 5. Testing the Bayesian Tyre Model

### What to Test
1. **TyreProfile dataclass** — validation (negative degradation_rate raises ValueError)
2. **StateSpaceConfig** — default mismatch_penalties, parameter bounds
3. **BayesianTyreDegradationModel** — core Kalman filter logic:
   - State prediction step
   - Observation update step
   - Health computation (0-1 range)
   - Track abrasion estimation
   - Fuel correction
   - Mismatch penalty application

### Testing Strategy: Known-Input/Known-Output

For Kalman filter testing:
```python
def test_degradation_increases_with_laps():
    model = BayesianTyreDegradationModel(profile, config)
    healths = []
    for lap in range(1, 20):
        model.update(lap_time=90 + lap * 0.1, lap_number=lap, ...)
        healths.append(model.get_health())
    # Health should decrease monotonically (with some noise tolerance)
    assert all(healths[i] >= healths[i+1] - 0.05 for i in range(len(healths)-1))
```

### Property-Based Tests
- Health always in [0, 1]
- Pit stop resets health toward 1.0
- Wet tyres on dry track → worse health than matching conditions
- Fuel correction is positive (lighter car = faster)

### What NOT to Test
- Exact Kalman filter math (implementation detail, changes with tuning)
- Specific numerical outputs (model is probabilistic)
- Instead: test behavioral properties and boundary conditions

## 6. Testing Utilities

### lib/time.py
Straightforward parametrized tests:
```python
@pytest.mark.parametrize("input,expected", [
    ("01:26.123", 86.123),
    ("00:01:26.123000", 86.123),
    ("0 days 00:01:27.060000", 87.06),
    ("", None),
    (None, None),
])
def test_parse_time_string(input, expected):
    assert parse_time_string(input) == expected
```

### lib/tyres.py
- `get_tyre_compound_int("SOFT")` → 0
- `get_tyre_compound_str(0)` → "SOFT"
- Edge: unknown compound → -1 / "UNKNOWN"

### lib/settings.py
- Singleton behavior (tricky in tests — must reset `_instance`)
- `tmp_path` for isolated settings file
- Load/save round-trip
- Default values
- Reset to defaults

**Singleton Reset Pattern:**
```python
@pytest.fixture(autouse=True)
def reset_settings_singleton():
    SettingsManager._instance = None
    yield
    SettingsManager._instance = None
```

## 7. Dependencies

### Required (add to dev dependencies)
- `pytest` >= 7.0
- `pytest-mock` — for `mocker` fixture

### NOT Needed
- `pytest-qt` — we're not testing Qt UI, just mocking signals
- `pytest-asyncio` — no async code in the project
- `pytest-socket` — we want real localhost sockets for stream tests
- `mocket` / `pytest-tcpclient` — overkill for our simple TCP protocol
- `hypothesis` — nice-to-have for property testing but not required for Phase 1

## 8. CI Considerations

- Tests should run without FastF1 cache data (all mocked)
- Tests should run without network access (no F1 API calls)
- Tests should run without PySide6 display server (mock Qt, don't instantiate windows)
- Port allocation: use random high ports to avoid CI conflicts

## Key Decisions for Planning

| Decision | Rationale |
|----------|-----------|
| Mock FastF1 sessions, don't use cached data | CI portability, no network dependency |
| Real localhost sockets for stream tests | More reliable than socket mocking, tests actual protocol |
| Property-based tests for Bayesian model | Probabilistic model — test behavior, not exact numbers |
| Reset singleton in fixtures | SettingsManager singleton leaks state between tests |
| Mock multiprocessing Pool | Serial execution in tests, same logic coverage |
| No pytest-qt dependency | We test logic, not Qt UI rendering |

## Sources

- [FastF1 Testing Docs](https://docs.fastf1.dev/contributing/testing.html)
- [FastF1 Core API — Session, Laps, Telemetry](https://docs.fastf1.dev/core.html)
- [pytest-mock on PyPI](https://pypi.org/project/pytest-mock/)
- [DevDungeon — Unit Testing TCP Server & Client](https://www.devdungeon.com/content/unit-testing-tcp-server-client-python)
- [FilterPy — Kalman Filter Testing Patterns](https://filterpy.readthedocs.io/en/latest/)
- [python-mocket — Socket Mock Framework](https://github.com/mindflayer/python-mocket)
