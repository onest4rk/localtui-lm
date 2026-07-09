from __future__ import annotations

import itertools
import threading
import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, RichLog, Button, Label, ListView, ListItem
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from rich.panel import Panel

from config.config import Config
from llm.engine import LLMEngine
from storage.session import Session, SessionStore
from prompts.presets import get_preset, list_presets
from ui.widgets import StatusBar, ChatMessage, SessionList, ModelInfoPanel, PresetSelector


class PresetScreen(ModalScreen[str]):
    def __init__(self, presets: dict[str, str], current: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.presets = presets
        self.current = current

    def compose(self) -> ComposeResult:
        yield Container(
            Label("select preset:"),
            ListView(
                *[ListItem(Label(f"{'* ' if name == self.current else '  '}{name}")) for name in self.presets]
            ),
            Button("cancel", id="cancel"),
            classes="popup",
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
        items = [ListItem(Label(f"{s.get('title', 'Untitled')} ({s.get('message_count', 0)} msgs)"), id=s.get("session_id", "")) for s in self._sessions]
        yield Container(
            Label("saved sessions:"),
            ListView(*items) if items else Label("no saved sessions"),
            Button("cancel", id="cancel"),
            classes="popup",
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)


class LocalLMApp(App):
    TITLE = "localtui-lm"
    SUB_TITLE = "cpu-only local ai"

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit"),
        Binding("ctrl+l", "clear_chat", "clear"),
        Binding("ctrl+n", "new_session", "new"),
        Binding("ctrl+s", "save_session", "save"),
        Binding("ctrl+o", "open_sessions", "open"),
        Binding("ctrl+p", "select_preset", "preset"),
        Binding("ctrl+e", "export_md", "export"),
        Binding("escape", "focus_input", "input"),
    ]

    CSS = """
    Screen { background: #1a1a1a; }
    #main-container { layout: horizontal; height: 100%; }
    #chat-column { width: 70%; height: 100%; }
    #sidebar { width: 30%; height: 100%; border-left: solid #333; }
    #chat-history { height: 1fr; border: solid #333; padding: 1; overflow-y: auto; background: #1a1a1a; }
    #chat-history:focus { border: solid #555; }
    #input-area { height: auto; min-height: 3; max-height: 8; border-top: solid #333; padding: 0 1; }
    #prompt-input { width: 1fr; }
    #prompt-input:focus { border: solid #666; }
    #input-buttons { width: auto; height: 3; }
    #sidebar StatusBar { height: auto; }
    #sidebar ModelInfoPanel { height: auto; }
    #sidebar PresetSelector { height: 1; padding: 0 1; color: #888; }
    #sidebar SessionList { height: 1fr; }
    .popup { width: 50; height: 20; margin: 5 8; padding: 1; background: #222; border: thick #444; }
    Header { background: #111; color: #aaa; }
    Footer { background: #111; color: #666; }
    Input { background: #222; color: #ddd; border: solid #444; }
    Button { background: #333; color: #ccc; }
    Button:hover { background: #555; }
    ListView { background: #222; }
    ListItem { background: #222; color: #ccc; }
    ListItem:hover { background: #444; }
    Label { color: #aaa; }
    """

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.engine = LLMEngine(config)
        self.session = Session()
        self.store = SessionStore(config.storage.save_dir)
        self._streaming = False
        self._spinner_active = False
        self._spinner_frames = None
        self._current_preset = config.prompt.default_preset

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Vertical(id="chat-column"):
                yield RichLog(id="chat-history", highlight=True, markup=True)
                with Horizontal(id="input-area"):
                    yield Input(placeholder="type a message... (/help)", id="prompt-input")
                    with Horizontal(id="input-buttons"):
                        yield Button("send", id="send-btn")
                        yield Button("clear", id="clear-btn")
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
        self.set_timer(0.05, self._focus_input)

    def _focus_input(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    def _show_welcome(self) -> None:
        model_path = Path(self.config.model.path)
        if model_path.exists():
            self._chat_history().write(Panel(
                "welcome to localtui-lm\n\ntype a message to start\n/help for commands",
                title="welcome",
                border_style="#446644",
            ))
        else:
            self._chat_history().write(Panel(
                "[#ffa500]no model found[/]\n\n"
                f"expected at: {self.config.model.path}\n\n"
                "to download: [bold]python scripts/download_model.py[/]",
                title="welcome",
                border_style="#664444",
            ))

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
        self._spinner_frames = itertools.cycle([".  ", ".. ", "...", " ..", "  .", "   "])
        self.set_interval(0.3, self._tick_spinner)

        def load_thread():
            try:
                self.engine.load()
                self._spinner_active = False
                self.call_from_thread(self._on_model_loaded)
            except Exception as e:
                self._spinner_active = False
                self.call_from_thread(self._on_model_error, str(e))

        threading.Thread(target=load_thread, daemon=True).start()

    def _tick_spinner(self) -> None:
        if not self._spinner_active:
            return
        panel = self.query_one("#model-info", ModelInfoPanel)
        panel.loading_progress = next(self._spinner_frames)

    def _on_model_loaded(self) -> None:
        info_panel = self.query_one("#model-info", ModelInfoPanel)
        info_panel.loaded = True
        info_panel.load_time = self.engine.load_time
        info_panel.model_path = self.config.model.path

        status_bar = self._status()
        status_bar.status = "ready"
        status_bar.context_max = self.config.model.context_size
        self._chat_history().write(Panel("model ready", border_style="#446644"))

    def _on_model_error(self, error: str) -> None:
        self._status().status = "error"
        self._chat_history().write(Panel(f"error: {error}", border_style="#664444"))

    def action_clear_chat(self) -> None:
        if self._streaming:
            return
        self._chat_history().clear()
        self.session = Session()
        self._chat_history().write(Panel("chat cleared", border_style="#666644"))

    def action_new_session(self) -> None:
        if self._streaming:
            return
        if self.session.messages and self.config.storage.auto_save:
            self.store.save(self.session)
        self.session = Session()
        self._chat_history().clear()
        self._update_sessions()
        self._chat_history().write(Panel("new session", border_style="#666644"))

    def action_save_session(self) -> None:
        if not self.session.messages:
            self._chat_history().write(Panel("nothing to save", border_style="#666644"))
            return
        self.store.save(self.session)
        self._update_sessions()
        self._chat_history().write(Panel("session saved", border_style="#446644"))

    def action_open_sessions(self) -> None:
        sessions = self.store.list_sessions()
        if not sessions:
            self._chat_history().write(Panel("no saved sessions", border_style="#666644"))
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

    def action_select_preset(self) -> None:
        presets = list_presets(self.config.prompt.custom_presets_file)
        self.push_screen(PresetScreen(presets, self._current_preset), self._on_preset_selected)

    def _on_preset_selected(self, name: str) -> None:
        if name:
            self._current_preset = name
            self._update_presets()
            self._chat_history().write(Panel(f"preset: {name}", border_style="#444466"))

    def action_export_md(self) -> None:
        if not self.session.messages:
            self._chat_history().write(Panel("nothing to export", border_style="#666644"))
            return
        export_dir = Path.cwd() / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        path = export_dir / f"{self.session.session_id}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {self.session.title}\n\n")
            for msg in self.session.messages:
                f.write(f"## {msg.role}\n\n{msg.content}\n\n")
        self._chat_history().write(Panel(f"exported: {path}", border_style="#446644"))

    def action_focus_input(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    def action_show_help(self) -> None:
        self._chat_history().write(Panel(
            "[bold]keys[/]\n"
            "  ctrl+c    quit\n"
            "  ctrl+l    clear\n"
            "  ctrl+n    new session\n"
            "  ctrl+s    save\n"
            "  ctrl+o    open\n"
            "  ctrl+p    preset\n"
            "  ctrl+e    export\n"
            "  escape    focus input\n"
            "\n"
            "[bold]commands[/]\n"
            "  /help       help\n"
            "  /new        new session\n"
            "  /save       save\n"
            "  /clear      clear\n"
            "  /config     settings\n"
            "  /presets    list presets\n"
            "  /preset <n> switch preset\n"
            "  /download   download model\n"
            "  /export     export to md\n"
            "  /tokens     token stats",
            title="help",
            border_style="#444466",
        ))

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
            self._chat_history().write(Panel(
                "[#ffa500]model not loaded[/]\n\n"
                f"expected: {self.config.model.path}\n\n"
                "fix: python scripts/download_model.py\n"
                "or: type /download",
                title="no model",
                border_style="#664444",
            ))
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
                for token in self.engine.generate(prompt=prompt_text, stream=True):
                    full_response += token
                    self.call_from_thread(self._update_stream, full_response)

                self.call_from_thread(self._finish_stream, full_response)
            except Exception as e:
                self.call_from_thread(self._handle_stream_error, str(e))

        threading.Thread(target=generate, daemon=True).start()

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
        self._chat_history().write(Panel(f"error: {error}", border_style="#664444"))

    def _handle_slash_command(self, text: str) -> None:
        parts = text[1:].split()
        cmd = parts[0].lower() if parts else "help"

        actions = {
            "help": self.action_show_help,
            "new": self.action_new_session,
            "save": self.action_save_session,
            "clear": self.action_clear_chat,
            "config": self._show_config,
            "presets": self._list_presets,
            "export": self.action_export_md,
            "download": self._show_download_instructions,
            "tokens": self._show_token_stats,
        }

        if cmd in actions:
            actions[cmd]()
        elif cmd == "preset" and len(parts) > 1:
            self._on_preset_selected(parts[1])
        else:
            self._chat_history().write(Panel(f"unknown: /{cmd}  (/help)", border_style="#666644"))

    def _show_config(self) -> None:
        cfg = self.config
        lines = [
            f"model: {cfg.model.path}",
            f"ctx: {cfg.model.context_size}",
            f"max tokens: {cfg.model.max_tokens}",
            f"temp: {cfg.model.temperature}",
            f"top-p: {cfg.model.top_p}",
            f"preset: {self._current_preset}",
            f"save: {cfg.storage.save_dir}",
        ]
        self._chat_history().write(Panel("\n".join(lines), title="config", border_style="#444466"))

    def _list_presets(self) -> None:
        presets = list_presets(self.config.prompt.custom_presets_file)
        lines = [f"  {k} {'(current)' if k == self._current_preset else ''}" for k in presets]
        self._chat_history().write(Panel("\n".join(lines), title="presets", border_style="#444466"))

    def _show_token_stats(self) -> None:
        total_chars = sum(len(m.content) for m in self.session.messages)
        total_msgs = len(self.session.messages)
        self._chat_history().write(Panel(
            f"messages: {total_msgs}\nchars: {total_chars}\ntokens (est): {total_chars // 4}",
            title="tokens",
            border_style="#444466",
        ))

    def _show_download_instructions(self) -> None:
        self._chat_history().write(Panel(
            "download model:\n\n"
            "  1. exit this app\n"
            "  2. run: python scripts/download_model.py\n\n"
            "or set a custom path in config.toml",
            title="download",
            border_style="#666644",
        ))

    def on_unmount(self) -> None:
        if self.session.messages and self.config.storage.auto_save:
            self.store.save(self.session)
        self.engine.unload()
