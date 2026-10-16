"""Weekly category leaders."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fantasy_pipeline.parse import StatCategory, TeamWeek

INNINGS_ABBRS = {"IP"}


def stat_sort_value(abbr: str, value: str | None) -> float | None:
    """Numeric value for comparing a raw Yahoo stat, or None when it can't be compared.

    Innings are written as whole.outs ("64.2" is 64 and 2/3 innings), so they are
    compared as total outs rather than as decimals.
    """
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "-", "--"}:
        return None
    try:
        if abbr in INNINGS_ABBRS:
            whole, _, outs = text.partition(".")
            return int(whole or 0) * 3 + int(outs or 0)
        return float(text)
    except ValueError:
        return None


def week_leaders(rows: list[TeamWeek], categories: list[StatCategory]) -> list[dict[str, Any]]:
    """For each category, the best value that week and every team that hit it."""
    leaders = []
    for cat in categories:
        scored = [
            (score, row)
            for row in rows
            if (score := stat_sort_value(cat.abbr, row.stats.get(cat.abbr))) is not None
        ]
        if not scored:
            continue
        best = (max if cat.higher_is_better else min)(score for score, _ in scored)
        winners = [row for score, row in scored if score == best]
        leaders.append(
            {
                "stat": cat.abbr,
                "value": winners[0].stats[cat.abbr],
                "team_keys": [row.team_key for row in winners],
            }
        )
    return leaders


def season_leaders(
    rows: list[TeamWeek],
    categories: list[StatCategory],
    week_dates: dict[int, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    by_week: dict[int, list[TeamWeek]] = defaultdict(list)
    for row in rows:
        by_week[row.week].append(row)

    week_dates = week_dates or {}
    weeks = []
    for week in sorted(by_week):
        week_rows = by_week[week]
        start, end = week_dates.get(week, ("", ""))
        weeks.append(
            {
                "week": week,
                "start": start,
                "end": end,
                "is_playoffs": any(r.is_playoffs for r in week_rows),
                "leaders": week_leaders(week_rows, categories),
            }
        )
    return weeks
