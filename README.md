# LocalTUI-LM

A lightweight, fully local AI assistant that runs on **CPU only** with a polished terminal user interface (TUI). Designed for modest laptops — no GPU required.

## Why CPU-Only

- Many laptops lack a capable GPU for running LLMs.
- Modern quantization (GGUF Q4\_K\_M) makes small models efficient on CPU.
- Fully offline — no data leaves your machine.
- Lower power draw compared to GPU inference.

## Supported Models

Any instruction-tuned GGUF model in the 1B-4B parameter range. Recommended:

| Model | Size (Q4\_K\_M) | RAM Usage |
|---|---|---|
| Qwen2.5-1.5B-Instruct | ~1 GB | ~2 GB |
| Phi-3-mini-4k-instruct | ~2.5 GB | ~4 GB |
| Llama-3.2-3B-Instruct | ~2 GB | ~3.5 GB |
| Gemma-2-2B-it | ~1.5 GB | ~3 GB |

Larger models (up to 7B) work on systems with 8 GB+ RAM.

## Hardware Requirements

- **Minimum:** 4 GB RAM, dual-core CPU (Intel i5 / AMD Ryzen 3 or better)
- **Recommended:** 8 GB RAM, 4+ CPU cores
- **Storage:** 1–3 GB free for model + app
- **GPU:** None required

## Installation

### Prerequisites

- Python 3.10 or later
- pip

### Setup

```bash
# Clone or copy the project
cd localtui-lm

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

# Install the package
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Quick setup (Linux/macOS)

```bash
bash scripts/setup.sh
```

## Model Setup

### Option 1: Download script (recommended)

```bash
python scripts/download_model.py
```

Downloads Qwen2.5-1.5B-Instruct Q4\_K\_M (~1 GB) to `data/models/`.

### Option 2: Manual download

1. Go to [huggingface.co/models?search=gguf](https://huggingface.co/models?search=gguf)
2. Pick a small GGUF model (e.g., `Qwen/Qwen2.5-1.5B-Instruct-GGUF`)
3. Download the `q4_k_m.gguf` file
4. Place it in `data/models/` or update `config.toml` to point to your path

### Option 3: Custom model path

Edit `config.toml`:

```toml
[model]
path = "/path/to/your/model.gguf"
```

## Usage

### Launch the TUI

```bash
# Using the installed command
localtui-lm

# Or directly
python -m src.app.app
```

### Layout

```
┌──────────────────────────────────────────────┐
│ LocalTUI-LM                 Preset: general  │
├──────────────────────┬───────────────────────┤
│ Chat History         │ System Status         │
│                      │ Model Info            │
│                      │ Sessions List         │
├──────────────────────┴───────────────────────┤
│ > Type a message...              [Send]      │
└──────────────────────────────────────────────┘
```

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Ctrl+C` | Quit |
| `Ctrl+L` | Clear chat |
| `Ctrl+N` | New session |
| `Ctrl+S` | Save session |
| `Ctrl+O` | Open saved sessions |
| `Ctrl+P` | Select prompt preset |
| `Ctrl+E` | Export chat to Markdown |
| `Escape` | Focus input |
| `/` | Show help |

### Slash Commands

| Command | Action |
|---|---|
| `/help` | Show help |
| `/new` | New session |
| `/save` | Save session |
| `/clear` | Clear chat |
| `/config` | Show configuration |
| `/presets` | List available presets |
| `/preset <name>` | Switch preset |
| `/export` | Export to Markdown |
| `/tokens` | Show token statistics |

### Prompt Presets

Switch between system prompts via `Ctrl+P` or `/preset`:

- **general** — Helpful, harmless assistant
- **coding** — Expert software engineer
- **writing** — Professional writing assistant
- **tutor** — Patient step-by-step teacher

Custom presets can be added via a JSON file (see `config.toml`).

## Configuration

Configuration is stored in `config.toml` (looked for in: current directory, `~/.config/localtui-lm/`, `~/.localtui-lm/`).

### Key options

```toml
[model]
path = "data/models/model.gguf"     # Path to GGUF model file
context_size = 2048                  # Context window size (tokens)
max_tokens = 512                     # Max tokens per response
temperature = 0.7                    # Sampling temperature (0.0–2.0)
top_p = 0.9                          # Nucleus sampling threshold
repeat_penalty = 1.1                 # Repetition penalty
n_threads = null                     # CPU threads (null = auto)

[storage]
save_dir = "data/sessions"           # Where chat sessions are saved
auto_save = true                     # Auto-save on new messages

[prompt]
default_preset = "general"           # Default system prompt
custom_presets_file = null           # Path to custom presets JSON
```

## Sessions

- Sessions are saved as JSON in `data/sessions/`.
- Auto-save is enabled by default.
- Browse and load sessions via `Ctrl+O`.
- Search sessions by content.
- Export to Markdown via `Ctrl+E` or `/export`.

## Project Structure

```
localtui-lm/
├── src/
│   ├── app/           # Application entry point
│   ├── config/        # TOML config loading and validation
│   ├── llm/           # GGUF inference engine (llama-cpp-python)
│   ├── ui/            # Textual TUI components
│   ├── storage/       # Session save/load
│   ├── prompts/       # System prompt presets
│   └── utils/         # Formatting helpers
├── tests/             # pytest tests
├── scripts/           # Model download, setup
├── data/              # Models, sessions, exports
├── config.toml        # Default configuration
├── pyproject.toml
└── requirements.txt
```

## Tests

```bash
# Install dev dependencies
pip install pytest

# Run tests
pytest tests/
```

## Performance Tuning

### Low-resource mode

```toml
[model]
context_size = 1024
max_tokens = 256
temperature = 0.7
```

### Quality mode

```toml
[model]
context_size = 4096
max_tokens = 1024
temperature = 0.6
top_p = 0.95
```

### Recommended thread count

Set `n_threads` to your physical CPU core count (not logical threads) for best performance.

## Expected RAM Usage

| Context Size | +1.5B model | +3B model |
|---|---|---|
| 1024 | ~2 GB | ~3.5 GB |
| 2048 | ~2.5 GB | ~4 GB |
| 4096 | ~3.5 GB | ~5 GB |

## Troubleshooting

### "Model file not found"
- Run `python scripts/download_model.py`
- Or update `model.path` in `config.toml`

### "llama-cpp-python is not installed"
- Run `pip install llama-cpp-python`
- On Windows, pre-built wheels are available on PyPI

### Slow generation
- Reduce `context_size` and `max_tokens` in config
- Set `n_threads` to your CPU core count
- Use a smaller model (1.5B instead of 3B)

### TUI looks broken
- Ensure your terminal is at least 80×24 characters
- Use a modern terminal emulator (Kitty, iTerm2, Windows Terminal, GNOME Terminal)

## Model Licensing

Models have their own licenses. Check the Hugging Face model card for details. Common licenses:
- **Qwen2.5:** Apache 2.0 / Qwen License
- **Llama 3.2:** Llama 3.2 Community License
- **Phi-3:** MIT
- **Gemma:** Gemma License

## License

This project is licensed under the MIT License. See the LICENSE file.
