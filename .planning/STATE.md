# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-07)

**Core value:** The pit wall insight system — dedicated analysis windows that transform raw telemetry into actionable race understanding
**Current focus:** Phase 3 — Lap Time Evolution Insight

## Current Position

Phase: 3 of 10 (Lap Time Evolution)
Plan: Not started
Status: Ready to plan
Last activity: 2026-03-07 — Phase 2 complete (88 tests passing)

Progress: ██░░░░░░░░ 17%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: ~4 min/plan
- Total execution time: ~34 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation & Testing | 5/5 | ~25 min | ~5 min |
| 2. Gap Computation | 3/3 | ~9 min | ~3 min |

**Recent Trend:**
- Last 5 plans: 01-04, 01-05, 02-01, 02-02, 02-03
- Trend: Accelerating — Phase 2 plans faster due to established patterns

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

### Deferred Issues

- ~~f1_data.py `total_dist_so_far` bug~~ — RESOLVED in Phase 2 (02-02)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-07
Stopped at: Phase 2 complete, all 88 tests passing
Resume file: None
