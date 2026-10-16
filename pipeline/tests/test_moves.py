import pytest

from fantasy_pipeline.draft import parse_players
from fantasy_pipeline.moves import TOP_PICKUPS, build_moves, move_json
from fantasy_pipeline.transactions import ownership, parse_transactions

VARGAS = "469.p.11781"


@pytest.fixture
def moves(fixture):
    draft_results = fixture("draft_results")
    transactions = parse_transactions(fixture("transactions"))
    players = parse_players(fixture("draft_players"), 2026)
    drafted = [(f"469.p.{r['player_id']}", r["team_key"]) for r in draft_results]
    stints = ownership(drafted, 1774313100, transactions)
    return build_moves(transactions, draft_results, "469", 1774313100, players, stints)


def test_log_is_newest_first_with_draft_last(moves):
    entries = moves["transactions"]
    season_moves = [e for e in entries if e["type"] != "draft"]
    draft = [e for e in entries if e["type"] == "draft"]
    assert entries == season_moves + draft
    dates = [e["date"] for e in season_moves]
    assert dates == sorted(dates, reverse=True)
    assert [e["pick"] for e in draft] == list(range(1, 295))
    assert draft[0]["moves"] == [
        {"player_key": "469.p.1000001", "action": "draft", "to_team_key": "469.l.83828.t.8"}
    ]


def test_every_player_in_log_has_details(moves):
    keys = {m["player_key"] for e in moves["transactions"] for m in e["moves"]}
    assert keys == set(moves["players"])
    assert moves["players"][VARGAS] == {
        "name": "Miguel Vargas",
        "position": "1B,3B",
        "mlb_team": "CWS",
        "rank": 12,
    }


def test_top_pickups(moves):
    pickups = moves["top_pickups"]
    assert 0 < len(pickups) <= TOP_PICKUPS
    assert pickups[0]["player_key"] == VARGAS
    assert [s["acquired"] for s in pickups[0]["stints"]] == ["draft", "add", "add"]
    assert pickups[0]["stints"][-1]["end"] is None


def test_move_json_omits_missing_fields():
    assert move_json("p", "drop", "t.1", None, "waivers") == {
        "player_key": "p",
        "action": "drop",
        "from_team_key": "t.1",
        "via": "waivers",
    }
