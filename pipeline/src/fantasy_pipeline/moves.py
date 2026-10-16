"""The season's move log (draft picks, adds, drops, trades) and top pickups."""

from __future__ import annotations

from typing import Any

from fantasy_pipeline.draft import Player
from fantasy_pipeline.transactions import Stint, Transaction, stint_json, to_date

# How many of the best-ranked players picked up during the season to list.
TOP_PICKUPS = 15


def build_moves(
    transactions: list[Transaction],
    draft_results: list[dict[str, Any]],
    game_id: str,
    draft_time: int,
    players: dict[str, Player],
    stints: dict[str, list[Stint]],
) -> dict[str, Any]:
    names: dict[str, str] = {}
    entries = []
    for tx in reversed(transactions):  # newest first
        for move in tx.moves:
            names.setdefault(move.player_key, move.name)
        entries.append(
            {
                "id": tx.transaction_id,
                "date": to_date(tx.timestamp),
                "type": tx.type,
                "moves": [
                    move_json(m.player_key, m.action, m.from_team, m.to_team, m.via)
                    for m in tx.moves
                ],
            }
        )

    draft_date = to_date(draft_time)
    for result in sorted(draft_results, key=lambda r: int(r["pick"])):
        entries.append(
            {
                "id": f"draft-{result['pick']}",
                "date": draft_date,
                "type": "draft",
                "pick": int(result["pick"]),
                "round": int(result["round"]),
                "moves": [
                    move_json(
                        f"{game_id}.p.{result['player_id']}", "draft", None, result["team_key"]
                    )
                ],
            }
        )

    involved = list(dict.fromkeys(m["player_key"] for e in entries for m in e["moves"]))
    return {
        "transactions": entries,
        "players": {key: player_json(key, players.get(key), names.get(key)) for key in involved},
        "top_pickups": top_pickups(stints, players),
    }


def move_json(
    player_key: str,
    action: str,
    from_team: str | None,
    to_team: str | None,
    via: str | None = None,
) -> dict[str, Any]:
    """One player's move; teams and source are omitted when they don't apply."""
    move: dict[str, Any] = {"player_key": player_key, "action": action}
    if from_team:
        move["from_team_key"] = from_team
    if to_team:
        move["to_team_key"] = to_team
    if via:
        move["via"] = via
    return move


def player_json(key: str, player: Player | None, fallback_name: str | None) -> dict[str, Any]:
    return {
        "name": player.name if player else (fallback_name or key),
        "position": player.position if player else "",
        "mlb_team": player.mlb_team if player else "",
        "rank": player.season_rank if player else None,
    }


def top_pickups(stints: dict[str, list[Stint]], players: dict[str, Player]) -> list[dict[str, Any]]:
    """The best-ranked players any team added during the season, with every team
    that had them."""
    picked_up = [
        (players[key], history)
        for key, history in stints.items()
        if key in players and players[key].season_rank and any(s.acquired == "add" for s in history)
    ]
    picked_up.sort(key=lambda pair: pair[0].season_rank or 0)
    return [
        {"player_key": player.player_key, "stints": [stint_json(s) for s in history]}
        for player, history in picked_up[:TOP_PICKUPS]
    ]
