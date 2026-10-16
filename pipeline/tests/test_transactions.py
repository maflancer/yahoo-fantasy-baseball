import pytest

from fantasy_pipeline.transactions import (
    Move,
    Stint,
    Transaction,
    kept_share,
    ownership,
    parse_transactions,
    season_bounds,
    to_date,
    transaction_player_keys,
)

VARGAS = "469.p.11781"


@pytest.fixture
def transactions(fixture):
    return parse_transactions(fixture("transactions"))


def by_name(transactions, name):
    return [(t, m) for t in transactions for m in t.moves if m.name == name]


def test_parse_skips_transactions_without_players(transactions, fixture):
    raw_count = fixture("transactions")["fantasy_content"]["league"][1]["transactions"]["count"]
    assert 0 < len(transactions) < raw_count  # commissioner entries have no players
    assert {t.type for t in transactions} == {"add", "add/drop", "drop", "trade"}
    stamps = [t.timestamp for t in transactions]
    assert stamps == sorted(stamps)


def test_parse_add_drop_fields(transactions):
    tx, add = by_name(transactions, "José Alvarado")[0]
    assert tx.type == "add/drop"
    assert add.action == "add" and add.via == "freeagents"
    assert add.from_team is None and add.to_team == "469.l.83828.t.1"
    _, drop = by_name(transactions, "Jacob Misiorowski")[0]
    assert drop.action == "drop" and drop.to_team is None and drop.via == "waivers"


def test_parse_trade(transactions):
    [trade, *_] = [t for t in transactions if t.type == "trade"]
    assert all(m.action == "trade" and m.from_team and m.to_team for m in trade.moves)


def test_unsuccessful_transactions_ignored():
    raw = {
        "fantasy_content": {
            "league": [
                {},
                {
                    "transactions": {
                        "count": 1,
                        "0": {
                            "transaction": [
                                {
                                    "transaction_id": "9",
                                    "type": "add",
                                    "status": "vetoed",
                                    "timestamp": "1",
                                },
                                [],
                            ]
                        },
                    }
                },
            ]
        }
    }
    assert parse_transactions(raw) == []


def test_parse_empty():
    assert parse_transactions({}) == []


def test_player_keys_unique(fixture):
    keys = transaction_player_keys(fixture("transactions"))
    assert len(keys) == len(set(keys))
    assert VARGAS in keys


def test_vargas_ownership(transactions):
    """Drafted by Jahn, dropped two days in, picked up by Zach, then nathan for good."""
    stints = ownership([(VARGAS, "469.l.83828.t.2")], 100, transactions)[VARGAS]
    assert [(s.team_key, s.acquired, s.left) for s in stints] == [
        ("469.l.83828.t.2", "draft", "drop"),
        ("469.l.83828.t.11", "add", "drop"),
        ("469.l.83828.t.7", "add", None),
    ]
    assert stints[0].start == 100
    assert to_date(stints[0].end) == "2026-03-27"
    assert stints[-1].end is None


def test_trade_moves_player_between_teams():
    a, b = "t.1", "t.2"
    txs = [
        Transaction("1", 10, "add", (Move("p", "P", "add", None, a, "freeagents"),)),
        Transaction("2", 20, "trade", (Move("p", "P", "trade", a, b, None),)),
        Transaction("3", 30, "drop", (Move("p", "P", "drop", b, None, "waivers"),)),
    ]
    stints = ownership([], 0, txs)["p"]
    assert [(s.team_key, s.start, s.end, s.acquired, s.left) for s in stints] == [
        (a, 10, 20, "add", "trade"),
        (b, 20, 30, "trade", "drop"),
    ]


def test_kept_share():
    stints = [
        Stint("a", 0, 25, "draft", "drop"),
        Stint("b", 25, None, "add"),
        Stint("a", 75, 100, "add"),
    ]
    assert kept_share(stints, "a", 0, 100) == 0.5
    assert kept_share(stints, "b", 0, 100) == 0.75
    assert kept_share(stints, "c", 0, 100) == 0.0
    assert kept_share(stints, "a", 50, 50) == 0.0


def test_season_bounds_use_eastern_time():
    start, end = season_bounds({"start_date": "2026-03-25", "end_date": "2026-09-20"})
    assert to_date(start) == "2026-03-25"
    assert to_date(end) == "2026-09-20"
    assert to_date(None) is None
