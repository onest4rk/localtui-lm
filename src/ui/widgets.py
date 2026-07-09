from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.table import Table


class StatusBar(Static):
    model_name = reactive("")
    status = reactive("idle")
    tokens_per_second = reactive(0.0)
    tokens_generated = reactive(0)
    context_used = reactive(0)
    context_max = reactive(2048)

    def render(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)

        dot = {"loading": "[#ffa500]●[/]", "ready": "[#00ff88]●[/]", "error": "[#ff4444]●[/]", "generating": "[#44ddff]●[/]", "idle": "[#666666]●[/]"}
        dot_char = dot.get(self.status, "[#666666]●[/]")

        model_info = f"{dot_char} {self.model_name or 'N/A'}"
        status_info = f"{self.status}"
        speed_info = f"{self.tokens_per_second:.1f} tok/s" if self.tokens_per_second > 0 else "-- tok/s"
        tokens_info = f"tokens: {self.tokens_generated}"
        ctx_pct = (self.context_used / self.context_max * 100) if self.context_max > 0 else 0
        ctx_info = f"ctx: {self.context_used}/{self.context_max} ({ctx_pct:.0f}%)"

        grid.add_row(model_info, status_info, speed_info)
        grid.add_row(tokens_info, ctx_info, "")

        return Panel(grid, title="status", border_style="#444444")


class ChatMessage(Static):
    def __init__(self, role: str, content: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.content = content

    def render(self) -> Panel:
        label = "you" if self.role == "user" else "assistant"
        border_style = "#446644" if self.role == "user" else "#444466"
        return Panel(self.content, title=label, border_style=border_style)


class SessionList(Static):
    sessions = reactive([])

    def render(self) -> Panel:
        if not self.sessions:
            return Panel("no saved sessions", title="sessions", border_style="#333333")

        table = Table.grid(expand=True)
        for s in self.sessions:
            title = s.get("title", "Untitled")
            count = s.get("message_count", 0)
            table.add_row(f"  {title} ({count})")

        return Panel(table, title="sessions", border_style="#444444")


class ModelInfoPanel(Static):
    loaded = reactive(False)
    load_time = reactive(0.0)
    model_path = reactive("")
    loading_progress = reactive("")

    def render(self) -> Panel:
        if not self.loaded:
            dots = self.loading_progress or "..."
            return Panel(
                f"loading{dots}\n\n{self.model_path}",
                title="model",
                border_style="#666644",
            )

        lines = [
            f"loaded in {self.load_time:.1f}s",
            f"path: {self.model_path}",
        ]
        return Panel("\n".join(lines), title="model", border_style="#446644")


class PresetSelector(Static):
    current_preset = reactive("general")
    available_presets = reactive([])

    def render(self) -> Text:
        presets = ", ".join(self.available_presets) if self.available_presets else "general, coding, writing, tutor"
        return Text(f"preset: {self.current_preset}  ({presets})")
