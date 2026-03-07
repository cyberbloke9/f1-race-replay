# Roadmap: F1 Race Replay Enhanced

## Overview

Transform F1 Race Replay from a solid race visualizer into the ultimate pit wall experience. Starting with test infrastructure and core data fixes, then systematically building out each insight window — lap evolution, tyre strategy, pit stops, gaps, sectors, overtakes — followed by practice session support and performance polish. Each phase delivers a complete, usable insight that connects to the existing telemetry stream.

## Domain Expertise

None

## Phases

- [x] **Phase 1: Foundation & Testing** — pytest infrastructure + test coverage for data pipeline and utilities
- [ ] **Phase 2: Gap Computation** — accurate time-based gaps replacing distance approximation
- [ ] **Phase 3: Lap Time Evolution Insight** — chart showing lap times across the race per driver
- [ ] **Phase 4: Tyre Strategy Insight** — visual stint timeline with degradation and pit windows
- [ ] **Phase 5: Pit Stop Analysis Insight** — pit durations, undercuts/overcuts, time delta
- [ ] **Phase 6: Gap & Battle Analysis Insight** — real-time gap evolution and battle detection
- [ ] **Phase 7: Sector & Speed Insights** — sector times + top speed tracker + DRS usage
- [ ] **Phase 8: Race Events & Overtakes** — flag timeline + overtake detection with context
- [ ] **Phase 9: Practice Sessions & Comparison** — FP1/FP2/FP3 support + head-to-head mode
- [ ] **Phase 10: Performance & Export** — rendering optimization + CSV/JSON data export

## Phase Details

### Phase 1: Foundation & Testing
**Goal**: Set up pytest with fixtures for mocking FastF1 sessions, test the data pipeline (f1_data.py), utilities (time.py, tyres.py), stream server/client, and Bayesian tyre model
**Depends on**: Nothing (first phase)
**Research**: Unlikely (standard pytest setup, established patterns)
**Plans**: 5 plans

Plans:
- [ ] 01-01: pytest setup with conftest.py and FastF1 session fixtures
- [ ] 01-02: Tests for lib/ utilities (time parsing, tyre mappings, settings)
- [ ] 01-03: Tests for f1_data.py data pipeline (telemetry extraction, resampling, frame building)
- [ ] 01-04: Tests for stream server/client (TCP socket mocking)
- [ ] 01-05: Tests for Bayesian tyre model (degradation rates, health computation)

### Phase 2: Gap Computation
**Goal**: Replace the crude distance-based gap approximation in the leaderboard with proper time-based gap computation using track position projection
**Depends on**: Phase 1
**Research**: Unlikely (internal math using existing KD-Tree and reference polyline)
**Plans**: 3 plans

Plans:
- [ ] 02-01: Implement time-based gap engine using reference polyline cumulative distance
- [ ] 02-02: Integrate gap engine into leaderboard component and telemetry stream
- [ ] 02-03: Tests for gap computation accuracy

### Phase 3: Lap Time Evolution Insight
**Goal**: PitWallWindow showing lap time chart per driver with compound colors, pit stops marked, and safety car periods shaded
**Depends on**: Phase 1 (PitWallWindow pattern established)
**Research**: Unlikely (Matplotlib in PySide6, pattern exists in driver_telemetry_window.py)
**Plans**: 3 plans

Plans:
- [ ] 03-01: Lap time data extraction from telemetry stream (accumulate per-lap times)
- [ ] 03-02: Matplotlib chart with driver selection, compound colors, pit/SC markers
- [ ] 03-03: Wire into insights menu + tests

### Phase 4: Tyre Strategy Insight
**Goal**: PitWallWindow showing horizontal stint bars per driver — compound type, stint length, degradation rate, and optimal pit window prediction using the Bayesian model
**Depends on**: Phase 1
**Research**: Unlikely (existing Bayesian model, PitWallWindow pattern)
**Plans**: 4 plans

Plans:
- [ ] 04-01: Stint data extraction — detect compound changes and pit stops from stream
- [ ] 04-02: Strategy timeline visualization (horizontal bars with compound colors)
- [ ] 04-03: Degradation overlay using Bayesian model health data
- [ ] 04-04: Wire into insights menu + tests

### Phase 5: Pit Stop Analysis Insight
**Goal**: PitWallWindow showing pit stop table — duration, position change, undercut/overcut detection, time gained/lost vs stayed-out scenario
**Depends on**: Phase 2 (needs gap data), Phase 4 (needs stint detection)
**Research**: Likely (FastF1 pit stop data fields — PitInTime, PitOutTime, PitDuration columns)
**Research topics**: FastF1 `session.laps` pit columns, how to compute undercut/overcut from position deltas
**Plans**: 4 plans

Plans:
- [ ] 05-01: Pit stop data extraction from FastF1 session laps
- [ ] 05-02: Undercut/overcut detection algorithm (position + gap analysis)
- [ ] 05-03: Pit analysis UI with sortable table and delta visualization
- [ ] 05-04: Wire into insights menu + tests

### Phase 6: Gap & Battle Analysis Insight
**Goal**: PitWallWindow showing gap evolution chart between any two drivers over race distance, with battle detection (gap < 1s sustained)
**Depends on**: Phase 2 (gap computation engine)
**Research**: Unlikely (builds on gap engine from Phase 2)
**Plans**: 3 plans

Plans:
- [ ] 06-01: Gap history accumulation from telemetry stream (per-driver-pair timeline)
- [ ] 06-02: Gap evolution chart with battle highlighting zones
- [ ] 06-03: Wire into insights menu + tests

### Phase 7: Sector & Speed Insights
**Goal**: Three PitWallWindow insights — sector times breakdown (personal/session bests), top speed tracker, and DRS usage analysis
**Depends on**: Phase 1
**Research**: Unlikely (FastF1 sector times already used in qualifying, speed data in stream)
**Plans**: 5 plans

Plans:
- [ ] 07-01: Sector time data extraction from telemetry stream
- [ ] 07-02: Sector times insight UI with color-coded personal/session bests
- [ ] 07-03: Top speed tracker insight — max speeds per driver with speed trap visualization
- [ ] 07-04: DRS usage insight — activation frequency, zones, time gained
- [ ] 07-05: Wire all three into insights menu + tests

### Phase 8: Race Events & Overtakes
**Goal**: Two PitWallWindow insights — flag/track status timeline (SC, VSC, red flag periods with context) and overtake detection (position changes with DRS/tyre context)
**Depends on**: Phase 2 (gap data for overtake context)
**Research**: Likely (overtake detection algorithm — distinguishing real overtakes from pit-induced position changes)
**Research topics**: Position change filtering (pit stops vs on-track), DRS-assisted detection, lapped car filtering
**Plans**: 4 plans

Plans:
- [ ] 08-01: Track status timeline data extraction and formatting
- [ ] 08-02: Flag tracker insight UI with timeline and period annotations
- [ ] 08-03: Overtake detection algorithm (filter pit changes, detect DRS assists)
- [ ] 08-04: Overtake counter insight UI + wire into menu + tests

### Phase 9: Practice Sessions & Comparison
**Goal**: Add FP1/FP2/FP3 session support with run-based lap analysis, and head-to-head driver comparison overlay in the race replay
**Depends on**: Phase 3 (lap time patterns), Phase 7 (sector time patterns)
**Research**: Likely (FastF1 practice session data structure, how practice runs differ from race stints)
**Research topics**: FastF1 practice session loading, run detection in practice, lap comparison UI patterns
**Plans**: 5 plans

Plans:
- [ ] 09-01: Practice session data loading and run detection
- [ ] 09-02: Practice session interface (lap times by run, compound, sector comparison)
- [ ] 09-03: Add FP1/FP2/FP3 to GUI and CLI session selectors
- [ ] 09-04: Head-to-head driver comparison overlay in race replay
- [ ] 09-05: Tests for practice session pipeline

### Phase 10: Performance & Export
**Goal**: Optimize Arcade rendering (reuse Text objects, reduce per-frame allocations), add CSV/JSON export of telemetry and analysis data, final polish
**Depends on**: All previous phases
**Research**: Unlikely (internal refactoring, standard file I/O)
**Plans**: 4 plans

Plans:
- [ ] 10-01: Audit and fix per-frame arcade.Text() allocations in ui_components.py
- [ ] 10-02: Optimize leaderboard and weather component rendering
- [ ] 10-03: CSV/JSON data export for telemetry, lap times, and analysis results
- [ ] 10-04: Final integration testing and polish

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Testing | 5/5 | Complete | 2026-03-07 |
| 2. Gap Computation | 0/3 | Not started | - |
| 3. Lap Time Evolution | 0/3 | Not started | - |
| 4. Tyre Strategy | 0/4 | Not started | - |
| 5. Pit Stop Analysis | 0/4 | Not started | - |
| 6. Gap & Battle Analysis | 0/3 | Not started | - |
| 7. Sector & Speed Insights | 0/5 | Not started | - |
| 8. Race Events & Overtakes | 0/4 | Not started | - |
| 9. Practice Sessions | 0/5 | Not started | - |
| 10. Performance & Export | 0/4 | Not started | - |
