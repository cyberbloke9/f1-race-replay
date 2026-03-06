# F1 Race Replay - Claude Code Instructions

## Project Overview

F1 Race Replay is a Python desktop application for visualizing Formula 1 race telemetry and replaying race events. It uses FastF1 for data, Arcade for OpenGL rendering, and PySide6 for GUI windows.

## Architecture

```
f1-race-replay/
├── main.py                          # Entry point — CLI args, GUI launcher, session orchestration
├── src/
│   ├── f1_data.py                   # Data pipeline — FastF1 loading, telemetry processing, frame generation
│   ├── run_session.py               # Session launcher — Arcade window + insights menu subprocess
│   ├── ui_components.py             # Arcade UI primitives — leaderboard, weather, legend, controls, progress bar
│   ├── bayesian_tyre_model.py       # Bayesian state-space model — tyre degradation with Kalman filter
│   ├── tyre_degradation_integration.py  # Integrator bridge between Bayesian model and UI
│   ├── interfaces/
│   │   ├── race_replay.py           # F1RaceReplayWindow (Arcade) — main race visualization (~800 lines)
│   │   └── qualifying.py            # QualifyingReplay (Arcade) — qualifying telemetry charts
│   ├── gui/
│   │   ├── race_selection.py        # PySide6 race/session selector with year/race filtering
│   │   ├── insights_menu.py         # PySide6 floating menu — launches insight windows
│   │   ├── pit_wall_window.py       # PitWallWindow base class — auto-connects to telemetry stream
│   │   ├── pit_wall_window_template.py  # Template for creating custom insight windows
│   │   └── settings_dialog.py       # Settings UI for cache/data paths
│   ├── insights/
│   │   ├── driver_telemetry_window.py   # Live speed/gear/throttle/brake charts (Matplotlib)
│   │   ├── telemetry_stream_viewer.py   # Raw telemetry data viewer/debugger
│   │   └── example_pit_wall_window.py   # Example PitWallWindow implementation
│   ├── services/
│   │   └── stream.py                # TCP socket server/client for telemetry broadcasting
│   ├── lib/
│   │   ├── settings.py              # Singleton JSON settings manager
│   │   ├── time.py                  # Time parsing/formatting utilities
│   │   └── tyres.py                 # Tyre compound ↔ integer mappings
│   └── cli/
│       └── race_selection.py        # CLI race selector (questionary + rich)
```

## Tech Stack — DO NOT CHANGE

- **Visualization**: Arcade (OpenGL) — the race replay renderer
- **GUI Windows**: PySide6 (Qt) — all insight windows, menus, dialogs
- **Data**: FastF1 — F1 telemetry data source
- **Numerical**: NumPy, Pandas, SciPy
- **Charts**: Matplotlib (in PySide6 windows via QtAgg backend)
- **CLI**: questionary + rich
- **No vulnerable dependencies** — check before adding any new package

## Key Patterns

### PitWallWindow Pattern (for all new insight windows)
All insight windows MUST extend `PitWallWindow` from `src/gui/pit_wall_window.py`:
```python
from src.gui.pit_wall_window import PitWallWindow

class MyInsightWindow(PitWallWindow):
    def setup_ui(self):
        # Create PySide6 UI here
        pass

    def on_telemetry_data(self, data):
        # Process incoming telemetry frame
        # data contains: frame_index, frame (with drivers dict), track_status,
        #                playback_speed, is_paused, total_frames, circuit_length_m
        pass
```
The base class handles TCP stream connection, status bar, and cleanup automatically.

### Telemetry Stream Protocol
- TCP socket on `localhost:9999`
- JSON messages separated by newlines
- Server runs in `F1RaceReplayWindow`, clients connect from insight windows
- Each frame contains all 20 drivers' x/y/speed/gear/drs/throttle/brake/lap/tyre data + weather

### Data Pipeline
1. `load_session()` — FastF1 session loading with telemetry + weather
2. `get_race_telemetry()` — Multiprocessing driver telemetry extraction → resampling → frame building
3. Pickle caching in `computed_data/` for fast reload
4. 25 FPS timeline with NumPy interpolation

### Arcade Rendering
- `world_to_screen()` transforms world coordinates with rotation + scaling
- KD-Tree (`scipy.spatial.cKDTree`) for fast track position projection
- Reuse `arcade.Text()` objects — never create new ones per frame
- Components follow `BaseComponent` pattern with `draw(window)` and `on_mouse_press()`

### Adding Insight Windows to the Menu
1. Create window class extending `PitWallWindow` in `src/insights/`
2. Add launch method in `src/gui/insights_menu.py`
3. Add button to a category section in `InsightsMenu.setup_ui()`
4. See `docs/InsightsMenu.md` for full guide

## Coding Standards

- **Python 3.11+** required
- Use type hints for function signatures
- Use `numpy` vectorized operations over Python loops for data processing
- Reuse `arcade.Text()` objects in draw methods — allocating per-frame causes lag
- Use multiprocessing (`Pool`) for parallel driver telemetry extraction
- Pickle for computed data caching (10-100x faster than JSON)
- Settings go through `src/lib/settings.py` singleton, never hardcode paths

## Testing

- Tests go in `tests/` directory at project root
- Use `pytest` as the test runner
- Mock FastF1 session objects for data pipeline tests
- Mock TCP sockets for stream tests
- No need to test Arcade rendering (visual, not unit-testable)

## GYWD Workflow

This project uses the GYWD (Get Your Work Done) framework for planning and execution:
- `.planning/PROJECT.md` — project vision, requirements, constraints
- `.planning/ROADMAP.md` — milestone and phase breakdown
- `.planning/STATE.md` — current progress tracking
- `.planning/phases/` — per-phase plans and summaries
- Use `/gywd:progress` to check status, `/gywd:execute-plan` to run plans

## Common Pitfalls

- `arcade.Text()` in draw loops = memory leak + lag. Always reuse.
- FastF1 `session.load(telemetry=True)` is slow — always check pickle cache first
- `multiprocessing.Pool` requires top-level functions (can't pickle lambdas/closures)
- PySide6 and Arcade run in separate processes — communicate via TCP stream only
- Tyre compound integers: SOFT=0, MEDIUM=1, HARD=2, INTERMEDIATE=3, WET=4
- Weather rainfall threshold: >= 0.5 = RAINING, < 0.5 = DRY
- Brake values from stream are 0-1, but UI expects 0-100 (multiply by 100)
