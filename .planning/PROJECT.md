# F1 Race Replay Enhanced

## What This Is

A Python desktop application for replaying and analyzing Formula 1 race telemetry data. Built on FastF1, Arcade (OpenGL), and PySide6, it provides a pit wall experience where users can watch races unfold with real-time driver positions, leaderboards, weather, and tyre degradation — plus launch dedicated insight windows for deep telemetry analysis.

## Core Value

The pit wall insight system — a suite of dedicated analysis windows (lap evolution, tyre strategy, gap analysis, pit stops, overtakes, sector times) that transform raw telemetry into actionable race understanding. Every F1 data point should be explorable.

## Requirements

### Validated

- Race replay visualization with driver positions on rendered track — existing
- Leaderboard with live positions, tyre compounds, and gap display — existing
- Weather telemetry display (track/air temp, humidity, wind, rain) — existing
- Interactive playback controls (pause, rewind, fast forward, speed 0.1x-256x) — existing
- Qualifying session replay with speed/gear/throttle/brake charts — existing
- Sprint and Sprint Qualifying session support — existing
- GUI race/session selector with year and race filtering — existing
- CLI race selector with questionary — existing
- PitWallWindow base class for extensible insight windows — existing
- TCP telemetry stream server broadcasting to insight windows — existing
- Driver telemetry insight (live speed/gear/throttle/brake per driver) — existing
- Telemetry stream viewer (raw data debugger) — existing
- Bayesian tyre degradation model with Kalman filter — existing
- DRS zone detection and visualization — existing
- Multiprocessing telemetry extraction with pickle caching — existing
- Configurable cache/data paths via settings dialog — existing
- Resizable window with dynamic track scaling — existing
- Circuit rotation for correct track orientation — existing
- Driver selection on leaderboard (click + shift-click multi-select) — existing

### Active

- [ ] Lap Time Evolution insight — chart showing lap times across the race for selected drivers
- [ ] Tyre Strategy insight — visual stint timeline showing compound changes and degradation
- [ ] Pit Stop Analysis insight — pit stop durations, undercuts/overcuts, time gained/lost
- [ ] Gap Analysis insight — real-time gap evolution between selected drivers
- [ ] Sector Times insight — sector-by-sector breakdown with personal/session bests
- [ ] Overtake Detection insight — position change events with context (DRS, tyre delta)
- [ ] DRS Usage insight — DRS activation frequency, time gained per zone
- [ ] Top Speed Tracker insight — speed trap data and max speeds per driver
- [ ] Flag/Track Status Tracker insight — safety car periods, VSC, red flags with timeline
- [ ] Practice Session support (FP1/FP2/FP3) — run analysis and lap comparison
- [ ] Accurate gap computation — proper time-based gaps replacing distance approximation
- [ ] Performance optimization — reduce Arcade rendering lag, reuse Text objects
- [ ] Test suite — pytest coverage for data pipeline, stream, and utilities
- [ ] Data export — CSV/JSON export of telemetry and analysis results
- [ ] Head-to-head driver comparison mode in race replay

### Out of Scope

- Live F1 data streaming — this is a replay/historical tool using FastF1 cached data
- Web/browser version — stays as desktop Python (Arcade + PySide6)
- Team/social features — single-user local tool, no accounts or sharing
- Framework migration — no replacing Arcade, PySide6, or FastF1
- Mobile app — desktop only for this enhancement round

## Context

- **Upstream**: Forked from github.com/IAmTomShaw/f1-race-replay (MIT license)
- **Maturity**: Active open-source project with community contributions, ~230 commits
- **Insights Menu**: 12 placeholder launch methods exist but only 3 are implemented (Example, Stream Viewer, Driver Telemetry). The PitWallWindow pattern is solid and ready for new windows.
- **Data richness**: FastF1 provides extensive data (lap times, sector times, pit stops, tyre info, weather, car telemetry) — most of it is loaded but not yet surfaced in insight windows
- **Tyre model**: A sophisticated Bayesian state-space model exists but is only used for health bars on the leaderboard — could power deeper strategy insights
- **Performance**: Creating new `arcade.Text()` per frame in some draw paths causes lag on lower-end machines. Several components need optimization.
- **Tests**: Zero test files exist. Core data pipeline and utilities are testable.

## Constraints

- **Tech stack**: Must stay on Arcade + PySide6 + FastF1 + NumPy + SciPy + Matplotlib. No framework changes.
- **Dependencies**: No packages with known vulnerabilities. Check before adding any new dependency.
- **Architecture**: New insight windows MUST use the PitWallWindow base class pattern
- **Stream protocol**: TCP socket on localhost:9999 with newline-delimited JSON
- **Python**: 3.11+ required

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PitWallWindow pattern for all insights | Consistent architecture, auto telemetry connection, clean lifecycle | -- Pending |
| Keep Arcade for rendering | Already works, community familiar with it, no benefit to switching | -- Pending |
| Insight windows as separate PySide6 processes | Decoupled from Arcade main loop, can't mix Qt and Arcade in same process | -- Pending |
| Bayesian model for tyre analysis | More accurate than linear regression, accounts for fuel/weather/track | -- Pending |
| Pickle caching over JSON | 10-100x faster serialization for large telemetry datasets | -- Pending |

---
*Last updated: 2026-03-07 after initialization*
