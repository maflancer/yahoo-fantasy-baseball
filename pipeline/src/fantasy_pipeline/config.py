"""Load config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Season:
    year: int
    # Yahoo league key, e.g. "469.l.83828". When omitted, the first league
    # the authenticated user played in that year is used.
    league_id: str | None = None


@dataclass(frozen=True)
class Config:
    game: str
    output_dir: Path
    oauth_file: Path
    seasons: tuple[Season, ...]

    def season(self, year: int) -> Season:
        for season in self.seasons:
            if season.year == year:
                return season
        # Allow ad-hoc backfills of years not listed in the config.
        return Season(year=year)

    @property
    def latest_season(self) -> Season:
        return max(self.seasons, key=lambda s: s.year)


def load_config(path: Path) -> Config:
    """Read config.toml. Relative paths resolve against the config file's folder."""
    with path.open("rb") as f:
        raw = tomllib.load(f)

    base = path.resolve().parent
    seasons = tuple(
        Season(year=int(s["year"]), league_id=s.get("league_id")) for s in raw.get("seasons", [])
    )
    if not seasons:
        raise ValueError(f"{path}: at least one [[seasons]] entry is required")

    return Config(
        game=raw.get("game", "mlb"),
        output_dir=base / raw.get("output_dir", "web/public/data"),
        oauth_file=base / raw.get("oauth_file", "oauth2.json"),
        seasons=seasons,
    )
