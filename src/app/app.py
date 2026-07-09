from __future__ import annotations

import sys
from pathlib import Path

from src.config.config import Config
from src.ui.app import LocalLMApp


def main():
    config = Config.load()

    errors = config.validate()
    if errors:
        for err in errors:
            print(f"Config error: {err}", file=sys.stderr)

    app = LocalLMApp(config)
    app.run()


if __name__ == "__main__":
    main()
