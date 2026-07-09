from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout


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

        model_info = f"[bold]Model:[/] {self.model_name or 'N/A'}"
        status_info = f"[bold]Status:[/] {self.status}"
        speed_info = f"[bold]Speed:[/] {self.tokens_per_second:.1f} tok/s" if self.tokens_per_second > 0 else "[bold]Speed:[/] --"
        tokens_info = f"[bold]Tokens:[/] {self.tokens_generated}"
        ctx_pct = (self.context_used / self.context_max * 100) if self.context_max > 0 else 0
        ctx_info = f"[bold]Context:[/] {self.context_used}/{self.context_max} ({ctx_pct:.0f}%)"

        grid.add_row(model_info, status_info, speed_info)
        grid.add_row(tokens_info, ctx_info, "")

        return Panel(grid, title="System Status", border_style="blue")


class ChatMessage(Static):
    def __init__(self, role: str, content: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.content = content

    def render(self) -> Panel:
        label = "You" if self.role == "user" else "Assistant"
        border_style = "green" if self.role == "user" else "blue"
        return Panel(self.content, title=label, border_style=border_style)


class SessionList(Static):
    sessions = reactive([])

    def render(self) -> Panel:
        if not self.sessions:
            return Panel("No saved sessions", title="Sessions", border_style="dim")

        table = Table.grid(expand=True)
        for s in self.sessions:
            title = s.get("title", "Untitled")
            count = s.get("message_count", 0)
            table.add_row(f"  {title} ({count} msgs)")

        return Panel(table, title="Sessions", border_style="green")


class ModelInfoPanel(Static):
    loaded = reactive(False)
    load_time = reactive(0.0)
    model_path = reactive("")

    def render(self) -> Panel:
        if not self.loaded:
            return Panel("Model not loaded", title="Model Info", border_style="yellow")

        lines = [
            f"Path: {self.model_path}",
            f"Load time: {self.load_time:.1f}s",
            "Status: Loaded",
        ]
        return Panel("\n".join(lines), title="Model Info", border_style="green")


class PresetSelector(Static):
    current_preset = reactive("general")
    available_presets = reactive([])

    def render(self) -> Text:
        presets = ", ".join(self.available_presets) if self.available_presets else "general, coding, writing, tutor"
        return Text(f"Preset: [bold]{self.current_preset}[/]  ({presets})")
