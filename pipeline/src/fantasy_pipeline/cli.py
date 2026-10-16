"""Command line entry point: `uv run fantasy-pipeline [--season YEAR ...] [--all]`."""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from fantasy_pipeline.build import build_season, season_summary
from fantasy_pipeline.config import load_config
from fantasy_pipeline.output import update_seasons_index, write_season

logger = logging.getLogger("fantasy_pipeline")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("config.toml"), help="path to config.toml"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--season",
        type=int,
        action="append",
        dest="seasons",
        help="season year to fetch (repeatable). Defaults to the latest season in the config.",
    )
    group.add_argument("--all", action="store_true", help="fetch every season in the config")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    config = load_config(args.config)

    if args.all:
        seasons = list(config.seasons)
    elif args.seasons:
        seasons = [config.season(year) for year in args.seasons]
    else:
        seasons = [config.latest_season]

    # Imported here so config errors surface without needing Yahoo credentials.
    from fantasy_pipeline.yahoo import connect, fetch_season

    oauth = connect(config.oauth_file)
    updated_at = datetime.now(UTC).isoformat(timespec="seconds")
    for season in seasons:
        raw = fetch_season(oauth, config.game, season)
        changed = write_season(config.output_dir, season.year, build_season(raw))
        update_seasons_index(config.output_dir, season_summary(raw, updated_at), changed)
        logger.info("%s: %s", season.year, "updated" if changed else "no changes")
