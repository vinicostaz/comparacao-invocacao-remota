from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def database_path() -> Path:
    configured = os.getenv("MUSIC_DB")
    path = Path(configured) if configured else project_root() / "data" / "music.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

