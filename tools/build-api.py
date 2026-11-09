#!/usr/bin/env python3
"""Generate compatible root and precise date-first API bundles."""
from pathlib import Path
from build_date_api import build
if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
