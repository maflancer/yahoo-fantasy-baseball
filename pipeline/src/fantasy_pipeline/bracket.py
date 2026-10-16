"""Label playoff matchups (Quarterfinal, Semifinal, Championship, placement games).

Yahoo only flags matchups as playoffs or consolation, so the round is derived by
replaying the bracket: every playoff team starts competing for places 1..N, and
each matchup splits that range in half, with the winner taking the top half and
the loser the bottom half. A matchup for places 1-2 is the championship, 3-4 the
third-place game, and so on.
"""

from __future__ import annotations

from dataclasses import dataclass

from fantasy_pipeline.parse import Matchup

PlaceRange = tuple[int, int]


@dataclass(frozen=True)
class RoundLabel:
    name: str  # e.g. "Championship", "Semifinal", "5th place game"
    for_title: bool  # True while the winner can still finish first
    order: int = 0  # best place at stake; sorts title games before placement games


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def round_name(places: PlaceRange) -> str:
    lo, hi = places
    size = hi - lo + 1
    if lo == 1:
        return {2: "Championship", 4: "Semifinal", 8: "Quarterfinal"}.get(size, f"Round of {size}")
    if size == 2:
        return f"{ordinal(lo)} place game"
    return f"Consolation ({ordinal(lo)}–{ordinal(hi)})"


def replay_playoffs(
    weeks: dict[int, list[Matchup]], num_playoff_teams: int | None
) -> tuple[dict[tuple[int, int], RoundLabel], dict[str, PlaceRange]]:
    """Labels keyed by (week, matchup index) for every playoff matchup, plus the
    range of places each playoff team can still finish in after the last week.

    Brackets that can't be replayed cleanly (byes, ties, team counts that don't
    match the settings) fall back to a plain "Playoffs" label rather than guessing.
    """
    labels: dict[tuple[int, int], RoundLabel] = {}
    playoff_weeks = sorted(w for w, ms in weeks.items() if any(m.is_playoffs for m in ms))
    if not playoff_weeks:
        return labels, {}

    first = [m for m in weeks[playoff_weeks[0]] if m.is_playoffs and not m.is_consolation]
    teams = {side.team_key for m in first for side in m.sides}
    places: dict[str, PlaceRange] = {}
    if num_playoff_teams and len(teams) == num_playoff_teams:
        places = dict.fromkeys(teams, (1, num_playoff_teams))

    for week in playoff_weeks:
        updates: dict[str, PlaceRange] = {}
        for i, matchup in enumerate(weeks[week]):
            if not matchup.is_playoffs:
                continue
            if matchup.is_consolation:
                labels[(week, i)] = RoundLabel("Consolation", False, 1000)
                continue

            keys = [side.team_key for side in matchup.sides]
            ranges = {places.get(k) for k in keys}
            if len(keys) != 2 or len(ranges) != 1 or None in ranges or not matchup.winner_key:
                labels[(week, i)] = RoundLabel("Playoffs", True)
                continue

            (lo, hi) = ranges.pop()
            labels[(week, i)] = RoundLabel(round_name((lo, hi)), lo == 1, lo)
            if hi > lo:
                mid = lo + (hi - lo + 1) // 2
                loser = keys[1] if keys[0] == matchup.winner_key else keys[0]
                updates[matchup.winner_key] = (lo, mid - 1)
                updates[loser] = (mid, hi)
        places.update(updates)

    return labels, places
