import pytest
import pandas as pd

from src.bayesian_tyre_model import (
    TyreCategory, TrackCondition, TyreProfile, StateSpaceConfig,
    BayesianTyreDegradationModel,
)


# ── Task 1: Dataclass validation and config defaults ──

class TestTyreProfile:
    def test_valid_creation(self):
        profile = TyreProfile(
            name="TEST", category=TyreCategory.SLICK,
            degradation_rate=0.05, reset_pace=68.5,
            warmup_laps=1, max_analysis_laps=10, max_degradation=2.0,
        )
        assert profile.name == "TEST"
        assert profile.category == TyreCategory.SLICK
        assert profile.degradation_rate == 0.05

    def test_negative_degradation_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            TyreProfile(
                name="BAD", category=TyreCategory.SLICK,
                degradation_rate=-0.1, reset_pace=68.5,
                warmup_laps=1, max_analysis_laps=None, max_degradation=2.0,
            )

    def test_negative_warmup_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            TyreProfile(
                name="BAD", category=TyreCategory.SLICK,
                degradation_rate=0.05, reset_pace=68.5,
                warmup_laps=-1, max_analysis_laps=None, max_degradation=2.0,
            )


class TestStateSpaceConfig:
    def test_defaults(self):
        config = StateSpaceConfig()
        assert config.sigma_epsilon == 0.3
        assert config.sigma_eta == 0.1
        assert config.fuel_effect_prior == 0.032
        assert config.starting_fuel == 110.0
        assert config.fuel_burn_rate == 1.6
        assert config.enable_warmup is True
        assert config.enable_track_abrasion is True

    def test_default_mismatch_penalties(self):
        config = StateSpaceConfig()
        penalties = config.mismatch_penalties
        # All 9 combinations present
        assert len(penalties) == 9

        # Matching conditions have 0 penalty
        assert penalties[(TyreCategory.SLICK, TrackCondition.DRY)] == 0.0
        assert penalties[(TyreCategory.INTER, TrackCondition.DAMP)] == 0.0
        assert penalties[(TyreCategory.WET, TrackCondition.WET)] == 0.0

        # Mismatches have positive penalty
        assert penalties[(TyreCategory.SLICK, TrackCondition.WET)] == 8.0
        assert penalties[(TyreCategory.WET, TrackCondition.DRY)] == 4.0

    def test_custom_values(self):
        config = StateSpaceConfig(sigma_epsilon=0.5, fuel_burn_rate=2.0)
        assert config.sigma_epsilon == 0.5
        assert config.fuel_burn_rate == 2.0


class TestEnums:
    def test_tyre_category_values(self):
        assert TyreCategory.SLICK.value == "SLICK"
        assert TyreCategory.INTER.value == "INTER"
        assert TyreCategory.WET.value == "WET"

    def test_track_condition_values(self):
        assert TrackCondition.DRY.value == "DRY"
        assert TrackCondition.DAMP.value == "DAMP"
        assert TrackCondition.WET.value == "WET"


# ── Task 2: Model behavioral property tests ──

def _make_laps_df(n_laps=20, compound="SOFT", driver="VER", stint=1,
                  base_time=90.0, degradation_per_lap=0.15,
                  track_condition="DRY"):
    """Helper to create a realistic laps DataFrame for the model."""
    laps = []
    for i in range(1, n_laps + 1):
        lap_time_s = base_time + i * degradation_per_lap
        laps.append({
            "Driver": driver,
            "LapNumber": i + 1,  # Start from lap 2 (lap 1 filtered by _prepare_data)
            "Compound": compound,
            "Stint": stint,
            "TyreLife": i,
            "LapTime": pd.Timedelta(seconds=lap_time_s),
            "PitInTime": pd.NaT,
            "PitOutTime": pd.NaT,
            "TrackCondition": track_condition,
        })
    return pd.DataFrame(laps)


class TestBayesianTyreDegradationModel:
    def test_model_initializes(self):
        model = BayesianTyreDegradationModel()
        assert "SOFT" in model.tyre_profiles
        assert "MEDIUM" in model.tyre_profiles
        assert "HARD" in model.tyre_profiles
        assert "INTERMEDIATE" in model.tyre_profiles
        assert "WET" in model.tyre_profiles

    def test_health_between_0_and_100(self):
        model = BayesianTyreDegradationModel()
        laps_df = _make_laps_df(n_laps=30, compound="SOFT")
        model.fit(laps_df)

        for lap in range(2, 32):
            health_info = model.get_health("VER", lap, laps_df)
            if health_info is not None:
                assert 0 <= health_info["health"] <= 100, \
                    f"Health {health_info['health']} out of bounds at lap {lap}"

    def test_health_decreases_over_stint(self):
        model = BayesianTyreDegradationModel()
        laps_df = _make_laps_df(n_laps=25, compound="SOFT")
        model.fit(laps_df)

        early_health = model.get_health("VER", 5, laps_df)
        late_health = model.get_health("VER", 20, laps_df)

        assert early_health is not None
        assert late_health is not None
        assert early_health["health"] > late_health["health"], \
            f"Health should decrease: early={early_health['health']}, late={late_health['health']}"

    def test_fresh_tyres_start_healthy(self):
        model = BayesianTyreDegradationModel()
        laps_df = _make_laps_df(n_laps=5, compound="SOFT")
        model.fit(laps_df)

        health_info = model.get_health("VER", 2, laps_df)
        assert health_info is not None
        assert health_info["health"] > 80, \
            f"Fresh tyres should be healthy, got {health_info['health']}"

    def test_mismatch_penalty_reduces_health(self):
        model = BayesianTyreDegradationModel()

        # SOFT on DRY (matching)
        dry_laps = _make_laps_df(n_laps=15, compound="SOFT", track_condition="DRY")
        model.fit(dry_laps)
        dry_health = model.get_health("VER", 10, dry_laps, track_condition="DRY")

        # SOFT on WET (mismatch — penalty 8.0)
        wet_health = model.get_health("VER", 10, dry_laps, track_condition="WET")

        assert dry_health is not None
        assert wet_health is not None
        assert dry_health["health"] > wet_health["health"], \
            f"Mismatch should reduce health: dry={dry_health['health']}, wet={wet_health['health']}"

    def test_handles_single_lap(self):
        model = BayesianTyreDegradationModel()
        laps_df = _make_laps_df(n_laps=1, compound="MEDIUM")
        model.fit(laps_df)

        health_info = model.get_health("VER", 2, laps_df)
        assert health_info is not None
        assert 0 <= health_info["health"] <= 100

    def test_get_degradation_rate(self):
        model = BayesianTyreDegradationModel()
        # Before fitting, returns profile prior
        assert model.get_degradation_rate("SOFT") == 0.05
        assert model.get_degradation_rate("MEDIUM") == 0.03
        assert model.get_degradation_rate("HARD") == 0.01
        # Unknown compound returns default
        assert model.get_degradation_rate("UNKNOWN") == 0.05

    def test_predict_requires_fit(self):
        model = BayesianTyreDegradationModel()
        laps_df = _make_laps_df(n_laps=5)
        with pytest.raises(RuntimeError, match="fitted"):
            model.predict_next_lap("VER", 3, laps_df)
