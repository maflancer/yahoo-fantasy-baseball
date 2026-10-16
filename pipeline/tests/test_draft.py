import pytest

from fantasy_pipeline.build import build_season, season_summary
from fantasy_pipeline.draft import (
    BUST_RANK,
    HIGHLIGHTS,
    STEAL_MIN_KEPT,
    STEAL_MIN_ROUND,
    build_draft,
    busts,
    parse_players,
    steals,
    tenure,
)
from fantasy_pipeline.transactions import Stint, ownership, parse_transactions, season_bounds

VARGAS = "469.p.11781"
JAHN = "469.l.83828.t.2"
DRAFT_TIME = 1774313100


@pytest.fixture
def draft_results(fixture):
    return fixture("draft_results")


@pytest.fixture
def players(fixture):
    return parse_players(fixture("draft_players"), 2026)


@pytest.fixture
def draft(draft_results, players, fixture):
    drafted = [(f"469.p.{r['player_id']}", r["team_key"]) for r in draft_results]
    stints = ownership(drafted, DRAFT_TIME, parse_transactions(fixture("transactions")))
    season = season_bounds({"start_date": "2026-03-25", "end_date": "2026-09-20"})
    return build_draft(draft_results, players, "469", stints, season)


def test_parse_players_uses_this_seasons_rank(players):
    ohtani = players["469.p.1000001"]
    assert ohtani.name == "Shohei Ohtani (Batter)"
    assert ohtani.mlb_team == "LAD"
    assert ohtani.position == "Util"
    # The fixture also has his 2025 rank (2); only the 2026 rank should be used.
    assert ohtani.season_rank == 21


def test_parse_players_skips_empty_pages():
    empty = {"fantasy_content": {"league": [{}, {"players": []}]}}
    assert parse_players([empty], 2026) == {}


def test_every_pick_is_matched_to_a_player(draft):
    assert draft["num_picks"] == 294
    assert [p["pick"] for p in draft["picks"]] == list(range(1, 295))
    assert all(p["rank"] is not None and p["name"] for p in draft["picks"])
    first = draft["picks"][0]
    assert {k: first[k] for k in ("pick", "round", "team_key", "name", "rank")} == {
        "pick": 1,
        "round": 1,
        "team_key": "469.l.83828.t.8",
        "name": "Shohei Ohtani (Batter)",
        "rank": 21,
    }
    assert "value" not in first


def test_vargas_tenure_shows_he_was_dropped(draft):
    [vargas] = [p for p in draft["picks"] if p["player_key"] == VARGAS]
    assert vargas["team_key"] == JAHN
    assert vargas["tenure"]["left"] == "drop"
    assert vargas["tenure"]["left_date"] == "2026-03-27"
    assert vargas["tenure"]["next_team_key"] == "469.l.83828.t.11"
    assert vargas["tenure"]["kept_share"] < 0.05
    # A great season rank, but Jahn didn't keep him, so he isn't Jahn's steal.
    assert vargas["pick"] not in draft["steals"]


def test_kept_all_season(draft):
    kept = [p for p in draft["picks"] if p["tenure"]["left"] is None]
    assert kept
    assert all(p["tenure"]["kept_share"] == 1.0 for p in kept)
    assert all(p["tenure"]["next_team_key"] is None for p in kept)


def test_tenure_without_history():
    assert tenure([], "t.1", (0, 100)) == {
        "kept_share": 0.0,
        "left": None,
        "left_date": None,
        "next_team_key": None,
    }


def test_tenure_traded_away():
    stints = [Stint("t.1", 0, 40, "draft", "trade"), Stint("t.2", 40, None, "trade")]
    result = tenure(stints, "t.1", (0, 100))
    assert result["left"] == "trade"
    assert result["kept_share"] == 0.4
    assert result["next_team_key"] == "t.2"


def pick(n, round_, rank, kept=1.0):
    return {"pick": n, "round": round_, "rank": rank, "tenure": {"kept_share": kept}}


def test_steals_rule():
    picks = [
        pick(1, 1, 5),  # too early to be a steal
        pick(150, STEAL_MIN_ROUND, 30),
        pick(200, 15, 10),
        pick(250, 18, 3, kept=STEAL_MIN_KEPT - 0.01),  # dropped too soon
        pick(260, 19, None),
    ]
    assert [p["pick"] for p in steals(picks)] == [200, 150]


def test_busts_rule():
    picks = [
        pick(1, 1, BUST_RANK + 1),
        pick(2, 1, BUST_RANK),  # just inside the cutoff
        pick(30, 3, None),  # no rank counts as a bust
        pick(80, 6, 900),  # too late to be a bust
    ]
    assert [p["pick"] for p in busts(picks)] == [1, 30]


def test_highlights_capped(draft):
    assert 0 < len(draft["steals"]) <= HIGHLIGHTS
    assert 0 < len(draft["busts"]) <= HIGHLIGHTS


def test_season_includes_draft_and_moves(raw_season, draft_results, fixture):
    docs = build_season(raw_season)
    assert "draft.json" not in docs and "moves.json" not in docs
    summary = season_summary(raw_season, "")
    assert summary["has_draft"] is False and summary["has_moves"] is False

    raw_season.draft_results = draft_results
    raw_season.transactions = fixture("transactions")
    raw_season.players = fixture("draft_players")
    docs = build_season(raw_season)
    assert len(docs["draft.json"]["picks"]) == 294
    assert docs["moves.json"]["transactions"]
    summary = season_summary(raw_season, "")
    assert summary["has_draft"] is True and summary["has_moves"] is True
