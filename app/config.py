from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppConfig:
    base_dir: Path
    notes_dir: Path
    index_path: Path
    host: str = "127.0.0.1"
    port: int = 17831

def default_config(base_dir: Path) -> AppConfig:
    data = base_dir / "data"
    notes = data / "notes"
    idx = data / "index.pkl"
    notes.mkdir(parents=True, exist_ok=True)
    return AppConfig(base_dir=base_dir, notes_dir=notes, index_path=idx)
