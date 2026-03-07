---
phase: 02-gap-computation
plan: 01
subsystem: data-pipeline
tags: [numpy, gaps, timing, searchsorted, interpolation]

requires:
  - phase: 01-foundation-testing
    provides: pytest infrastructure, conftest fixtures
provides:
  - compute_driver_gaps() function for time-based gap calculation
  - _find_time_at_progress() helper for timeline interpolation
affects: [02-gap-computation, 06-gap-battle-analysis]

tech-stack:
  added: []
  patterns: [progress-based gap computation using searchsorted + interpolation]

key-files:
  created: [src/lib/gaps.py, tests/test_gaps.py]
  modified: []

key-decisions:
  - "Progress metric: (lap - 1) + rel_dist as continuous float"
  - "Lapped cars use negative gap values (-1.0 per lap behind)"
  - "Early frames where no history exists use NaN"

patterns-established:
  - "Gap computation via searchsorted on progress timeline + linear interpolation"

issues-created: []

duration: 3min
completed: 2026-03-07
---

# Phase 2 Plan 1: Gap Computation Engine (TDD) Summary

**Time-based gap engine using progress interpolation with searchsorted — 9 tests, 176-line module**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-07T03:59:56Z
- **Completed:** 2026-03-07T04:02:33Z
- **Tasks:** 2 (RED + GREEN, REFACTOR skipped)
- **Files modified:** 2

## Accomplishments
- `compute_driver_gaps()` computes accurate time-based gaps for all drivers on a shared timeline
- `_find_time_at_progress()` helper interpolates between adjacent frames using searchsorted
- Progress metric: `(lap - 1) + rel_dist` gives continuous laps-completed float
- 9 tests covering single driver, two drivers, three drivers interval, lapped, early frames, output shape

## Task Commits

1. **RED: Failing gap tests** - `17f4022` (test)
2. **GREEN: Implement gap engine** - `b61098e` (feat)

REFACTOR skipped — implementation was clean.

## Files Created/Modified
- `src/lib/gaps.py` - Gap computation engine (176 lines, compute_driver_gaps + _find_time_at_progress)
- `tests/test_gaps.py` - 9 tests across 6 test classes

## Decisions Made
- Progress = (lap - 1) + rel_dist as continuous float (simpler than cumulative distance, works with existing data)
- Lapped cars: negative gap values (-1.0 per full lap behind)
- Early frames: NaN (no history to interpolate)
- No REFACTOR needed — implementation clean on first pass

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Step

Ready for 02-02-PLAN.md (distance fix + pipeline integration)

---
*Phase: 02-gap-computation*
*Completed: 2026-03-07*
