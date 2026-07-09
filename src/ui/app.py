from __future__ import annotations

import asyncio
import itertools
import threading
import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Input, Static, RichLog, Button, Label, ListView, ListItem
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from config.config import Config
from llm.engine import LLMEngine
from storage.session import Session, SessionStore
from prompts.presets import get_preset, list_presets
from ui.widgets import StatusBar, ChatMessage, SessionList, ModelInfoPanel, PresetSelector


class PresetScreen(ModalScreen[str]):
    presets: dict[str, str]

    def __init__(self, presets: dict[str, str], current: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.presets = presets
        self.current = current

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Select a system prompt preset:", classes="title"),
            ListView(
                *[ListItem(Label(f"{'* ' if name == self.current else '  '}{name}")) for name in self.presets]
            ),
            Button("Cancel", variant="default", id="cancel"),
            classes="preset-screen",
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        label = event.item.children[0].renderable
        name = label.replace("* ", "").replace("  ", "").strip()
        self.dismiss(name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss("")


class SessionScreen(ModalScreen[Optional[str]]):
    def __init__(self, sessions: list[dict], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sessions = sessions

    def compose(self) -> ComposeResult:
        items = []
        for s in self._sessions:
            title = s.get("title", "Untitled")
            count = s.get("message_count", 0)
            sid = s.get("session_id", "")
            items.append(ListItem(Label(f"{title} ({count} msgs)"), id=sid))

        yield Container(
            Label("Saved sessions:", classes="title"),
            ListView(*items) if items else Label("No saved sessions."),
            Button("Cancel", variant="default", id="cancel"),
            classes="session-screen",
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)


class LocalLMApp(App):
    TITLE = "LocalTUI-LM"
    SUB_TITLE = "CPU-Only Local AI Assistant"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("ctrl+n", "new_session", "New"),
        Binding("ctrl+s", "save_session", "Save"),
        Binding("ctrl+o", "open_sessions", "Open"),
        Binding("ctrl+p", "select_preset", "Preset"),
        Binding("ctrl+e", "export_md", "Export"),
        Binding("escape", "focus_input", "Input"),
        Binding("/", "show_help", "Help"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        layout: horizontal;
        height: 100%;
    }

    #chat-column {
        width: 70%;
        height: 100%;
    }

    #sidebar {
        width: 30%;
        height: 100%;
        border-left: solid $primary;
    }

    #chat-history {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }

    #input-area {
        height: auto;
        min-height: 3;
        max-height: 8;
        border-top: solid $primary;
        padding: 0 1;
    }

    #prompt-input {
        width: 1fr;
    }

    #input-buttons {
        width: auto;
        height: 3;
    }

    #sidebar StatusBar {
        height: auto;
    }

    #sidebar ModelInfoPanel {
        height: auto;
    }

    #sidebar PresetSelector {
        height: 1;
        padding: 0 1;
    }

    #sidebar SessionList {
        height: 1fr;
    }

    .preset-screen, .session-screen {
        width: 50;
        height: 20;
        margin: 5 8;
        padding: 1;
        background: $surface;
        border: thick $primary;
    }

    .preset-screen > .title, .session-screen > .title {
        text-style: bold;
        padding: 0 1;
        margin-bottom: 1;
    }

    #help-popup {
        width: 60;
        height: auto;
        margin: 3 5;
        padding: 1;
        background: $surface;
        border: thick $primary;
    }
    """

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.engine = LLMEngine(config)
        self.session = Session()
        self.store = SessionStore(config.storage.save_dir)
        self._streaming = False
        self._spinner_active = False
        self._current_preset = config.prompt.default_preset

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Vertical(id="chat-column"):
                yield RichLog(id="chat-history", highlight=True, markup=True)
                with Horizontal(id="input-area"):
                    yield Input(placeholder="Type a message... (/help for commands)", id="prompt-input")
                    with Horizontal(id="input-buttons"):
                        yield Button("Send", variant="primary", id="send-btn")
                        yield Button("Clear", variant="default", id="clear-btn")
            with Vertical(id="sidebar"):
                yield StatusBar(id="status-bar")
                yield ModelInfoPanel(id="model-info")
                yield PresetSelector(id="preset-selector")
                yield SessionList(id="session-list")
        yield Footer()

    def on_mount(self) -> None:
        self._update_presets()
        self._update_sessions()
        self._show_welcome()
        self._load_model()
        self.query_one("#prompt-input", Input).focus()

    def _show_welcome(self) -> None:
        model_path = Path(self.config.model.path)
        if model_path.exists():
            welcome = Panel(
                "Welcome to LocalTUI-LM!\n\n"
                "Type a message to start chatting, or /help for commands.",
                title="Welcome",
                border_style="green",
            )
        else:
            welcome = Panel(
                "[bold yellow]No model found[/]\n\n"
                f"Expected at: {self.config.model.path}\n\n"
                "To download a default model:\n"
                "  [bold]python scripts/download_model.py[/]\n\n"
                "Or set a custom path in [bold]config.toml[/]\n\n"
                "Type [bold]/help[/] for available commands.",
                title="Welcome to LocalTUI-LM",
                border_style="yellow",
            )
        self._chat_history().write(welcome)

    def _update_presets(self) -> None:
        presets = list_presets(self.config.prompt.custom_presets_file)
        selector = self.query_one("#preset-selector", PresetSelector)
        selector.current_preset = self._current_preset
        selector.available_presets = list(presets.keys())

    def _update_sessions(self) -> None:
        sessions = self.store.list_sessions()[:10]
        self.query_one("#session-list", SessionList).sessions = sessions

    def _status(self) -> StatusBar:
        return self.query_one("#status-bar", StatusBar)

    def _chat_history(self) -> RichLog:
        return self.query_one("#chat-history", RichLog)

    def _load_model(self) -> None:
        info_panel = self.query_one("#model-info", ModelInfoPanel)
        status_bar = self._status()

        status_bar.status = "loading"
        status_bar.model_name = Path(self.config.model.path).name
        info_panel.model_path = self.config.model.path
        info_panel.loaded = False

        self._spinner_active = True
        self._animate_spinner(info_panel)

        def load_thread():
            try:
                self.engine.load()
                self._spinner_active = False
                self.call_from_thread(self._on_model_loaded)
            except Exception as e:
                self._spinner_active = False
                self.call_from_thread(self._on_model_error, str(e))

        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def _animate_spinner(self, panel: ModelInfoPanel) -> None:
        frames = itertools.cycle([".  ", ".. ", "...", " ..", "  .", "   "])
        def animate():
            while self._spinner_active:
                panel.loading_progress = next(frames)
                self.call_later(panel.refresh)
                time.sleep(0.3)
        thread = threading.Thread(target=animate, daemon=True)
        thread.start()

    def _on_model_loaded(self) -> None:
        info_panel = self.query_one("#model-info", ModelInfoPanel)
        info_panel.loaded = True
        info_panel.load_time = self.engine.load_time
        info_panel.model_path = self.config.model.path

        status_bar = self._status()
        status_bar.status = "ready"
        status_bar.context_max = self.config.model.context_size

        self._chat_history().write(Panel("Model loaded. Ready for chat.", border_style="green"))

    def _on_model_error(self, error: str) -> None:
        status_bar = self._status()
        status_bar.status = "error"
        self._chat_history().write(Panel(f"Error loading model: {error}", border_style="red"))

    def action_clear_chat(self) -> None:
        if self._streaming:
            return
        self._chat_history().clear()
        self.session = Session()
        self._chat_history().write(Panel("Chat cleared. Starting fresh.", border_style="yellow"))

    def action_new_session(self) -> None:
        if self._streaming:
            return
        if self.session.messages and self.config.storage.auto_save:
            self.store.save(self.session)
        self.session = Session()
        self._chat_history().clear()
        self._update_sessions()
        self._chat_history().write(Panel("New session started.", border_style="yellow"))

    def action_save_session(self) -> None:
        if not self.session.messages:
            self._chat_history().write(Panel("Nothing to save.", border_style="yellow"))
            return
        self.store.save(self.session)
        self._update_sessions()
        self._chat_history().write(Panel(f"Session saved: {self.session.title}", border_style="green"))

    def action_open_sessions(self) -> None:
        sessions = self.store.list_sessions()
        if not sessions:
            self._chat_history().write(Panel("No saved sessions found.", border_style="yellow"))
            return
        self.push_screen(SessionScreen(sessions), self._on_session_selected)

    def _on_session_selected(self, session_id: Optional[str]) -> None:
        if session_id is None:
            return
        if self.session.messages and self.config.storage.auto_save:
            self.store.save(self.session)
        loaded = self.store.load(session_id)
        if loaded:
            self.session = loaded
            self._chat_history().clear()
            for msg in loaded.messages:
                self._chat_history().write(ChatMessage(msg.role, msg.content))
            self._chat_history().write(Panel(f"Loaded session: {loaded.title}", border_style="green"))

    def action_select_preset(self) -> None:
        presets = list_presets(self.config.prompt.custom_presets_file)
        self.push_screen(PresetScreen(presets, self._current_preset), self._on_preset_selected)

    def _on_preset_selected(self, name: str) -> None:
        if name:
            self._current_preset = name
            self._update_presets()
            self._chat_history().write(Panel(f"System prompt preset changed to: {name}", border_style="blue"))

    def action_export_md(self) -> None:
        if not self.session.messages:
            self._chat_history().write(Panel("Nothing to export.", border_style="yellow"))
            return
        export_dir = Path.cwd() / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        path = export_dir / f"{self.session.session_id}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {self.session.title}\n\n")
            for msg in self.session.messages:
                f.write(f"## {msg.role}\n\n{msg.content}\n\n")
        self._chat_history().write(Panel(f"Exported to: {path}", border_style="green"))

    def action_focus_input(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    def action_show_help(self) -> None:
        help_text = Panel(
            "[bold]Keyboard Shortcuts[/]\n"
            "  Ctrl+C    Quit\n"
            "  Ctrl+L    Clear chat\n"
            "  Ctrl+N    New session\n"
            "  Ctrl+S    Save session\n"
            "  Ctrl+O    Open sessions\n"
            "  Ctrl+P    Select preset\n"
            "  Ctrl+E    Export to Markdown\n"
            "  Escape    Focus input\n"
            "\n"
            "[bold]Slash Commands[/]\n"
            "  /help        Show this help\n"
            "  /new         New session\n"
            "  /save        Save session\n"
            "  /clear       Clear chat\n"
            "  /config      Show config summary\n"
            "  /presets     List presets\n"
            "  /preset <n>  Switch preset\n"
            "  /download    Show download instructions\n"
            "  /export      Export to Markdown\n"
            "  /tokens      Show token stats",
            title="Help",
            border_style="blue",
        )
        self._chat_history().write(help_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            self._send_message()
        elif event.button.id == "clear-btn":
            self.action_clear_chat()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._send_message()

    def _send_message(self) -> None:
        if self._streaming:
            return

        input_widget = self.query_one("#prompt-input", Input)
        user_text = input_widget.value.strip()
        if not user_text:
            return

        input_widget.value = ""

        if user_text.startswith("/"):
            self._handle_slash_command(user_text)
            return

        if not self.engine.is_loaded:
            msg = (
                "[bold yellow]Model not loaded[/]\n\n"
                "The model file was not found at:\n"
                f"  [bold]{self.config.model.path}[/]\n\n"
                "To fix this:\n"
                "  1. Run: [bold]python scripts/download_model.py[/]\n"
                "  2. Or update the path in [bold]config.toml[/]\n"
                "  3. Or type [bold]/download[/] for instructions"
            )
            self._chat_history().write(Panel(msg, title="No Model Loaded", border_style="red"))
            return

        self.session.add_message("user", user_text)
        self._chat_history().write(ChatMessage("user", user_text))

        self._streaming = True
        self._status().status = "generating"

        def generate():
            try:
                system_prompt = get_preset(self._current_preset, self.config.prompt.custom_presets_file)

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                for msg in self.session.messages:
                    messages.append({"role": msg.role, "content": msg.content})

                prompt_text = self._build_prompt(messages)

                full_response = ""
                for token in self.engine.generate(
                    prompt=prompt_text,
                    stream=True,
                ):
                    full_response += token
                    self.call_from_thread(self._update_stream, full_response)

                self.call_from_thread(self._finish_stream, full_response)
            except Exception as e:
                self.call_from_thread(self._handle_stream_error, str(e))

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def _build_prompt(self, messages: list[dict]) -> str:
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"<|system|>\n{content}\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
        prompt += "<|assistant|>\n"
        return prompt

    def _update_stream(self, full_response: str) -> None:
        self._chat_history().clear()
        for msg in self.session.messages[:-1]:
            self._chat_history().write(ChatMessage(msg.role, msg.content))
        self._chat_history().write(ChatMessage("user", self.session.messages[-1].content))
        self._chat_history().write(ChatMessage("assistant", full_response + "~"))

    def _finish_stream(self, full_response: str) -> None:
        self._streaming = False
        self.session.add_message("assistant", full_response)

        self._chat_history().clear()
        for msg in self.session.messages:
            self._chat_history().write(ChatMessage(msg.role, msg.content))

        status = self._status()
        status.status = "ready"
        status.tokens_generated = self.engine.tokens_generated
        status.tokens_per_second = self.engine.tokens_per_second

        if self.config.storage.auto_save:
            self.store.save(self.session)

    def _handle_stream_error(self, error: str) -> None:
        self._streaming = False
        self._status().status = "error"
        self._chat_history().write(Panel(f"Generation error: {error}", border_style="red"))

    def _handle_slash_command(self, text: str) -> None:
        parts = text[1:].split()
        cmd = parts[0].lower() if parts else "help"

        if cmd == "help":
            self.action_show_help()
        elif cmd == "new":
            self.action_new_session()
        elif cmd == "save":
            self.action_save_session()
        elif cmd == "clear":
            self.action_clear_chat()
        elif cmd == "config":
            self._show_config()
        elif cmd == "presets":
            self._list_presets()
        elif cmd == "preset" and len(parts) > 1:
            self._on_preset_selected(parts[1])
        elif cmd == "download":
            self._show_download_instructions()
        elif cmd == "export":
            self.action_export_md()
        elif cmd == "tokens":
            current = self.session.messages
            total_chars = sum(len(m.content) for m in current)
            total_msgs = len(current)
            self._chat_history().write(Panel(
                f"Messages: {total_msgs}\nTotal characters: {total_chars}\nTokens (approx): {total_chars // 4}",
                title="Token Stats",
                border_style="blue",
            ))
        else:
            self._chat_history().write(Panel(f"Unknown command: /{cmd}. Type /help for available commands.", border_style="yellow"))

    def _show_config(self) -> None:
        cfg = self.config
        lines = [
            f"Model path: {cfg.model.path}",
            f"Context size: {cfg.model.context_size}",
            f"Max tokens: {cfg.model.max_tokens}",
            f"Temperature: {cfg.model.temperature}",
            f"Top-p: {cfg.model.top_p}",
            f"Preset: {self._current_preset}",
            f"Save dir: {cfg.storage.save_dir}",
        ]
        self._chat_history().write(Panel("\n".join(lines), title="Configuration", border_style="blue"))

    def _list_presets(self) -> None:
        presets = list_presets(self.config.prompt.custom_presets_file)
        lines = [f"  {k} {'(current)' if k == self._current_preset else ''}" for k in presets]
        self._chat_history().write(Panel("\n".join(lines), title="Available Presets", border_style="blue"))

    def _show_download_instructions(self) -> None:
        msg = (
            "[bold]Model Download Instructions[/]\n\n"
            "Option 1 - Automatic (recommended):\n"
            "  Exit this TUI and run:\n"
            "  [bold]python scripts/download_model.py[/]\n\n"
            "Option 2 - Manual:\n"
            "  1. Go to huggingface.co/models?search=gguf\n"
            "  2. Download a small GGUF file (Q4_K_M quantization)\n"
            "  3. Place it at: [bold]data/models/model.gguf[/]\n\n"
            "Option 3 - Custom path:\n"
            "  Edit [bold]config.toml[/] and set:\n"
            "  [bold]model.path = \"path/to/your/model.gguf\"[/]\n\n"
            "Recommended model:\n"
            "  Qwen2.5-1.5B-Instruct (Q4_K_M, ~1GB)"
        )
        self._chat_history().write(Panel(msg, title="Download Model", border_style="blue"))

    def on_unmount(self) -> None:
        if self.session.messages and self.config.storage.auto_save:
            self.store.save(self.session)
        self.engine.unload()
