"""Per team-week numeric stats, plus the rules for totalling them over any set of weeks.

Counting stats (HR, K, ...) are summed. Rate stats can't be summed or averaged, so
each row also carries the parts needed to recompute them:

- AVG = H / AB, using Yahoo's display-only H/AB stat (exact)
- ERA = 27 * ER / outs and WHIP = 3 * (H + BB) / outs, where ER and H + BB are
  recovered from the weekly ERA/WHIP and innings (exact up to Yahoo's rounding)
- any other rate stat (e.g. OBP) is averaged weighted by AB (batting) or outs
  (pitching), which is a close estimate and flagged as such
"""

from __future__ import annotations

from typing import Any

from fantasy_pipeline.leaders import stat_sort_value
from fantasy_pipeline.parse import Matchup, StatCategory

# Yahoo stat IDs, stable across leagues and seasons.
AVG_ID = "3"
ERA_ID = "26"
WHIP_ID = "27"
IP_ID = "50"
H_AB_ID = "60"


def aggregation(cat: StatCategory, values: list[str]) -> dict[str, Any]:
    """How the web app should total this category across weeks."""
    if cat.stat_id == IP_ID:
        return {"type": "innings"}
    if cat.stat_id == AVG_ID:
        return {"type": "ratio", "num": "H", "den": "AB", "scale": 1, "decimals": 3}
    if cat.stat_id == ERA_ID:
        return {"type": "ratio", "num": "ER", "den": "outs", "scale": 27, "decimals": 2}
    if cat.stat_id == WHIP_ID:
        return {"type": "ratio", "num": "WH", "den": "outs", "scale": 3, "decimals": 2}

    present = [v for v in values if stat_sort_value(cat.abbr, v) is not None]
    if all("." not in v for v in present):
        return {"type": "sum"}
    decimals = max((len(v.partition(".")[2]) for v in present), default=2)
    weight = "AB" if cat.position_type == "B" else "outs"
    return {"type": "weighted", "weight": weight, "decimals": decimals, "approximate": True}


def _compact(value: float | None) -> float | int | None:
    return int(value) if value is not None and float(value).is_integer() else value


def row_parts(stats: dict[str, str], categories: list[StatCategory]) -> dict[str, int]:
    """Components for recomputing rate stats: H, AB, outs, ER, WH (walks + hits)."""
    by_id = {c.stat_id: c.abbr for c in categories}
    parts: dict[str, int] = {}

    hits_ab = stats.get("H/AB", "")
    if "/" in hits_ab:
        hits, _, at_bats = hits_ab.partition("/")
        if hits.isdigit() and at_bats.isdigit():
            parts["H"], parts["AB"] = int(hits), int(at_bats)

    if IP_ID in by_id:
        outs = stat_sort_value("IP", stats.get(by_id[IP_ID]))
        if outs is not None:
            parts["outs"] = int(outs)
            # Earned runs and baserunners are whole numbers, so rounding recovers them.
            for stat_id, key, per_out in ((ERA_ID, "ER", 27), (WHIP_ID, "WH", 3)):
                rate = stat_sort_value("", stats.get(by_id.get(stat_id, ""), None))
                parts[key] = round(rate * outs / per_out) if rate is not None and outs else 0
    return parts


def build_stats(
    matchups_by_week: dict[int, list[Matchup]],
    categories: list[StatCategory],
    round_names: dict[tuple[int, int], str] | None = None,
) -> dict[str, Any]:
    """The categories (with aggregation rules) and one row per team per week."""
    round_names = round_names or {}
    rows = []
    values_by_abbr: dict[str, list[str]] = {c.abbr: [] for c in categories}

    for week in sorted(matchups_by_week):
        for i, matchup in enumerate(matchups_by_week[week]):
            for j, side in enumerate(matchup.sides):
                opponent = matchup.sides[1 - j] if len(matchup.sides) == 2 else None
                if matchup.winner_key is None:
                    result = "T"
                else:
                    result = "W" if side.team_key == matchup.winner_key else "L"
                values = {}
                for cat in categories:
                    raw = side.stats.get(cat.abbr)
                    if raw is not None:
                        values_by_abbr[cat.abbr].append(raw)
                    values[cat.abbr] = _compact(stat_sort_value(cat.abbr, raw))
                row: dict[str, Any] = {
                    "week": week,
                    "team_key": side.team_key,
                    "opponent_key": opponent.team_key if opponent else None,
                    "result": result,
                    "score": [side.points, opponent.points if opponent else 0],
                    "is_playoffs": matchup.is_playoffs,
                    "values": values,
                    "parts": row_parts(side.stats, categories),
                }
                if (week, i) in round_names:
                    row["round"] = round_names[(week, i)]
                rows.append(row)

    return {
        "categories": [
            {**cat.to_json(), "agg": aggregation(cat, values_by_abbr[cat.abbr])}
            for cat in categories
        ],
        "rows": rows,
    }
