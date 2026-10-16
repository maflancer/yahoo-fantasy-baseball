"""Draft results compared with how each player finished the season."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# How many undrafted players to list, best season rank first.
UNDRAFTED_LIMIT = 15


@dataclass(frozen=True)
class Player:
    player_key: str
    name: str
    mlb_team: str
    position: str
    season_rank: int | None


def parse_players(pages: list[dict[str, Any]], year: int) -> dict[str, Player]:
    """Players from league player-collection pages fetched with `out=ranks`."""
    players: dict[str, Player] = {}
    for page in pages:
        collection = page["fantasy_content"]["league"][1].get("players")
        if not isinstance(collection, dict):  # Yahoo returns [] for an empty page
            continue
        for i in range(int(collection["count"])):
            entry = collection[str(i)]["player"]
            info: dict[str, Any] = {}
            for item in entry[0]:
                if isinstance(item, dict):
                    info.update(item)
            players[info["player_key"]] = Player(
                player_key=info["player_key"],
                name=info["name"]["full"],
                mlb_team=info.get("editorial_team_abbr", ""),
                position=info.get("display_position", ""),
                season_rank=_season_rank(entry, year),
            )
    return players


def _season_rank(entry: list[Any], year: int) -> int | None:
    for item in entry[1:]:
        for rank in item.get("player_ranks", []) if isinstance(item, dict) else []:
            rank = rank["player_rank"]
            if rank.get("rank_type") == "S" and str(rank.get("rank_season")) == str(year):
                return int(rank["rank_value"])
    return None


def pick_value(pick: int, rank: int | None, num_picks: int) -> int | None:
    """How many spots better than their draft slot a player finished (negative = worse).

    Ranks past the end of the draft count as one spot past the last pick, so a
    late-round flier who finished 900th isn't scored as a bigger bust than a
    first-rounder who finished 300th.
    """
    if rank is None:
        return None
    return pick - min(rank, num_picks + 1)


def build_draft(
    draft_results: list[dict[str, Any]], players: dict[str, Player], game_id: str
) -> dict[str, Any]:
    num_picks = len(draft_results)
    picks = []
    for result in sorted(draft_results, key=lambda r: int(r["pick"])):
        key = f"{game_id}.p.{result['player_id']}"
        player = players.get(key)
        rank = player.season_rank if player else None
        picks.append(
            {
                "pick": int(result["pick"]),
                "round": int(result["round"]),
                "team_key": result["team_key"],
                "player_key": key,
                "name": player.name if player else key,
                "mlb_team": player.mlb_team if player else "",
                "position": player.position if player else "",
                "rank": rank,
                "value": pick_value(int(result["pick"]), rank, num_picks),
            }
        )

    drafted = {p["player_key"] for p in picks}
    undrafted = sorted(
        (p for p in players.values() if p.player_key not in drafted and p.season_rank),
        key=lambda p: p.season_rank or 0,
    )[:UNDRAFTED_LIMIT]

    return {
        "num_picks": num_picks,
        "picks": picks,
        "undrafted": [
            {
                "player_key": p.player_key,
                "name": p.name,
                "mlb_team": p.mlb_team,
                "position": p.position,
                "rank": p.season_rank,
            }
            for p in undrafted
        ],
    }
