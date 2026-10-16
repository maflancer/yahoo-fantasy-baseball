"""All network access to Yahoo lives here."""

from __future__ import annotations

import logging
from pathlib import Path

import yahoo_fantasy_api as yfa
from yahoo_oauth import OAuth2

from fantasy_pipeline.build import RawSeason
from fantasy_pipeline.config import Season
from fantasy_pipeline.transactions import transaction_player_keys

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


# Yahoo returns at most 25 players per request.
PLAYERS_PAGE = 25
# How many of the season's top-ranked players to fetch, so rankings cover
# standouts who were never drafted.
TOP_RANKED = 100


def fetch_players(league: yfa.League, player_keys: list[str]) -> list[dict]:
    """Raw player-collection pages, with season ranks, for the given players plus
    the season's top-ranked players."""
    league_key = league.league_id
    pages = []
    for i in range(0, len(player_keys), PLAYERS_PAGE):
        batch = ",".join(player_keys[i : i + PLAYERS_PAGE])
        pages.append(
            league.yhandler.get(f"league/{league_key}/players;player_keys={batch};out=ranks")
        )
    for start in range(0, TOP_RANKED, PLAYERS_PAGE):
        pages.append(
            league.yhandler.get(
                f"league/{league_key}/players;sort=AR;sort_type=season;"
                f"start={start};count={PLAYERS_PAGE};out=ranks"
            )
        )
    return pages


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
    draft_results = league.draft_results()
    transactions = league.yhandler.get(f"league/{league.league_id}/transactions")
    game_id = league.league_id.split(".")[0]
    player_keys = list(
        dict.fromkeys(
            [f"{game_id}.p.{pick['player_id']}" for pick in draft_results if "player_id" in pick]
            + transaction_player_keys(transactions)
        )
    )
    logger.info(
        "Fetching %s draft picks and ranks for %s players", len(draft_results), len(player_keys)
    )

    return RawSeason(
        year=season.year,
        settings=settings,
        settings_raw=league.yhandler.get_settings_raw(league.league_id),
        standings=league.standings(),
        teams=league.teams(),
        matchups=[league.matchups(week) for week in range(1, last_week + 1)],
        draft_results=draft_results,
        transactions=transactions,
        players=fetch_players(league, player_keys) if player_keys else [],
    )
