import pytest

from fantasy_pipeline.build import build_season, season_summary
from fantasy_pipeline.draft import UNDRAFTED_LIMIT, build_draft, parse_players, pick_value


@pytest.fixture
def draft_results(fixture):
    return fixture("draft_results")


@pytest.fixture
def players(fixture):
    return parse_players(fixture("draft_players"), 2026)


@pytest.fixture
def draft(draft_results, players):
    return build_draft(draft_results, players, "469")


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


@pytest.mark.parametrize(
    ("pick", "rank", "expected"),
    [
        (1, 21, -20),  # first pick finished 21st
        (250, 20, 230),  # late-round steal
        (1, 900, -294),  # rank capped one past the last pick
        (290, 900, -5),  # late flier who busted barely counts
        (10, None, None),
    ],
)
def test_pick_value(pick, rank, expected):
    assert pick_value(pick, rank, num_picks=294) == expected


def test_every_pick_is_matched_to_a_player(draft):
    assert draft["num_picks"] == 294
    assert [p["pick"] for p in draft["picks"]] == list(range(1, 295))
    assert all(p["rank"] is not None and p["name"] for p in draft["picks"])
    first = draft["picks"][0]
    assert first == {
        "pick": 1,
        "round": 1,
        "team_key": "469.l.83828.t.8",
        "player_key": "469.p.1000001",
        "name": "Shohei Ohtani (Batter)",
        "mlb_team": "LAD",
        "position": "Util",
        "rank": 21,
        "value": -20,
    }


def test_undrafted_are_best_ranked_players_nobody_picked(draft):
    undrafted = draft["undrafted"]
    drafted = {p["player_key"] for p in draft["picks"]}
    assert 0 < len(undrafted) <= UNDRAFTED_LIMIT
    assert not drafted & {p["player_key"] for p in undrafted}
    ranks = [p["rank"] for p in undrafted]
    assert ranks == sorted(ranks)


def test_missing_player_details_still_listed():
    results = [{"pick": 1, "round": 1, "team_key": "1.l.1.t.1", "player_id": 5}]
    [pick] = build_draft(results, {}, "1")["picks"]
    assert pick["name"] == "1.p.5"
    assert pick["rank"] is None and pick["value"] is None


def test_season_includes_draft_when_drafted(raw_season, draft_results, fixture):
    assert "draft.json" not in build_season(raw_season)
    assert season_summary(raw_season, "")["has_draft"] is False

    raw_season.draft_results = draft_results
    raw_season.players = fixture("draft_players")
    doc = build_season(raw_season)["draft.json"]
    assert len(doc["picks"]) == 294
    assert doc["teams"]
    assert season_summary(raw_season, "")["has_draft"] is True
