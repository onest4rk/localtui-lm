from __future__ import annotations

import re
from typing import Optional


def format_speed(tokens_per_second: float) -> str:
    if tokens_per_second < 1:
        return f"{tokens_per_second:.1f} tok/s"
    return f"{tokens_per_second:.1f} tok/s"


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def count_tokens(text: str) -> int:
    return len(text.split())


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def truncate_text(text: str, max_length: int = 100) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_markdown_basic(text: str) -> str:
    code_block = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
    text = code_block.sub(lambda m: m.group(2).strip(), text)

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"^###\s+(.*)$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.*)$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.*)$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "  * ", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "  ", text, flags=re.MULTILINE)

    return text.strip()


def format_context_usage(current: int, max: int) -> str:
    pct = (current / max) * 100 if max > 0 else 0
    bar_len = 10
    filled = int(bar_len * pct / 100)
    bar = "#" * filled + "-" * (bar_len - filled)
    return f"[{bar}] {current}/{max} ({pct:.0f}%)"
