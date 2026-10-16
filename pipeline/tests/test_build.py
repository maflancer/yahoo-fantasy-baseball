import json

from fantasy_pipeline.build import build_season, season_summary
from fantasy_pipeline.output import update_seasons_index, write_season


def test_build_season_documents(raw_season):
    docs = build_season(raw_season, name_map={})
    assert set(docs) == {"standings.json", "scoreboard.json", "stats.json"}

    standings = docs["standings.json"]["standings"]
    assert len(standings) == 14
    assert [r["rank"] for r in standings] == list(range(1, 15))
    assert all(isinstance(r["wins"], int) for r in standings)

    weeks = docs["scoreboard.json"]["weeks"]
    assert [w["week"] for w in weeks] == [1, 23]
    assert [w["is_playoffs"] for w in weeks] == [False, True]

    assert [len(w["matchups"]) for w in weeks] == [7, 4]
    assert all(w["leaders"] for w in weeks)


def test_scoreboard_matchup_shape(raw_season):
    week1 = build_season(raw_season, {})["scoreboard.json"]["weeks"][0]
    tie, win = week1["matchups"][0], week1["matchups"][1]

    assert tie["winner_key"] is None
    assert [t["points"] for t in tie["teams"]] == [6, 6]

    assert [t["points"] for t in win["teams"]] == [9, 3]
    assert win["winner_key"] == win["teams"][0]["team_key"]
    assert len(win["stat_winners"]) == 12
    assert set(win["stat_winners"].values()) <= {t["team_key"] for t in win["teams"]} | {None}


def test_playoff_rounds_labelled(raw_season):
    week1, week23 = build_season(raw_season, {})["scoreboard.json"]["weeks"]
    assert all("round" not in m for m in week1["matchups"])
    assert [m["round"] for m in week23["matchups"]] == ["Quarterfinal"] * 4
    assert all(m["for_title"] for m in week23["matchups"])


def test_team_names_never_exposed(raw_season):
    docs = build_season(raw_season, name_map={})
    text = json.dumps(docs)
    # Fixture team names are "Team N"; output should only use manager nicknames.
    assert '"Team ' not in text


def test_name_map_overrides_nickname(raw_season):
    plain = build_season(raw_season, name_map={})["standings.json"]["teams"]
    nickname = plain[0]["name"]
    mapped = build_season(raw_season, name_map={nickname: "Renamed"})["standings.json"]["teams"]
    assert mapped[0]["name"] == "Renamed"
    assert [t["name"] for t in mapped[1:]] == [t["name"] for t in plain[1:]]


def test_season_summary(raw_season):
    summary = season_summary(raw_season, "2026-10-01T00:00:00+00:00")
    assert summary == {
        "year": 2026,
        "name": "Test League",
        "league_key": "",
        "num_teams": 14,
        "playoff_start_week": 23,
        "is_finished": True,
        "updated_at": "2026-10-01T00:00:00+00:00",
    }


def test_write_season_reports_changes(tmp_path, raw_season):
    docs = build_season(raw_season, {})
    assert write_season(tmp_path, 2026, docs) is True
    assert (tmp_path / "2026" / "scoreboard.json").exists()
    assert write_season(tmp_path, 2026, docs) is False


def test_unchanged_data_keeps_updated_at(tmp_path):
    update_seasons_index(tmp_path, {"year": 2026, "updated_at": "old"})
    [kept] = update_seasons_index(tmp_path, {"year": 2026, "updated_at": "new"}, False)
    assert kept["updated_at"] == "old"
    [bumped] = update_seasons_index(tmp_path, {"year": 2026, "updated_at": "new"}, True)
    assert bumped["updated_at"] == "new"


def test_seasons_index_order(tmp_path):

    update_seasons_index(tmp_path, {"year": 2025, "name": "old"})
    update_seasons_index(tmp_path, {"year": 2026, "name": "first"})
    seasons = update_seasons_index(tmp_path, {"year": 2026, "name": "second"})
    assert seasons == [{"year": 2026, "name": "second"}, {"year": 2025, "name": "old"}]
