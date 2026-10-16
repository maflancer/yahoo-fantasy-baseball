import pytest

from fantasy_pipeline.config import Season, load_config
from fantasy_pipeline.yahoo import last_completed_week


def write(tmp_path, text):
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def test_load_config_resolves_paths_relative_to_file(tmp_path):
    config = load_config(
        write(
            tmp_path,
            """
            output_dir = "out"
            [[seasons]]
            year = 2025
            [[seasons]]
            year = 2026
            league_id = "469.l.1"
            """,
        )
    )
    assert config.game == "mlb"
    assert config.output_dir == tmp_path.resolve() / "out"
    assert config.oauth_file == tmp_path.resolve() / "oauth2.json"
    assert config.latest_season == Season(2026, "469.l.1")
    assert config.season(2025) == Season(2025)
    # Years not in the config can still be backfilled.
    assert config.season(2019) == Season(2019)


def test_load_config_requires_seasons(tmp_path):
    with pytest.raises(ValueError, match="seasons"):
        load_config(write(tmp_path, 'game = "mlb"\n'))


def test_repo_config_is_valid():
    from pathlib import Path

    config = load_config(Path(__file__).parents[2] / "config.toml")
    assert config.seasons


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ({"is_finished": 1, "end_week": "25", "current_week": "25"}, 25),
        ({"current_week": "10", "end_week": "25"}, 9),
        ({"is_finished": "0", "current_week": "1", "end_week": "25"}, 0),
    ],
)
def test_last_completed_week(settings, expected):
    assert last_completed_week(settings) == expected
