from fantasy_pipeline.parse import managers_by_team, parse_matchups, parse_scoreboard, week_dates


def test_stat_categories_skip_display_only_and_read_sort_order(categories):
    abbrs = [c.abbr for c in categories]
    assert "H/AB" not in abbrs
    assert abbrs == ["R", "HR", "RBI", "SB", "TB", "AVG", "OBP", "IP", "K", "ERA", "WHIP", "SV+H"]
    lower = {c.abbr for c in categories if not c.higher_is_better}
    assert lower == {"ERA", "WHIP"}


def test_regular_week_has_every_team(week1, categories):
    rows = parse_matchups(week1, categories)
    assert len(rows) == 14
    assert {r.week for r in rows} == {1}
    assert not any(r.is_playoffs for r in rows)
    assert all(set(r.stats) == {c.abbr for c in categories} for r in rows)


def test_playoff_week_uses_actual_matchup_count(week23, categories):
    rows = parse_matchups(week23, categories)
    assert len(rows) == 8
    assert all(r.is_playoffs for r in rows)


def test_opponents_are_symmetric(week1, categories):
    rows = {r.team_key: r for r in parse_matchups(week1, categories)}
    for row in rows.values():
        assert rows[row.opponent_key].opponent_key == row.team_key


def test_results_and_ties(week1, categories):
    rows = parse_matchups(week1, categories)
    # Week 1 matchup 0 was a tie; the other six have a winner and a loser.
    assert sum(r.result == "T" for r in rows) == 2
    assert sum(r.result == "W" for r in rows) == 6
    assert sum(r.result == "L" for r in rows) == 6


def test_manager_nickname_not_team_name(week1, categories):
    rows = parse_matchups(week1, categories)
    assert all(not r.manager.startswith("Team ") for r in rows)


def test_week_dates(week1):
    start, end = week_dates(week1)
    assert start < end


def test_managers_by_team(teams):
    managers = managers_by_team(teams)
    assert len(managers) == 14
    assert all(not name.startswith("Team ") for name in managers.values())


def test_scoreboard_points_and_tied_categories(week1, categories):
    matchups = parse_scoreboard(week1, categories)
    assert len(matchups) == 7
    # Matchup 3 went 7-4 with home runs tied.
    m = matchups[3]
    assert [side.points for side in m.sides] == [7, 4]
    assert m.stat_winners["HR"] is None
    assert sum(winner is None for winner in m.stat_winners.values()) == 1
    # Points match the number of categories each side won.
    for side in m.sides:
        assert side.points == sum(w == side.team_key for w in m.stat_winners.values())


def test_scoreboard_playoff_week(week23, categories):
    matchups = parse_scoreboard(week23, categories)
    assert len(matchups) == 4
    assert all(m.is_playoffs and m.winner_key for m in matchups)
