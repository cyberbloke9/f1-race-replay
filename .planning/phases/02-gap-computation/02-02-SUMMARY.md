---
phase: 02-gap-computation
plan: 02
subsystem: data-pipeline
tags: [distance, gaps, f1_data, pipeline, integration]

requires:
  - phase: 02-gap-computation/01
    provides: compute_driver_gaps() function
provides:
  - Fixed race distance accumulation across laps
  - Gap data (gap_to_leader, gap_to_ahead) in every frame's driver dict
affects: [02-gap-computation, 06-gap-battle-analysis]

tech-stack:
  added: []
  patterns: [gap data embedded in telemetry frames]

key-files:
  created: []
  modified: [src/f1_data.py, tests/test_f1_data.py]

key-decisions:
  - "Distance fix: total_dist_so_far += d_lap.max() after each lap"
  - "Gap data added as gap_to_leader and gap_to_ahead in frame driver dicts"

patterns-established:
  - "Pre-computed analysis data embedded directly in frame dicts for downstream consumption"

issues-created: []

duration: 3min
completed: 2026-03-07
---

# Phase 2 Plan 2: Distance Fix + Pipeline Integration Summary

**Fixed distance accumulation bug and wired gap engine into frame building — gap_to_leader and gap_to_ahead in every frame**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-07T04:03:41Z
- **Completed:** 2026-03-07T04:06:30Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- Fixed `total_dist_so_far` — race distance now accumulates correctly across laps
- Integrated `compute_driver_gaps()` call after resampling step in `get_race_telemetry()`
- Every frame's driver dict now carries `gap_to_leader` and `gap_to_ahead` (float seconds or None)
- Updated distance test to verify accumulation (>5000m for 3 laps)

## Task Commits

1. **Task 1: Fix distance accumulation** - `1abb11a` (fix)
2. **Task 2: Integrate gap engine** - `5f72ace` (feat)

## Files Created/Modified
- `src/f1_data.py` - Distance fix (1 line) + gap import + gap computation call + gap data in frames
- `tests/test_f1_data.py` - Updated distance test to verify accumulation

## Decisions Made
- Distance fix: `total_dist_so_far += d_lap.max()` — max distance in lap = one lap length
- Gap data as float seconds or None (NaN converted to None for JSON serialization)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Step

Ready for 02-03-PLAN.md (leaderboard update + integration tests)

---
*Phase: 02-gap-computation*
*Completed: 2026-03-07*
