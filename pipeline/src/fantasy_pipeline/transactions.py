"""Season transactions and each player's ownership history.

Yahoo's transaction log covers adds, drops and trades but not the draft, so
the draft results are replayed first and every transaction applied on top.
That gives, for every player, the stints each team had him.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

# Yahoo baseball leagues run on US Eastern time.
LEAGUE_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Move:
    player_key: str
    name: str
    action: str  # "add", "drop" or "trade"
    from_team: str | None
    to_team: str | None
    # Where an added player came from, or where a dropped player went:
    # "freeagents" or "waivers".
    via: str | None


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    timestamp: int
    type: str  # Yahoo's type: "add", "drop", "add/drop", "trade" or "commish"
    moves: tuple[Move, ...]


@dataclass
class Stint:
    team_key: str
    start: int  # timestamp
    end: int | None  # None while the team still has him
    acquired: str  # "draft", "add" or "trade"
    left: str | None = None  # "drop" or "trade"


def _flatten(items: list[Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        if isinstance(item, dict):
            merged.update(item)
    return merged


def _collection(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {}
    collection = raw["fantasy_content"]["league"][1].get("transactions")
    return collection if isinstance(collection, dict) else {}


def parse_transactions(raw: dict[str, Any]) -> list[Transaction]:
    """Successful transactions from `league/{key}/transactions`, oldest first."""
    collection = _collection(raw)
    parsed = []
    for i in range(int(collection.get("count", 0))):
        entry = collection[str(i)]["transaction"]
        meta = entry[0]
        if meta.get("status") != "successful":
            continue
        # Transactions without players (e.g. commissioner edits) have [] or nothing here.
        details = entry[1] if len(entry) > 1 and isinstance(entry[1], dict) else {}
        players = details.get("players")
        if not isinstance(players, dict):
            players = {}
        moves = []
        for j in range(int(players.get("count", 0))):
            player = players[str(j)]["player"]
            info = _flatten(player[0])
            data = player[1]["transaction_data"]
            data = data[0] if isinstance(data, list) else data
            action = data["type"]
            via = None
            if action == "add":
                via = data.get("source_type")
            elif action == "drop":
                via = data.get("destination_type")
            moves.append(
                Move(
                    player_key=info["player_key"],
                    name=info["name"]["full"],
                    action=action,
                    from_team=data.get("source_team_key"),
                    to_team=data.get("destination_team_key"),
                    via=via,
                )
            )
        if moves:
            parsed.append(
                Transaction(
                    transaction_id=str(meta["transaction_id"]),
                    timestamp=int(meta["timestamp"]),
                    type=meta["type"],
                    moves=tuple(moves),
                )
            )
    return sorted(parsed, key=lambda t: (t.timestamp, int(t.transaction_id)))


def transaction_player_keys(raw: dict[str, Any]) -> list[str]:
    """Every player involved in a transaction, in first-seen order."""
    keys = [m.player_key for t in parse_transactions(raw) for m in t.moves]
    return list(dict.fromkeys(keys))


def ownership(
    draft: list[tuple[str, str]], draft_time: int, transactions: list[Transaction]
) -> dict[str, list[Stint]]:
    """Each player's stints, from draft results (player_key, team_key) and transactions."""
    stints: dict[str, list[Stint]] = {}
    for player_key, team_key in draft:
        stints.setdefault(player_key, []).append(Stint(team_key, draft_time, None, "draft"))

    for tx in transactions:
        for move in tx.moves:
            history = stints.setdefault(move.player_key, [])
            current = history[-1] if history and history[-1].end is None else None
            if current and move.from_team in (None, current.team_key):
                if move.to_team != current.team_key:
                    current.end = tx.timestamp
                    current.left = "trade" if move.action == "trade" else "drop"
            if move.to_team and (not current or current.end is not None):
                history.append(Stint(move.to_team, tx.timestamp, None, move.action))
    return stints


def kept_share(stints: list[Stint], team_key: str, start: int, end: int) -> float:
    """Fraction of the season (start..end) the team had the player."""
    if end <= start:
        return 0.0
    held = 0
    for stint in stints:
        if stint.team_key != team_key:
            continue
        lo = max(stint.start, start)
        hi = min(stint.end if stint.end is not None else end, end)
        held += max(0, hi - lo)
    return round(min(held / (end - start), 1.0), 3)


def season_bounds(settings: dict[str, Any]) -> tuple[int, int]:
    """Timestamps for the first and last day of the season."""
    start = date.fromisoformat(settings["start_date"])
    end = date.fromisoformat(settings["end_date"])
    return (
        int(datetime.combine(start, time.min, LEAGUE_TZ).timestamp()),
        int(datetime.combine(end, time.max, LEAGUE_TZ).timestamp()),
    )


def to_date(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, LEAGUE_TZ).date().isoformat()


def stint_json(stint: Stint) -> dict[str, Any]:
    return {
        "team_key": stint.team_key,
        "start": to_date(stint.start),
        "end": to_date(stint.end),
        "acquired": stint.acquired,
        "left": stint.left,
    }
