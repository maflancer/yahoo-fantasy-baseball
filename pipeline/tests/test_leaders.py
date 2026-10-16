import pytest

from fantasy_pipeline.leaders import season_leaders, stat_sort_value, week_leaders
from fantasy_pipeline.parse import StatCategory, TeamWeek, parse_matchups

RUNS = StatCategory("7", "R", "Runs", True, "B")
ERA = StatCategory("26", "ERA", "Earned Run Average", False, "P")
IP = StatCategory("50", "IP", "Innings Pitched", True, "P")


def team(key: str, week: int = 1, **stats: str) -> TeamWeek:
    return TeamWeek(
        week=week,
        team_key=key,
        manager=key,
        opponent_key="",
        result="W",
        is_playoffs=False,
        is_consolation=False,
        stats=stats,
    )


@pytest.mark.parametrize(
    ("abbr", "raw", "expected"),
    [
        ("R", "24", 24.0),
        ("AVG", ".284", 0.284),
        ("IP", "64.2", 194),  # 64 innings + 2 outs
        ("IP", "64", 192),
        ("ERA", "-", None),
        ("ERA", "", None),
        ("R", None, None),
    ],
)
def test_stat_sort_value(abbr, raw, expected):
    assert stat_sort_value(abbr, raw) == expected


def test_higher_is_better_with_tie():
    rows = [team("a", R="10"), team("b", R="12"), team("c", R="12")]
    [leader] = week_leaders(rows, [RUNS])
    assert leader == {"stat": "R", "value": "12", "team_keys": ["b", "c"]}


def test_lower_is_better():
    rows = [team("a", ERA="3.50"), team("b", ERA="1.20"), team("c", ERA="4.00")]
    [leader] = week_leaders(rows, [ERA])
    assert leader["team_keys"] == ["b"]


def test_lower_is_better_ignores_missing_values():
    # A team with no innings pitched has no ERA, so it can't "lead" ERA.
    rows = [team("a", ERA="-"), team("b", ERA="2.00")]
    [leader] = week_leaders(rows, [ERA])
    assert leader["team_keys"] == ["b"]


def test_innings_compared_as_outs():
    # As decimals 64.2 > 64.10 would be wrong; 64.2 is 194 outs, 64.1 is 193.
    rows = [team("a", IP="64.1"), team("b", IP="64.2"), team("c", IP="63.2")]
    [leader] = week_leaders(rows, [IP])
    assert leader["team_keys"] == ["b"]


def test_category_with_no_values_is_skipped():
    assert week_leaders([team("a", ERA="-")], [ERA]) == []


def test_season_leaders_groups_by_week():
    rows = [team("a", 2, R="5"), team("b", 1, R="9"), team("a", 1, R="3")]
    weeks = season_leaders(rows, [RUNS], {1: ("2026-03-25", "2026-04-05")})
    assert [w["week"] for w in weeks] == [1, 2]
    assert weeks[0]["start"] == "2026-03-25"
    assert weeks[0]["leaders"][0]["team_keys"] == ["b"]
    assert weeks[1]["start"] == ""


def test_real_week_has_leader_for_every_category(week1, categories):
    leaders = week_leaders(parse_matchups(week1, categories), categories)
    assert [leader["stat"] for leader in leaders] == [c.abbr for c in categories]
    assert all(leader["team_keys"] for leader in leaders)
