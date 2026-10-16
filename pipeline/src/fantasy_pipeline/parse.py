"""Turn raw Yahoo API responses into plain records.

Everything here is pure (no network) so it can be tested against saved responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StatCategory:
    stat_id: str
    abbr: str
    name: str
    higher_is_better: bool
    position_type: str  # "B" (batting) or "P" (pitching)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.stat_id,
            "abbr": self.abbr,
            "name": self.name,
            "higher_is_better": self.higher_is_better,
            "position_type": self.position_type,
        }


@dataclass(frozen=True)
class TeamWeek:
    week: int
    team_key: str
    manager: str
    opponent_key: str
    result: str  # "W", "L" or "T"
    is_playoffs: bool
    is_consolation: bool
    stats: dict[str, str]  # keyed by category abbr, raw Yahoo values


def _flatten(items: list[Any]) -> dict[str, Any]:
    """Yahoo returns objects as lists of single-key dicts (and empty lists). Merge them."""
    merged: dict[str, Any] = {}
    for item in items:
        if isinstance(item, dict):
            merged.update(item)
    return merged


def _flag(value: Any) -> bool:
    return str(value) == "1"


def manager_nickname(team_info: dict[str, Any]) -> str:
    managers = team_info.get("managers") or []
    for entry in managers:
        nickname = entry.get("manager", {}).get("nickname")
        if nickname:
            return nickname
    return f"Team {team_info.get('team_id', '?')}"


def parse_stat_categories(settings_raw: dict[str, Any]) -> list[StatCategory]:
    """Scoring categories from the raw league settings, excluding display-only stats."""
    settings = _league_section(settings_raw)["settings"][0]
    categories = []
    for entry in settings["stat_categories"]["stats"]:
        stat = entry["stat"]
        if _flag(stat.get("is_only_display_stat")):
            continue
        categories.append(
            StatCategory(
                stat_id=str(stat["stat_id"]),
                abbr=stat["display_name"],
                name=stat["name"],
                higher_is_better=str(stat.get("sort_order", "1")) == "1",
                position_type=stat.get("position_type", ""),
            )
        )
    return categories


def parse_matchups(matchups_raw: dict[str, Any], categories: list[StatCategory]) -> list[TeamWeek]:
    """One TeamWeek per team that played, from `league.matchups(week)`."""
    scoreboard = _league_section(matchups_raw)["scoreboard"]
    week = int(scoreboard["week"])
    matchups = scoreboard["0"]["matchups"]
    abbr_by_id = {c.stat_id: c.abbr for c in categories}

    rows: list[TeamWeek] = []
    for i in range(int(matchups["count"])):
        matchup = matchups[str(i)]["matchup"]
        teams = matchup["0"]["teams"]
        is_tied = _flag(matchup.get("is_tied"))
        winner = matchup.get("winner_team_key")

        sides = []
        for j in range(int(teams["count"])):
            team = teams[str(j)]["team"]
            info = _flatten(team[0])
            stats = {
                abbr_by_id[str(s["stat"]["stat_id"])]: s["stat"]["value"]
                for s in team[1]["team_stats"]["stats"]
                if str(s["stat"]["stat_id"]) in abbr_by_id
            }
            sides.append((info, stats))

        for j, (info, stats) in enumerate(sides):
            opponent = sides[1 - j][0] if len(sides) == 2 else {}
            if is_tied or not winner:
                result = "T"
            else:
                result = "W" if info["team_key"] == winner else "L"
            rows.append(
                TeamWeek(
                    week=week,
                    team_key=info["team_key"],
                    manager=manager_nickname(info),
                    opponent_key=opponent.get("team_key", ""),
                    result=result,
                    is_playoffs=_flag(matchup.get("is_playoffs")),
                    is_consolation=_flag(matchup.get("is_consolation")),
                    stats=stats,
                )
            )
    return rows


def week_dates(matchups_raw: dict[str, Any]) -> tuple[str, str]:
    """(start, end) ISO dates for the scoreboard week."""
    matchups = _league_section(matchups_raw)["scoreboard"]["0"]["matchups"]
    first = matchups["0"]["matchup"]
    return first.get("week_start", ""), first.get("week_end", "")


def managers_by_team(teams: dict[str, dict[str, Any]]) -> dict[str, str]:
    """team_key -> manager nickname, from `league.teams()`."""
    return {key: manager_nickname(info) for key, info in teams.items()}


def _league_section(raw: dict[str, Any]) -> dict[str, Any]:
    return raw["fantasy_content"]["league"][1]
