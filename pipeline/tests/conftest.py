import json
from pathlib import Path

import pytest

from fantasy_pipeline.build import RawSeason
from fantasy_pipeline.parse import parse_stat_categories

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def fixture():
    """Load any saved Yahoo response by name."""
    return load


@pytest.fixture
def settings_raw():
    return load("settings_raw")


@pytest.fixture
def categories(settings_raw):
    return parse_stat_categories(settings_raw)


@pytest.fixture
def teams():
    return load("teams")


@pytest.fixture
def week1():
    return load("matchups_w1")


@pytest.fixture
def week23():
    """A playoff week: only 8 of 14 teams play."""
    return load("matchups_w23")


@pytest.fixture
def raw_season(settings_raw, week1, week23):
    return RawSeason(
        year=2026,
        settings={
            "name": "Test League",
            "num_teams": 14,
            "playoff_start_week": "23",
            "is_finished": 1,
            "num_playoff_teams": "8",
            "league_key": "469.l.83828",
            "start_date": "2026-03-25",
            "end_date": "2026-09-20",
            "draft_time": "1774313100",
        },
        settings_raw=settings_raw,
        standings=load("standings"),
        teams=load("teams"),
        matchups=[week1, week23],
    )
