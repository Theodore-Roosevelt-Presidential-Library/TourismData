"""Shared helpers for the TourismData fetchers."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "config" / "sources.json").read_text())

USER_AGENT = (
    "TRPL-TourismData/1.0 (+https://github.com/Theodore-Roosevelt-Presidential-Library/TourismData)"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_csv(df, name: str) -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / name
    df.to_csv(path, index=False)
    print(f"wrote {path.relative_to(ROOT)} ({len(df)} rows)")
    return path


def update_manifest(source: str, **fields) -> None:
    """Record fetch status per source in data/manifest.json."""
    path = DATA / "manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else {}
    manifest[source] = {"fetched_at": now_iso(), **fields}
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
