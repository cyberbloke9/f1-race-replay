"""Lap Time Evolution insight window.

Shows lap time progression across the race for selected drivers with
compound-colored markers, pit stop indicators, and safety car shading.
"""

import sys
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QSplitter,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.gui.pit_wall_window import PitWallWindow

# Tyre compound colors (matching F1 broadcast)
COMPOUND_COLORS: dict[int, str] = {
    0: "#FF3333",   # SOFT — red
    1: "#FFC300",   # MEDIUM — yellow
    2: "#FFFFFF",   # HARD — white
    3: "#43B02A",   # INTERMEDIATE — green
    4: "#0072CE",   # WET — blue
}

# Default driver line color palette (10 distinct colors, cycled)
DRIVER_LINE_COLORS: list[str] = [
    "#3366FF", "#FF6633", "#33CC33", "#CC33FF", "#FFCC00",
    "#00CCCC", "#FF3399", "#99CC00", "#FF9900", "#6666FF",
]

_BG = "#282828"
_OUTLIER_THRESHOLD_S = 150.0  # laps longer than this are filtered out


@dataclass
class CompletedLap:
    """A single completed lap record."""
    lap_num: int
    lap_time_s: float
    compound_int: int
    is_pit_stop: bool = False  # compound changed from previous lap


@dataclass
class _DriverState:
    """Mutable per-driver tracking state."""
    current_lap: int | None = None
    lap_start_t: float | None = None
    last_compound: int | None = None
    pending_pit: bool = False  # True if the current lap started after a pit stop


@dataclass
class SCPeriod:
    """A safety car or VSC period."""
    start_lap: int
    end_lap: int | None = None
    is_vsc: bool = False


class LapTimeAccumulator:
    """Pure-data class that accumulates lap times from telemetry frames.

    Extracted from the window so it can be tested without Qt/Matplotlib.
    """

    def __init__(self) -> None:
        # driver_code -> list of CompletedLap
        self.completed_laps: dict[str, list[CompletedLap]] = {}
        # driver_code -> _DriverState
        self._driver_states: dict[str, _DriverState] = {}
        # Safety car / VSC periods
        self.sc_periods: list[SCPeriod] = []
        self._last_track_status: str = "GREEN"
        self._current_sc: SCPeriod | None = None

    def process_frame(self, data: dict) -> None:
        """Process one telemetry frame and update internal state."""
        frame = data.get("frame")
        if not frame:
            return

        session_t = float(frame.get("t", 0))
        drivers = frame.get("drivers", {})
        track_status = data.get("track_status", "GREEN")
        current_leader_lap = frame.get("lap")

        # Update SC tracking
        self._update_sc_tracking(track_status, current_leader_lap)

        for code, driver in drivers.items():
            self._process_driver(code, driver, session_t)

    def _process_driver(self, code: str, driver: dict, session_t: float) -> None:
        """Process a single driver's data from a frame."""
        lap = driver.get("lap")
        compound = driver.get("tyre")
        if lap is None:
            return

        # Ensure state exists
        if code not in self._driver_states:
            self._driver_states[code] = _DriverState()
        if code not in self.completed_laps:
            self.completed_laps[code] = []

        state = self._driver_states[code]

        if state.current_lap is None:
            # First frame for this driver — initialize
            state.current_lap = lap
            state.lap_start_t = session_t
            state.last_compound = compound
            return

        if lap > state.current_lap:
            # Lap transition detected — compute lap time for the lap that just ended
            completed_lap_num = state.current_lap
            if state.lap_start_t is not None:
                lap_time = session_t - state.lap_start_t

                # Skip lap 1 (formation/out lap) and outliers
                if completed_lap_num >= 2 and lap_time <= _OUTLIER_THRESHOLD_S:
                    self.completed_laps[code].append(CompletedLap(
                        lap_num=completed_lap_num,
                        lap_time_s=lap_time,
                        compound_int=state.last_compound if state.last_compound is not None else 0,
                        is_pit_stop=state.pending_pit,
                    ))

            # Detect pit stop for the NEW lap: compound changed at boundary
            is_pit_next = False
            if state.last_compound is not None and compound is not None:
                if compound != state.last_compound:
                    is_pit_next = True

            # Reset for the new lap
            state.current_lap = lap
            state.lap_start_t = session_t
            state.last_compound = compound
            state.pending_pit = is_pit_next
        else:
            # Same lap — update compound if it changed mid-lap (shouldn't normally happen)
            if compound is not None:
                state.last_compound = compound

    def _update_sc_tracking(self, track_status: str, leader_lap: int | None) -> None:
        """Track safety car and VSC periods."""
        is_sc = track_status == "4"
        is_vsc = track_status in ("6", "7")
        was_sc_or_vsc = self._last_track_status in ("4", "6", "7")

        lap = leader_lap if leader_lap is not None else 1

        if (is_sc or is_vsc) and not was_sc_or_vsc:
            # SC/VSC started
            self._current_sc = SCPeriod(
                start_lap=lap,
                is_vsc=is_vsc,
            )
        elif not is_sc and not is_vsc and was_sc_or_vsc:
            # SC/VSC ended
            if self._current_sc is not None:
                self._current_sc.end_lap = lap
                self.sc_periods.append(self._current_sc)
                self._current_sc = None

        self._last_track_status = track_status

    def get_pit_stop_laps(self, code: str) -> list[int]:
        """Return lap numbers where driver pitted."""
        laps = self.completed_laps.get(code, [])
        return [lap.lap_num for lap in laps if lap.is_pit_stop]


class LapTimeEvolutionWindow(PitWallWindow):
    """Pit wall insight showing lap time evolution for multiple drivers."""

    def __init__(self) -> None:
        self._known_drivers: list[str] = []
        self.accumulator = LapTimeAccumulator()
        self._driver_color_map: dict[str, str] = {}
        self._color_index = 0
        super().__init__()
        self.setWindowTitle("F1 Race Replay - Lap Time Evolution")
        self.setGeometry(100, 100, 1200, 700)

    # ── UI setup ──────────────────────────────────────────────────────────

    def setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setSpacing(6)
        root_layout.setContentsMargins(10, 10, 10, 10)

        # Splitter: driver list (left) | chart (right)
        splitter = QSplitter(Qt.Horizontal)

        # Driver list (checkable, multi-select)
        self.driver_list = QListWidget()
        self.driver_list.setMaximumWidth(150)
        self.driver_list.setFont(QFont("Arial", 11))
        self.driver_list.itemChanged.connect(self._on_driver_selection_changed)
        splitter.addWidget(self.driver_list)

        # Matplotlib figure
        self._fig, self._ax = plt.subplots(figsize=(10, 6), facecolor=_BG)
        self._ax.set_facecolor(_BG)
        self._ax.set_xlabel("Lap Number", color="#F0F0F0", fontsize=10)
        self._ax.set_ylabel("Lap Time (s)", color="#F0F0F0", fontsize=10)
        self._ax.set_title("Lap Time Evolution", color="#F0F0F0", fontsize=13, fontweight="bold")
        self._ax.tick_params(colors="#F0F0F0")
        for spine in self._ax.spines.values():
            spine.set_edgecolor("#555555")

        self._canvas = FigureCanvas(self._fig)
        splitter.addWidget(self._canvas)

        # Set initial splitter sizes (150px for list, rest for chart)
        splitter.setSizes([150, 1050])

        root_layout.addWidget(splitter)

    # ── Driver list management ────────────────────────────────────────────

    def _refresh_driver_list(self, drivers: dict) -> None:
        incoming = sorted(drivers.keys())
        if incoming == self._known_drivers:
            return

        # Block signals while updating
        self.driver_list.blockSignals(True)

        # Remember checked drivers
        checked = set()
        for i in range(self.driver_list.count()):
            item = self.driver_list.item(i)
            if item and item.checkState() == Qt.Checked:
                checked.add(item.text())

        self.driver_list.clear()
        for code in incoming:
            item = QListWidgetItem(code)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if code in checked else Qt.Unchecked)
            self.driver_list.addItem(item)

        self.driver_list.blockSignals(False)
        self._known_drivers = incoming

    def _get_selected_drivers(self) -> list[str]:
        selected = []
        for i in range(self.driver_list.count()):
            item = self.driver_list.item(i)
            if item and item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def _on_driver_selection_changed(self, item: QListWidgetItem) -> None:
        self._redraw()

    def _get_driver_color(self, code: str) -> str:
        if code not in self._driver_color_map:
            self._driver_color_map[code] = DRIVER_LINE_COLORS[
                self._color_index % len(DRIVER_LINE_COLORS)
            ]
            self._color_index += 1
        return self._driver_color_map[code]

    # ── Chart rendering ───────────────────────────────────────────────────

    def _redraw(self) -> None:
        self._ax.clear()
        self._ax.set_facecolor(_BG)
        self._ax.set_xlabel("Lap Number", color="#F0F0F0", fontsize=10)
        self._ax.set_ylabel("Lap Time (s)", color="#F0F0F0", fontsize=10)
        self._ax.set_title("Lap Time Evolution", color="#F0F0F0", fontsize=13, fontweight="bold")
        self._ax.tick_params(colors="#F0F0F0")
        for spine in self._ax.spines.values():
            spine.set_edgecolor("#555555")

        selected = self._get_selected_drivers()
        if not selected:
            self._canvas.draw_idle()
            return

        all_times: list[float] = []
        max_lap = 1

        # Draw SC/VSC shading first (behind data)
        for period in self.accumulator.sc_periods:
            end = period.end_lap if period.end_lap is not None else max_lap
            color = "#FF8C00" if period.is_vsc else "#FFD700"
            alpha = 0.2
            self._ax.axvspan(period.start_lap - 0.5, end + 0.5,
                             color=color, alpha=alpha, zorder=0)

        # Also shade any ongoing SC/VSC
        if self.accumulator._current_sc is not None:
            sc = self.accumulator._current_sc
            color = "#FF8C00" if sc.is_vsc else "#FFD700"
            self._ax.axvspan(sc.start_lap - 0.5, max_lap + 0.5,
                             color=color, alpha=0.2, zorder=0)

        # Draw each selected driver
        for code in selected:
            laps = self.accumulator.completed_laps.get(code, [])
            if not laps:
                continue

            lap_nums = [lap.lap_num for lap in laps]
            lap_times = [lap.lap_time_s for lap in laps]
            compounds = [lap.compound_int for lap in laps]

            all_times.extend(lap_times)
            if lap_nums:
                max_lap = max(max_lap, max(lap_nums))

            line_color = self._get_driver_color(code)

            # Connect with thin line
            self._ax.plot(lap_nums, lap_times, color=line_color,
                         linewidth=1.0, alpha=0.6, zorder=1, label=code)

            # Scatter colored by compound
            for i, (ln, lt, comp) in enumerate(zip(lap_nums, lap_times, compounds)):
                marker_color = COMPOUND_COLORS.get(comp, "#CCCCCC")
                self._ax.scatter(ln, lt, color=marker_color, s=30,
                                edgecolors=line_color, linewidths=0.5, zorder=2)

            # Mark pit stop laps with vertical dashed gray line
            pit_laps = self.accumulator.get_pit_stop_laps(code)
            for pl in pit_laps:
                self._ax.axvline(x=pl, color="#888888", linestyle="--",
                                linewidth=0.8, alpha=0.5, zorder=0)

        # Re-draw SC shading with correct max_lap for ongoing periods
        # (Already drawn above with initial max_lap, update if needed)

        # Axes scaling
        if all_times:
            y_min = min(all_times) - 2
            y_max = max(all_times) + 2
            self._ax.set_ylim(y_min, y_max)

        self._ax.set_xlim(1, max(max_lap, 2))

        # Legend
        if selected:
            self._ax.legend(loc="upper right", fontsize=8,
                           facecolor="#333333", edgecolor="#555555",
                           labelcolor="#F0F0F0")

        self._canvas.draw_idle()

    # ── PitWallWindow overrides ───────────────────────────────────────────

    def on_telemetry_data(self, data: dict) -> None:
        if "frame" not in data or not data["frame"]:
            return

        drivers = data["frame"].get("drivers", {})
        if not drivers:
            return

        self._refresh_driver_list(drivers)
        self.accumulator.process_frame(data)
        self._redraw()

    def on_connection_status_changed(self, status: str) -> None:
        if status != "Connected":
            pass  # Keep accumulated data visible


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Lap Time Evolution")
    window = LapTimeEvolutionWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
