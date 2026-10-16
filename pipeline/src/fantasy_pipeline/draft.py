"""Draft results compared with how each player finished the season."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fantasy_pipeline.transactions import Stint, kept_share, to_date

# Highlight rules. Steals: drafted this round or later, kept by the drafter for
# at least this share of the season, best season rank first. Busts: drafted
# this round or earlier and finished outside this rank, earliest pick first.
STEAL_MIN_ROUND = 10
STEAL_MIN_KEPT = 0.5
BUST_MAX_ROUND = 5
BUST_RANK = 300
HIGHLIGHTS = 5


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


def build_draft(
    draft_results: list[dict[str, Any]],
    players: dict[str, Player],
    game_id: str,
    stints: dict[str, list[Stint]],
    season: tuple[int, int],
) -> dict[str, Any]:
    picks = []
    for result in sorted(draft_results, key=lambda r: int(r["pick"])):
        key = f"{game_id}.p.{result['player_id']}"
        player = players.get(key)
        picks.append(
            {
                "pick": int(result["pick"]),
                "round": int(result["round"]),
                "team_key": result["team_key"],
                "player_key": key,
                "name": player.name if player else key,
                "mlb_team": player.mlb_team if player else "",
                "position": player.position if player else "",
                "rank": player.season_rank if player else None,
                "tenure": tenure(stints.get(key, []), result["team_key"], season),
            }
        )
    return {
        "num_picks": len(picks),
        "picks": picks,
        "steals": [p["pick"] for p in steals(picks)],
        "busts": [p["pick"] for p in busts(picks)],
    }


def tenure(stints: list[Stint], team_key: str, season: tuple[int, int]) -> dict[str, Any]:
    """How long the drafting team kept the player, and where he went next."""
    first = stints[0] if stints and stints[0].team_key == team_key else None
    later = stints[1:] if first else stints
    next_stint = next((s for s in later if s.team_key != team_key), None)
    return {
        "kept_share": kept_share(stints, team_key, *season),
        "left": first.left if first else None,
        "left_date": to_date(first.end) if first else None,
        "next_team_key": next_stint.team_key if next_stint else None,
    }


def steals(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Late picks the drafting team held onto that finished highest."""
    candidates = [
        p
        for p in picks
        if p["round"] >= STEAL_MIN_ROUND
        and p["rank"] is not None
        and p["tenure"]["kept_share"] >= STEAL_MIN_KEPT
    ]
    return sorted(candidates, key=lambda p: p["rank"])[:HIGHLIGHTS]


def busts(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Early picks who finished outside the top BUST_RANK, earliest first."""
    candidates = [
        p
        for p in picks
        if p["round"] <= BUST_MAX_ROUND and (p["rank"] is None or p["rank"] > BUST_RANK)
    ]
    return sorted(candidates, key=lambda p: p["pick"])[:HIGHLIGHTS]
