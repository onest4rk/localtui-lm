#!/usr/bin/env python3
"""Simple launcher for LocalTUI-LM. Run with: python run.py"""

import os
import sys
from pathlib import Path

os.environ.setdefault("CMAKE_ARGS", "-DLLAMA_AVX2=OFF;-DLLAMA_AVX=OFF;-DLLAMA_AVX512=OFF;-DLLAMA_FMA=OFF")

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app.app import main

main()
