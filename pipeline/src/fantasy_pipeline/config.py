"""Load config.toml and environment-provided settings."""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

NAME_MAP_ENV = "TEAM_NAME_MAP"


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


def load_name_map(env: dict[str, str] | None = None) -> dict[str, str]:
    """Optional manager-nickname -> display-name overrides from the TEAM_NAME_MAP env var (JSON)."""
    env = os.environ if env is None else env
    raw = env.get(NAME_MAP_ENV, "").strip()
    if not raw:
        return {}
    mapping = json.loads(raw)
    if not isinstance(mapping, dict):
        raise ValueError(f"{NAME_MAP_ENV} must be a JSON object of nickname -> display name")
    return {str(k): str(v) for k, v in mapping.items()}
