"""All network access to Yahoo lives here."""

from __future__ import annotations

import logging
from pathlib import Path

import yahoo_fantasy_api as yfa
from yahoo_oauth import OAuth2

from fantasy_pipeline.build import RawSeason
from fantasy_pipeline.config import Season

logger = logging.getLogger(__name__)


def connect(oauth_file: Path) -> OAuth2:
    if not oauth_file.exists():
        raise FileNotFoundError(f"OAuth file not found: {oauth_file}")
    # yahoo_oauth logs every token check at INFO; keep the output readable.
    logging.getLogger("yahoo_oauth").setLevel(logging.WARNING)
    return OAuth2(None, None, from_file=str(oauth_file))


def last_completed_week(settings: dict) -> int:
    """The final week once the season is over, otherwise the week before the current one."""
    if str(settings.get("is_finished", "0")) == "1":
        return int(settings["end_week"])
    return int(settings["current_week"]) - 1


def fetch_season(oauth: OAuth2, game_code: str, season: Season) -> RawSeason:
    game = yfa.Game(oauth, game_code)
    league_id = season.league_id
    if league_id is None:
        ids = game.league_ids(year=season.year)
        if not ids:
            raise RuntimeError(f"No {game_code} leagues found for {season.year}")
        league_id = ids[0]
    league = game.to_league(league_id)
    logger.info("Season %s: league %s", season.year, league_id)

    settings = league.settings()
    last_week = last_completed_week(settings)
    logger.info("Fetching weeks 1-%s", last_week)

    return RawSeason(
        year=season.year,
        settings=settings,
        settings_raw=league.yhandler.get_settings_raw(league.league_id),
        standings=league.standings(),
        teams=league.teams(),
        matchups=[league.matchups(week) for week in range(1, last_week + 1)],
    )
