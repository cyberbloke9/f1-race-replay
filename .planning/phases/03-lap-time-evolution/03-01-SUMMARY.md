---
phase: 03-lap-time-evolution
plan: 01
subsystem: insights
tags: [lap-times, pit-wall, matplotlib, tyre-compound, safety-car, pit-stops]

requires:
  - phase: 01-foundation/01
    provides: PitWallWindow base class pattern
provides:
  - LapTimeEvolutionWindow with multi-driver lap time chart
  - LapTimeAccumulator pure-data class for testable lap time tracking
  - Compound-colored scatter markers and pit stop detection
  - SC/VSC period shading on chart
  - "Race Analysis" category in insights menu
affects: [03-lap-time-evolution]

tech-stack:
  added: []
  patterns: [pure-data accumulator extracted for testability, pending_pit state for correct pit marking]

key-files:
  created: [src/insights/lap_time_evolution_window.py, tests/test_lap_time_evolution.py]
  modified: [src/gui/insights_menu.py]

key-decisions:
  - "Extract LapTimeAccumulator as pure-data class for Qt-free testing"
  - "Pit stop marked on first lap with new compound (not outgoing lap)"
  - "Skip lap 1 (formation/out lap) and filter outliers >150s"
  - "SC/VSC periods tracked via state machine on track_status changes"

patterns-established:
  - "Pure-data accumulator pattern: extract stateful logic from PitWallWindow into testable class"
  - "Pit stop detection via pending_pit flag carried to next completed lap"

issues-created: []

duration: 5min
completed: 2026-03-07
---

# Phase 3 Plan 1: Lap Time Evolution Window Summary

**Created LapTimeEvolutionWindow with data accumulation, compound-colored chart, menu integration, and 16 tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-07
- **Completed:** 2026-03-07
- **Tasks:** 3/3
- **Files created:** 2
- **Files modified:** 1

## Accomplishments
- Created `LapTimeEvolutionWindow` extending `PitWallWindow` with Matplotlib chart
- Extracted `LapTimeAccumulator` pure-data class for testable lap time tracking
- Multi-driver selection via QListWidget with checkable items and QSplitter layout
- Compound-colored scatter markers (SOFT red, MEDIUM yellow, HARD white, INTER green, WET blue)
- Pit stop detection: marks the first lap on new tyres (pending_pit pattern)
- SC/VSC period shading (yellow/orange axvspan bands)
- Pit stop laps marked with vertical dashed gray lines
- Added "Race Analysis" category to InsightsMenu with Lap Time Evolution button
- Replaced placeholder `launch_lap_evolution` with working `launch_lap_time_evolution`
- 16 new tests covering accumulation, compounds, pit stops, SC detection, multi-driver, edge cases
- All 104 tests passing (88 existing + 16 new)

## Task Commits

1. **Task 1: Create LapTimeEvolutionWindow** - `62e4448` (feat)
2. **Task 2: Wire into insights menu** - `ae4b9b8` (feat)
3. **Task 3: Tests for accumulation logic** - `a2410ed` (test)

## Files Created/Modified
- `src/insights/lap_time_evolution_window.py` - LapTimeEvolutionWindow + LapTimeAccumulator (new)
- `tests/test_lap_time_evolution.py` - 16 tests in 4 test classes (new)
- `src/gui/insights_menu.py` - Added "Race Analysis" category, replaced placeholder

## Decisions Made
- Extracted accumulation logic into `LapTimeAccumulator` for Qt-free testing (following test_gaps.py pattern)
- Pit stop flag uses `pending_pit` on `_DriverState` — set at lap transition, consumed on next lap completion
- Outlier threshold at 150s filters pit laps and red flag periods

## Deviations from Plan

- **Plan listed 3 separate plans (03-01, 03-02, 03-03) but execution context says 1 plan with 3 tasks** — executed as single plan with all 3 tasks (window creation, menu wiring, tests). This is correct per the PLAN.md task structure.
- **Pit stop marking fix (Rule 1 auto-fix):** Initial implementation marked the outgoing lap as pit stop; corrected to mark the incoming lap (first on new compound) using pending_pit pattern.

## Issues Encountered

None

## Next Step

Phase 3 complete (1/1 plans). Ready for Phase 4: Tyre Strategy Insight.

---
*Phase: 03-lap-time-evolution*
*Completed: 2026-03-07*
