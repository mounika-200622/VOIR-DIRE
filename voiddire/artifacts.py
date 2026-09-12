"""Working-tree snapshots, kept on disk so a holding can be replayed against history."""
from __future__ import annotations

import json
from pathlib import Path

from .change import Change


def _dir(repo: Path) -> Path:
    d = Path(repo) / ".voiddire" / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(repo: Path, run_id: int, ch: Change) -> None:
    (_dir(repo) / f"run_{run_id}.json").write_text(
        json.dumps({"touched": ch.touched, "added": ch.added}), encoding="utf-8")


def load(repo: Path, run_id: int) -> Change | None:
    p = _dir(repo) / f"run_{run_id}.json"
    if not p.is_file():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return Change(repo=Path(repo), touched=d["touched"], added=d["added"])
