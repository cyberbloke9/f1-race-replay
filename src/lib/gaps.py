"""Time-based gap computation engine for F1 race replay.

Computes gap_to_leader and gap_to_ahead (interval) for each driver
using track progress interpolation on a common timeline.
"""
import numpy as np


def _find_time_at_progress(
    progress_history: np.ndarray,
    time_history: np.ndarray,
    target_progress: float,
) -> float:
    """Find the time when a driver was at a given progress value.

    Uses np.searchsorted + linear interpolation on the driver's
    progress history.

    Returns:
        Interpolated time in seconds, or NaN if target_progress
        is outside the range of progress_history.
    """
    if len(progress_history) == 0:
        return np.nan

    # searchsorted finds insertion point in sorted array
    idx = np.searchsorted(progress_history, target_progress, side="right")

    if idx == 0:
        # Target is before any recorded progress — no history
        return np.nan
    if idx >= len(progress_history):
        # Target is beyond recorded progress — extrapolate from last two
        # Only if very close, otherwise NaN
        return np.nan

    # Linear interpolation between idx-1 and idx
    p0 = progress_history[idx - 1]
    p1 = progress_history[idx]
    t0 = time_history[idx - 1]
    t1 = time_history[idx]

    if p1 == p0:
        return t0

    frac = (target_progress - p0) / (p1 - p0)
    return t0 + frac * (t1 - t0)


def compute_driver_gaps(
    resampled_data: dict,
    timeline: np.ndarray,
) -> dict:
    """Compute time-based gaps between drivers.

    Args:
        resampled_data: {driver_code: {"lap": array, "rel_dist": array, ...}}
            where lap is 1-indexed lap number and rel_dist is 0-1 around track.
        timeline: Common time array (seconds), same length as the data arrays.

    Returns:
        {driver_code: {"gap_to_leader": array, "gap_to_ahead": array}}
        Arrays are same length as timeline. Values in seconds.
        Leader: 0.0. Lapped (>1 lap behind): negative (-1.0 per lap).
        Early frames with no history: NaN.
    """
    num_frames = len(timeline)
    driver_codes = list(resampled_data.keys())

    if len(driver_codes) == 0:
        return {}

    # Compute progress for each driver: progress = (lap - 1) + rel_dist
    progress = {}
    for code in driver_codes:
        lap = np.asarray(resampled_data[code]["lap"], dtype=float)
        rel_dist = np.asarray(resampled_data[code]["rel_dist"], dtype=float)
        progress[code] = (lap - 1.0) + rel_dist

    # Single driver — all gaps are zero
    if len(driver_codes) == 1:
        code = driver_codes[0]
        return {
            code: {
                "gap_to_leader": np.zeros(num_frames),
                "gap_to_ahead": np.zeros(num_frames),
            }
        }

    # Initialize output
    result = {
        code: {
            "gap_to_leader": np.full(num_frames, np.nan),
            "gap_to_ahead": np.full(num_frames, np.nan),
        }
        for code in driver_codes
    }

    # Process each frame
    for i in range(num_frames):
        # Sort drivers by progress descending at this frame
        frame_progress = [(code, progress[code][i]) for code in driver_codes]
        frame_progress.sort(key=lambda x: x[1], reverse=True)

        leader_code = frame_progress[0][0]
        result[leader_code]["gap_to_leader"][i] = 0.0
        result[leader_code]["gap_to_ahead"][i] = 0.0

        # For each non-leader driver, compute gaps
        for pos_idx in range(1, len(frame_progress)):
            behind_code = frame_progress[pos_idx][0]
            ahead_code = frame_progress[pos_idx - 1][0]
            behind_progress_val = frame_progress[pos_idx][1]
            leader_progress_val = frame_progress[0][1]

            # Check if lapped (more than 1 full lap behind leader)
            lap_diff = leader_progress_val - behind_progress_val
            if lap_diff >= 1.0:
                laps_behind = int(lap_diff)
                result[behind_code]["gap_to_leader"][i] = -float(laps_behind)
                # Interval to car ahead: also compute normally or mark lapped
                ahead_progress_val = frame_progress[pos_idx - 1][1]
                ahead_lap_diff = ahead_progress_val - behind_progress_val
                if ahead_lap_diff >= 1.0:
                    result[behind_code]["gap_to_ahead"][i] = -float(
                        int(ahead_lap_diff)
                    )
                else:
                    # Compute interval gap to car ahead
                    ahead_prog_history = progress[ahead_code][: i + 1]
                    ahead_time_history = timeline[: i + 1]
                    t_ahead = _find_time_at_progress(
                        ahead_prog_history, ahead_time_history,
                        behind_progress_val,
                    )
                    if np.isnan(t_ahead):
                        result[behind_code]["gap_to_ahead"][i] = np.nan
                    else:
                        result[behind_code]["gap_to_ahead"][i] = (
                            timeline[i] - t_ahead
                        )
                continue

            # Gap to leader
            leader_prog_history = progress[leader_code][: i + 1]
            leader_time_history = timeline[: i + 1]
            t_leader = _find_time_at_progress(
                leader_prog_history, leader_time_history,
                behind_progress_val,
            )
            if np.isnan(t_leader):
                result[behind_code]["gap_to_leader"][i] = np.nan
            else:
                result[behind_code]["gap_to_leader"][i] = timeline[i] - t_leader

            # Gap to car directly ahead (interval)
            if ahead_code == leader_code:
                # Already computed
                result[behind_code]["gap_to_ahead"][i] = (
                    result[behind_code]["gap_to_leader"][i]
                )
            else:
                ahead_prog_history = progress[ahead_code][: i + 1]
                ahead_time_history = timeline[: i + 1]
                t_ahead = _find_time_at_progress(
                    ahead_prog_history, ahead_time_history,
                    behind_progress_val,
                )
                if np.isnan(t_ahead):
                    result[behind_code]["gap_to_ahead"][i] = np.nan
                else:
                    result[behind_code]["gap_to_ahead"][i] = (
                        timeline[i] - t_ahead
                    )

    return result
