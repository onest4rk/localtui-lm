#!/usr/bin/env python3
"""Simple launcher for LocalTUI-LM. Run with: python run.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app.app import main

main()
