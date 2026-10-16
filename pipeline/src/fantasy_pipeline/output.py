"""Write JSON documents to the output directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SEASONS_FILE = "seasons.json"


def write_json(path: Path, doc: Any) -> bool:
    """Write doc as JSON. Returns True if the file's contents changed."""
    # Compact: these files are served to browsers, not read by people.
    text = json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def write_season(output_dir: Path, year: int, docs: dict[str, Any]) -> bool:
    """Write one season's files. Returns True if any of them changed."""
    changed = [write_json(output_dir / str(year) / name, doc) for name, doc in docs.items()]
    return any(changed)


def update_seasons_index(
    output_dir: Path, summary: dict[str, Any], data_changed: bool = True
) -> list[dict[str, Any]]:
    """Insert or replace one season in seasons.json, newest first.

    When the season's data didn't change, its previous `updated_at` is kept so
    re-running the pipeline on unchanged data produces no diff.
    """
    path = output_dir / SEASONS_FILE
    seasons = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    previous = next((s for s in seasons if s.get("year") == summary["year"]), None)
    if previous and not data_changed and "updated_at" in previous:
        summary = {**summary, "updated_at": previous["updated_at"]}

    seasons = [s for s in seasons if s.get("year") != summary["year"]]
    seasons.append(summary)
    seasons.sort(key=lambda s: s["year"], reverse=True)
    write_json(path, seasons)
    return seasons
