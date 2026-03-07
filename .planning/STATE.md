# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-07)

**Core value:** The pit wall insight system — dedicated analysis windows that transform raw telemetry into actionable race understanding
**Current focus:** Phase 4 — Tyre Strategy Insight

## Current Position

Phase: 4 of 10 (Tyre Strategy)
Plan: Not started
Status: Ready to plan
Last activity: 2026-03-07 — Phase 3 complete (104 tests passing)

Progress: ███░░░░░░░ 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: ~4 min/plan
- Total execution time: ~39 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation & Testing | 5/5 | ~25 min | ~5 min |
| 2. Gap Computation | 3/3 | ~9 min | ~3 min |
| 3. Lap Time Evolution | 1/1 | ~5 min | ~5 min |

**Recent Trend:**
- Last 5 plans: 01-05, 02-01, 02-02, 02-03, 03-01
- Trend: Consistent — established patterns enable single-plan phases

## Accumulated Context

### Decisions

- Mock FastF1 sessions (never hit network in tests)
- Real localhost sockets for stream tests (not mocked)
- Behavioral property tests for Bayesian model (not exact math)
- Reset SettingsManager singleton between tests (autouse fixture)
- Progress metric: (lap - 1) + rel_dist as continuous float for gap computation
- Lapped cars use negative gap values (-1.0 per lap behind)
- Pre-computed gap data embedded in frame driver dicts (gap_to_leader, gap_to_ahead)
- Leaderboard falls back to crude distance math for old cached pickle files
- Extract pure-data accumulator classes from PitWallWindows for Qt-free testing
- Pit stop marked on first lap with new compound (pending_pit pattern)

### Deferred Issues

- ~~f1_data.py `total_dist_so_far` bug~~ — RESOLVED in Phase 2 (02-02)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-07
Stopped at: Phase 3 complete, all 104 tests passing
Resume file: None
