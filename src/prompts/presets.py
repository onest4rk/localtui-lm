from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

BUILTIN_PRESETS: dict[str, str] = {
    "general": (
        "You are a helpful, harmless, and honest AI assistant. "
        "Answer the user's questions clearly and concisely."
    ),
    "coding": (
        "You are an expert software engineer. Help the user write clean, "
        "efficient, and well-documented code. Provide examples where helpful. "
        "Focus on best practices and explain your reasoning."
    ),
    "writing": (
        "You are a professional writing assistant. Help the user improve "
        "their writing with suggestions on grammar, style, clarity, and "
        "structure. Adapt your tone to match the user's needs."
    ),
    "tutor": (
        "You are a patient and knowledgeable tutor. Explain concepts "
        "step by step, check for understanding, and use examples to "
        "illustrate ideas. Adapt your explanation to the user's level."
    ),
}


def get_preset(name: str, custom_file: Optional[str] = None) -> Optional[str]:
    if name in BUILTIN_PRESETS:
        return BUILTIN_PRESETS[name]

    if custom_file:
        custom = _load_custom_presets(custom_file)
        if name in custom:
            return custom[name]

    return None


def list_presets(custom_file: Optional[str] = None) -> dict[str, str]:
    presets = dict(BUILTIN_PRESETS)

    if custom_file:
        custom = _load_custom_presets(custom_file)
        presets.update(custom)

    return presets


def _load_custom_presets(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}

    try:
        with open(p, "r", encoding="utf-8") as f:
            if p.suffix == ".json":
                return json.load(f)
            else:
                data = f.read()
                result: dict[str, str] = {}
                for line in data.strip().split("\n\n"):
                    if ":" in line:
                        name, _, content = line.partition(":")
                        result[name.strip().lower()] = content.strip()
                return result
    except (json.JSONDecodeError, OSError):
        return {}
