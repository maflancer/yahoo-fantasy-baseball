"""Assemble the JSON documents the web app reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fantasy_pipeline.bracket import RoundLabel, replay_playoffs
from fantasy_pipeline.leaders import season_leaders
from fantasy_pipeline.parse import (
    Matchup,
    StatCategory,
    managers_by_team,
    parse_matchups,
    parse_scoreboard,
    parse_stat_categories,
    week_dates,
)


@dataclass
class RawSeason:
    """Everything fetched from Yahoo for one season."""

    year: int
    settings: dict[str, Any]  # league.settings()
    settings_raw: dict[str, Any]  # league.yhandler.get_settings_raw()
    standings: list[dict[str, Any]]  # league.standings()
    teams: dict[str, dict[str, Any]]  # league.teams()
    matchups: list[dict[str, Any]]  # league.matchups(week) for each completed week


def team_directory(
    teams: dict[str, dict[str, Any]], name_map: dict[str, str]
) -> list[dict[str, str]]:
    """Public team list. Only manager nicknames (or their mapped names) are exposed,
    never Yahoo team names."""
    return [
        {"team_key": key, "name": name_map.get(nickname, nickname)}
        for key, nickname in sorted(managers_by_team(teams).items())
    ]


def build_standings(raw: RawSeason) -> list[dict[str, Any]]:
    rows = []
    for team in raw.standings:
        totals = team.get("outcome_totals", {})
        rows.append(
            {
                "team_key": team["team_key"],
                "rank": _int_or_none(team.get("rank")),
                "playoff_seed": _int_or_none(team.get("playoff_seed")),
                "wins": int(totals.get("wins", 0)),
                "losses": int(totals.get("losses", 0)),
                "ties": int(totals.get("ties", 0)),
                "percentage": totals.get("percentage", ""),
                "games_back": team.get("games_back", "-"),
            }
        )
    return sorted(rows, key=lambda r: (r["rank"] is None, r["rank"]))


def build_season(raw: RawSeason, name_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Returns {filename: document} for one season."""
    categories: list[StatCategory] = parse_stat_categories(raw.settings_raw)
    rows = [row for week in raw.matchups for row in parse_matchups(week, categories)]
    matchups_by_week: dict[int, list[Matchup]] = {}
    dates = {}
    for week_raw in raw.matchups:
        week_matchups = parse_scoreboard(week_raw, categories)
        if not week_matchups:
            continue
        week = week_matchups[0].week
        matchups_by_week[week] = week_matchups
        dates[week] = week_dates(week_raw)

    labels, _ = replay_playoffs(
        matchups_by_week, _int_or_none(raw.settings.get("num_playoff_teams"))
    )
    weeks = season_leaders(rows, categories, dates)
    for week in weeks:
        labelled = [
            (m, labels.get((week["week"], i)))
            for i, m in enumerate(matchups_by_week.get(week["week"], []))
        ]
        # Title games first, then placement games from the top down.
        labelled.sort(key=lambda pair: pair[1].order if pair[1] else 0)
        week["matchups"] = [matchup_json(m, label) for m, label in labelled]

    teams = team_directory(raw.teams, name_map)
    return {
        "standings.json": {"teams": teams, "standings": build_standings(raw)},
        "scoreboard.json": {
            "teams": teams,
            "categories": [c.to_json() for c in categories],
            "weeks": weeks,
        },
    }


def matchup_json(matchup: Matchup, label: RoundLabel | None = None) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "winner_key": matchup.winner_key,
        "is_playoffs": matchup.is_playoffs,
        "is_consolation": matchup.is_consolation,
        "teams": [
            {"team_key": side.team_key, "points": side.points, "stats": side.stats}
            for side in matchup.sides
        ],
        "stat_winners": matchup.stat_winners,
    }
    if label:
        doc["round"] = label.name
        doc["for_title"] = label.for_title
    return doc


def season_summary(raw: RawSeason, updated_at: str) -> dict[str, Any]:
    s = raw.settings
    return {
        "year": raw.year,
        "name": s.get("name", str(raw.year)),
        "league_key": s.get("league_key", ""),
        "num_teams": _int_or_none(s.get("num_teams")),
        "playoff_start_week": _int_or_none(s.get("playoff_start_week")),
        "is_finished": str(s.get("is_finished", "0")) == "1",
        "updated_at": updated_at,
    }


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
