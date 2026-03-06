import pytest
from unittest.mock import patch

from src.lib.settings import SettingsManager, get_settings


@pytest.fixture
def isolated_settings(tmp_path):
    """SettingsManager using isolated temp file."""
    settings_file = tmp_path / "test_settings.json"
    with patch.object(SettingsManager, "_get_settings_file_path", return_value=settings_file):
        SettingsManager._instance = None
        manager = SettingsManager()
        yield manager, settings_file
        SettingsManager._instance = None


class TestSettingsManager:
    def test_default_values(self, isolated_settings):
        manager, _ = isolated_settings
        assert manager.cache_location == ".fastf1-cache"
        assert manager.computed_data_location == "computed_data"

    def test_get_set(self, isolated_settings):
        manager, _ = isolated_settings
        manager.set("key", "value")
        assert manager.get("key") == "value"

    def test_save_load_roundtrip(self, isolated_settings):
        manager, settings_file = isolated_settings
        manager.set("custom_key", "custom_value")
        manager.cache_location = "/new/cache/path"
        manager.save()

        # Reset singleton and reload
        SettingsManager._instance = None
        with patch.object(SettingsManager, "_get_settings_file_path", return_value=settings_file):
            new_manager = SettingsManager()
            assert new_manager.get("custom_key") == "custom_value"
            assert new_manager.cache_location == "/new/cache/path"

    def test_property_accessors(self, isolated_settings):
        manager, _ = isolated_settings
        assert manager.cache_location == ".fastf1-cache"
        assert manager.computed_data_location == "computed_data"

        manager.cache_location = "/tmp/new-cache"
        assert manager.cache_location == "/tmp/new-cache"

        manager.computed_data_location = "/tmp/new-data"
        assert manager.computed_data_location == "/tmp/new-data"

    def test_reset_to_defaults(self, isolated_settings):
        manager, _ = isolated_settings
        manager.cache_location = "/custom/path"
        manager.set("extra_key", "extra_value")
        manager.reset_to_defaults()

        assert manager.cache_location == ".fastf1-cache"
        assert manager.computed_data_location == "computed_data"
        # Extra keys are cleared since reset replaces the dict
        assert manager.get("extra_key") is None

    def test_singleton_pattern(self, isolated_settings):
        manager, settings_file = isolated_settings
        with patch.object(SettingsManager, "_get_settings_file_path", return_value=settings_file):
            second = get_settings()
            assert second is manager

    def test_corrupted_settings_file(self, tmp_path):
        settings_file = tmp_path / "corrupt_settings.json"
        settings_file.write_text("NOT VALID JSON {{{")

        with patch.object(SettingsManager, "_get_settings_file_path", return_value=settings_file):
            SettingsManager._instance = None
            manager = SettingsManager()
            # Should fall back to defaults without crashing
            assert manager.cache_location == ".fastf1-cache"

    def test_get_with_default(self, isolated_settings):
        manager, _ = isolated_settings
        assert manager.get("nonexistent", "fallback") == "fallback"
