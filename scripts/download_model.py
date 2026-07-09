#!/usr/bin/env python3
"""
Model download helper for LocalTUI-LM.

Downloads a small GGUF model suitable for CPU-only inference.
Default: Qwen2.5-1.5B-Instruct (Q4_K_M) from Hugging Face.

Usage:
    python scripts/download_model.py
    python scripts/download_model.py --model <hf-repo> --file <filename>
    python scripts/download_model.py --output <path>
"""

import argparse
import os
import sys
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin


DEFAULT_MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
DEFAULT_MODEL_FILE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
HF_BASE = "https://huggingface.co"


def download_file(url: str, dest: Path, desc: str = "") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {desc or url}...")
    print(f"  To: {dest}")

    try:
        with urlopen(url) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 8192

            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 // total
                        print(f"\r  Progress: {pct}% ({downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB)", end="")
                    else:
                        print(f"\r  Downloaded: {downloaded // 1024 // 1024}MB", end="")
                    sys.stdout.flush()
            print()

        print(f"Download complete: {dest}")
        print(f"  Size: {dest.stat().st_size / 1024 / 1024:.1f} MB")

    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        if dest.exists():
            dest.unlink()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download a GGUF model for LocalTUI-LM")
    parser.add_argument("--model", default=DEFAULT_MODEL_REPO, help="Hugging Face model repo")
    parser.add_argument("--file", default=DEFAULT_MODEL_FILE, help="GGUF filename in the repo")
    parser.add_argument("--output", default=None, help="Output path (default: data/models/<filename>)")
    args = parser.parse_args()

    if args.output:
        output_path = Path(args.output)
    else:
        script_dir = Path(__file__).resolve().parent
        project_dir = script_dir.parent
        output_path = project_dir / "data" / "models" / "model.gguf"

    repo = args.model.strip("/")
    file_url = f"{HF_BASE}/{repo}/resolve/main/{args.file}"

    print(f"Model repo: {repo}")
    print(f"Model file: {args.file}")
    print(f"Expected size: ~1-2 GB (Q4_K_M quantization)")
    print()

    download_file(file_url, output_path, desc=f"{repo}/{args.file}")

    print()
    print(f"Model downloaded to: {output_path}")
    print("The app will find it automatically at the default location.")
    print("You can now run: python run.py")


if __name__ == "__main__":
    main()
