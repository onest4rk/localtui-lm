from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from src.config.config import Config


class TestConfig:
    def test_default_values(self):
        cfg = Config()
        assert cfg.model.context_size == 2048
        assert cfg.model.max_tokens == 512
        assert cfg.model.temperature == 0.7
        assert cfg.model.top_p == 0.9
        assert cfg.model.repeat_penalty == 1.1
        assert cfg.model.n_gpu_layers == 0
        assert cfg.model.verbose is False
        assert cfg.storage.save_dir == "data/sessions"
        assert cfg.storage.auto_save is True
        assert cfg.prompt.default_preset == "general"

    def test_load_from_toml(self):
        toml_content = """
[model]
context_size = 4096
temperature = 0.5
max_tokens = 1024

[ui]
theme = "dark"

[storage]
auto_save = false
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            tmp_path = f.name

        try:
            cfg = Config.load(tmp_path)
            assert cfg.model.context_size == 4096
            assert cfg.model.temperature == 0.5
            assert cfg.model.max_tokens == 1024
            assert cfg.ui.theme == "dark"
            assert cfg.storage.auto_save is False
        finally:
            os.unlink(tmp_path)

    def test_validate_missing_model(self):
        cfg = Config()
        cfg.model.path = "/nonexistent/path/model.gguf"
        errors = cfg.validate()
        assert len(errors) > 0
        assert any("Model file not found" in e for e in errors)

    def test_validate_context_size(self):
        cfg = Config()
        cfg.model.context_size = 64
        errors = cfg.validate()
        assert any("context_size" in e for e in errors)

    def test_validate_temperature_range(self):
        cfg = Config()
        cfg.model.temperature = 3.0
        errors = cfg.validate()
        assert any("temperature" in e for e in errors)

    def test_save_and_reload(self):
        cfg = Config()
        cfg.model.context_size = 4096
        cfg.model.temperature = 0.3
        cfg.storage.save_dir = "/tmp/test_sessions"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            tmp_path = f.name

        try:
            cfg.save(tmp_path)
            loaded = Config.load(tmp_path)
            assert loaded.model.context_size == 4096
            assert loaded.model.temperature == 0.3
            assert loaded.storage.save_dir == "/tmp/test_sessions"
        finally:
            os.unlink(tmp_path)

    def test_custom_presets_file_config(self):
        cfg = Config()
        assert cfg.prompt.custom_presets_file is None
        cfg.prompt.custom_presets_file = "/tmp/custom_presets.json"
        assert cfg.prompt.custom_presets_file == "/tmp/custom_presets.json"
