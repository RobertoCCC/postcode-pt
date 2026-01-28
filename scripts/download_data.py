"""Download Portuguese postal-code CSVs from the open `centraldedados` dataset.

Source: https://github.com/centraldedados/codigos_postais
License: PDDL (Public Domain Dedication License).
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

BASE_URL = (
    "https://raw.githubusercontent.com/centraldedados/codigos_postais/master/data"
)
FILES = ("distritos.csv", "concelhos.csv", "codigos_postais.csv")
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def download(client: httpx.Client, filename: str) -> Path:
    url = f"{BASE_URL}/{filename}"
    dest = DATA_DIR / filename
    print(f"  → {filename} ", end="", flush=True)
    with client.stream("GET", url) as resp:
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                f.write(chunk)
    size_mb = dest.stat().st_size / 1024 / 1024
    print(f"({size_mb:.2f} MB) ✓")
    return dest


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading to {DATA_DIR}")
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for name in FILES:
            download(client, name)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
