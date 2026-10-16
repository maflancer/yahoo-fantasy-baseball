import pytest

from fantasy_pipeline.build import build_season
from fantasy_pipeline.parse import StatCategory, parse_stat_categories
from fantasy_pipeline.stats import aggregation, row_parts


def cat(stat_id: str, abbr: str, position: str = "B") -> StatCategory:
    return StatCategory(stat_id, abbr, abbr, True, position)


@pytest.mark.parametrize(
    ("category", "values", "expected"),
    [
        (cat("12", "HR"), ["3", "10"], {"type": "sum"}),
        (cat("50", "IP", "P"), ["64.2"], {"type": "innings"}),
        (
            cat("3", "AVG"),
            [".275"],
            {"type": "ratio", "num": "H", "den": "AB", "scale": 1, "decimals": 3},
        ),
        (
            cat("26", "ERA", "P"),
            ["4.52"],
            {"type": "ratio", "num": "ER", "den": "outs", "scale": 27, "decimals": 2},
        ),
        (
            cat("27", "WHIP", "P"),
            ["1.28"],
            {"type": "ratio", "num": "WH", "den": "outs", "scale": 3, "decimals": 2},
        ),
        (
            cat("4", "OBP"),
            [".353", "-"],
            {"type": "weighted", "weight": "AB", "decimals": 3, "approximate": True},
        ),
        (
            cat("57", "K/9", "P"),
            ["9.50"],
            {"type": "weighted", "weight": "outs", "decimals": 2, "approximate": True},
        ),
    ],
)
def test_aggregation(category, values, expected):
    assert aggregation(category, values) == expected


CATS = [cat("50", "IP", "P"), cat("26", "ERA", "P"), cat("27", "WHIP", "P")]


def test_row_parts_recovers_components():
    stats = {"H/AB": "66/240", "IP": "69.2", "ERA": "4.52", "WHIP": "1.28"}
    # 69.2 IP = 209 outs; ER = 4.52 * 209 / 27 = 34.99; H+BB = 1.28 * 209 / 3 = 89.2
    assert row_parts(stats, CATS) == {"H": 66, "AB": 240, "outs": 209, "ER": 35, "WH": 89}


def test_row_parts_without_innings():
    assert row_parts({"H/AB": "0/0", "IP": "0", "ERA": "-", "WHIP": "-"}, CATS) == {
        "H": 0,
        "AB": 0,
        "outs": 0,
        "ER": 0,
        "WH": 0,
    }


def test_row_parts_missing_stats():
    assert row_parts({}, CATS) == {}


@pytest.fixture
def stats_doc(raw_season):
    return build_season(raw_season, {})["stats.json"]


def test_one_row_per_team_week(stats_doc):
    rows = stats_doc["rows"]
    assert len(rows) == 14 + 8
    assert {r["week"] for r in rows} == {1, 23}
    assert all(r["round"] == "Quarterfinal" for r in rows if r["week"] == 23)
    assert all("round" not in r for r in rows if r["week"] == 1)


def test_rows_are_numeric(stats_doc):
    row = stats_doc["rows"][0]
    assert isinstance(row["values"]["HR"], int)
    assert isinstance(row["values"]["IP"], int)  # innings stored as outs
    assert isinstance(row["values"]["AVG"], float)
    assert set(row["parts"]) == {"H", "AB", "outs", "ER", "WH"}


def test_scores_and_results(stats_doc):
    for row in stats_doc["rows"]:
        mine, theirs = row["score"]
        if row["result"] == "W":
            assert mine >= theirs
        elif row["result"] == "L":
            assert mine <= theirs


def test_recovered_parts_reproduce_weekly_rates(stats_doc, settings_raw):
    """Recomputing each week's AVG/ERA/WHIP from the parts matches what Yahoo reported."""
    for row in stats_doc["rows"]:
        values, parts = row["values"], row["parts"]
        if parts["AB"]:
            assert round(parts["H"] / parts["AB"], 3) == pytest.approx(values["AVG"], abs=0.0005)
        if parts["outs"]:
            assert round(27 * parts["ER"] / parts["outs"], 2) == pytest.approx(
                values["ERA"], abs=0.006
            )
            assert round(3 * parts["WH"] / parts["outs"], 2) == pytest.approx(
                values["WHIP"], abs=0.006
            )


def test_display_only_stats_parsed(settings_raw):
    display = parse_stat_categories(settings_raw, display_only=True)
    assert [c.abbr for c in display] == ["H/AB"]
