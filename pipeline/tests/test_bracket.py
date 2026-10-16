import pytest

from fantasy_pipeline.bracket import ordinal, replay_playoffs, round_name
from fantasy_pipeline.parse import Matchup, MatchupSide


def game(week: int, a: str, b: str, winner: str | None, consolation: bool = False) -> Matchup:
    return Matchup(
        week=week,
        sides=(MatchupSide(a, a, 0, {}), MatchupSide(b, b, 0, {})),
        winner_key=winner,
        is_playoffs=True,
        is_consolation=consolation,
        stat_winners={},
    )


def regular(week: int, a: str, b: str) -> Matchup:
    return Matchup(week, (MatchupSide(a, a, 0, {}), MatchupSide(b, b, 0, {})), a, False, False, {})


# An 8-team bracket where the better seed always wins, plus a regular-season week.
EIGHT_TEAM = {
    21: [regular(21, "s1", "s2")],
    22: [game(22, "s1", "s8", "s1"), game(22, "s4", "s5", "s4"),
         game(22, "s2", "s7", "s2"), game(22, "s3", "s6", "s3")],
    23: [game(23, "s1", "s4", "s1"), game(23, "s2", "s3", "s2"),
         game(23, "s8", "s5", "s5"), game(23, "s7", "s6", "s6")],
    24: [game(24, "s1", "s2", "s1"), game(24, "s4", "s3", "s3"),
         game(24, "s5", "s6", "s5"), game(24, "s8", "s7", "s7")],
}  # fmt: skip


def names(labels, week):
    return [labels[(week, i)].name for i in range(len(EIGHT_TEAM[week]))]


def test_eight_team_bracket_rounds():
    labels, _ = replay_playoffs(EIGHT_TEAM, 8)
    assert (21, 0) not in labels
    assert names(labels, 22) == ["Quarterfinal"] * 4
    assert names(labels, 23) == [
        "Semifinal",
        "Semifinal",
        "Consolation (5th–8th)",
        "Consolation (5th–8th)",
    ]
    assert names(labels, 24) == [
        "Championship",
        "3rd place game",
        "5th place game",
        "7th place game",
    ]


def test_for_title_only_while_first_place_is_possible():
    labels, _ = replay_playoffs(EIGHT_TEAM, 8)
    assert labels[(24, 0)].for_title
    assert not labels[(24, 1)].for_title
    assert labels[(23, 1)].for_title
    assert not labels[(23, 2)].for_title


def test_final_places():
    _, places = replay_playoffs(EIGHT_TEAM, 8)
    assert places == {f"s{n}": (n, n) for n in range(1, 9)}


def test_upsets_follow_the_winner():
    weeks = {
        1: [game(1, "a", "b", "b"), game(1, "c", "d", "c")],
        2: [game(2, "b", "c", "c"), game(2, "a", "d", "a")],
    }
    labels, places = replay_playoffs(weeks, 4)
    assert [labels[(2, i)].name for i in range(2)] == ["Championship", "3rd place game"]
    assert places == {"c": (1, 1), "b": (2, 2), "a": (3, 3), "d": (4, 4)}


def test_consolation_flag_from_yahoo():
    weeks = {1: [game(1, "a", "b", "a"), game(1, "x", "y", "x", consolation=True)]}
    labels, _ = replay_playoffs(weeks, 2)
    assert labels[(1, 0)].name == "Championship"
    assert labels[(1, 1)].name == "Consolation"


def test_unexpected_team_count_falls_back():
    # 6-team bracket with byes: only 4 teams play the first week.
    weeks = {1: [game(1, "a", "b", "a"), game(1, "c", "d", "c")]}
    labels, _ = replay_playoffs(weeks, 6)
    assert {label.name for label in labels.values()} == {"Playoffs"}


def test_tied_playoff_matchup_falls_back():
    weeks = {1: [game(1, "a", "b", None), game(1, "c", "d", "c")]}
    labels, _ = replay_playoffs(weeks, 4)
    assert labels[(1, 0)].name == "Playoffs"
    assert labels[(1, 1)].name == "Semifinal"


def test_no_playoffs():
    assert replay_playoffs({1: [regular(1, "a", "b")]}, 8) == ({}, {})


@pytest.mark.parametrize(
    ("n", "expected"), [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (21, "21st")]
)
def test_ordinal(n, expected):
    assert ordinal(n) == expected


def test_round_name_larger_brackets():
    assert round_name((1, 16)) == "Round of 16"
    assert round_name((9, 12)) == "Consolation (9th–12th)"
