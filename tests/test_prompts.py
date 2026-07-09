from __future__ import annotations

import json
import os
import tempfile

from src.prompts.presets import get_preset, list_presets, BUILTIN_PRESETS


class TestPresets:
    def test_builtin_presets_exist(self):
        assert "general" in BUILTIN_PRESETS
        assert "coding" in BUILTIN_PRESETS
        assert "writing" in BUILTIN_PRESETS
        assert "tutor" in BUILTIN_PRESETS

    def test_get_preset_returns_string(self):
        for name in BUILTIN_PRESETS:
            preset = get_preset(name)
            assert preset is not None
            assert isinstance(preset, str)
            assert len(preset) > 10

    def test_get_unknown_preset_returns_none(self):
        assert get_preset("nonexistent") is None

    def test_list_presets_includes_all_builtin(self):
        presets = list_presets()
        for name in BUILTIN_PRESETS:
            assert name in presets

    def test_custom_presets_from_json(self):
        custom = {
            "custom_help": "You are a helpful assistant specialized in customer support.",
            "custom_debug": "You are a debugging assistant. Help find bugs.",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(custom, f)
            tmp_path = f.name

        try:
            presets = list_presets(tmp_path)
            assert "custom_help" in presets
            assert "custom_debug" in presets
            assert "general" in presets

            preset = get_preset("custom_help", tmp_path)
            assert preset == custom["custom_help"]
        finally:
            os.unlink(tmp_path)

    def test_builtin_presets_are_distinct(self):
        values = list(BUILTIN_PRESETS.values())
        assert len(set(values)) == len(values), "Built-in presets should be distinct"

    def test_coding_preset_mentions_code(self):
        preset = get_preset("coding")
        assert preset is not None
        assert any(word in preset.lower() for word in ["code", "software", "engineer"])

    def test_tutor_preset_mentions_teaching(self):
        preset = get_preset("tutor")
        assert preset is not None
        assert any(word in preset.lower() for word in ["teach", "tutor", "explain", "step"])
