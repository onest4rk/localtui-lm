from __future__ import annotations

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w


CONFIG_DIR_NAMES = [
    Path.cwd(),
    Path.home() / ".config" / "localtui-lm",
    Path.home() / ".localtui-lm",
]

CONFIG_FILENAME = "config.toml"


@dataclass
class ModelConfig:
    path: str = "data/models/model.gguf"
    context_size: int = 2048
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    n_gpu_layers: int = 0
    n_threads: Optional[int] = None
    verbose: bool = False


@dataclass
class UIConfig:
    theme: str = "default"
    show_token_count: bool = True
    show_speed: bool = True
    markdown_render: bool = True


@dataclass
class StorageConfig:
    save_dir: str = "data/sessions"
    auto_save: bool = True
    max_history: int = 100


@dataclass
class PromptConfig:
    default_preset: str = "general"
    custom_presets_file: Optional[str] = None


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        cfg = cls()

        if path is not None:
            config_path = Path(path)
            if config_path.exists():
                cfg._merge_toml(config_path)
            else:
                print(f"Warning: config file not found at {path}", file=sys.stderr)
            return cfg

        for base_dir in CONFIG_DIR_NAMES:
            config_path = base_dir / CONFIG_FILENAME
            if config_path.exists():
                cfg._merge_toml(config_path)
                return cfg

        defaults_path = Path(__file__).parent / "defaults.toml"
        if defaults_path.exists():
            cfg._merge_toml(defaults_path)

        return cfg

    def _merge_toml(self, path: Path) -> None:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        if "model" in data:
            for key, val in data["model"].items():
                if hasattr(self.model, key):
                    setattr(self.model, key, val)

        if "ui" in data:
            for key, val in data["ui"].items():
                if hasattr(self.ui, key):
                    setattr(self.ui, key, val)

        if "storage" in data:
            for key, val in data["storage"].items():
                if hasattr(self.storage, key):
                    setattr(self.storage, key, val)

        if "prompt" in data:
            for key, val in data["prompt"].items():
                if hasattr(self.prompt, key):
                    setattr(self.prompt, key, val)

    def save(self, path: Optional[str] = None) -> None:
        target = Path(path) if path else self._discover_save_path()
        target.parent.mkdir(parents=True, exist_ok=True)

        def _clean(d: dict) -> dict:
            return {k: v for k, v in d.items() if v is not None}

        data = {
            "model": _clean(self.model.__dict__),
            "ui": _clean(self.ui.__dict__),
            "storage": _clean(self.storage.__dict__),
            "prompt": _clean(self.prompt.__dict__),
        }

        with open(target, "wb") as f:
            tomli_w.dump(data, f)

    def _discover_save_path(self) -> Path:
        for base_dir in CONFIG_DIR_NAMES:
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
                return base_dir / CONFIG_FILENAME
            except OSError:
                continue
        return Path.cwd() / CONFIG_FILENAME

    def validate(self) -> list[str]:
        errors: list[str] = []

        model_path = Path(self.model.path)
        if not model_path.exists():
            errors.append(
                f"Model file not found: {self.model.path}. "
                "Run `python scripts/download_model.py` to download a model, "
                "or update the `model.path` in config.toml."
            )

        if self.model.context_size < 256:
            errors.append("context_size must be at least 256")
        if self.model.max_tokens < 1:
            errors.append("max_tokens must be at least 1")
        if not (0.0 < self.model.temperature <= 2.0):
            errors.append("temperature must be between 0.0 and 2.0")
        if not (0.0 < self.model.top_p <= 1.0):
            errors.append("top_p must be between 0.0 and 1.0")

        if self.prompt.default_preset not in ("general", "coding", "writing", "tutor") and not self.prompt.custom_presets_file:
            errors.append(
                f"Unknown default preset '{self.prompt.default_preset}'. "
                "Built-in presets: general, coding, writing, tutor."
            )

        return errors
