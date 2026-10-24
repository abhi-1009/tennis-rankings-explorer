"""The parsers must turn nested API JSON into flat tables and fill missing values predictably."""
import pandas as pd

from api import transform


def test_competitions_are_flattened_and_categories_deduplicated(competitions_payload):
    categories, comps = transform.parse_competitions(competitions_payload)
    assert set(categories["category_id"]) == {"sr:category:3", "sr:category:72"}
    assert len(comps) == 3
    assert list(comps.columns) == ["competition_id", "competition_name", "parent_id", "type", "gender", "level", "category_id"]


def test_missing_competition_fields_get_safe_values(competitions_payload):
    _, comps = transform.parse_competitions(competitions_payload)
    mystery = comps.set_index("competition_id").loc["sr:competition:3"]
    assert mystery["gender"] == "unknown"
    assert pd.isna(mystery["category_id"])
    assert pd.isna(mystery["level"]) and pd.isna(mystery["parent_id"])


def test_parent_and_level_are_kept_when_present(competitions_payload):
    _, comps = transform.parse_competitions(competitions_payload)
    by_id = comps.set_index("competition_id")
    assert by_id.loc["sr:competition:2", "parent_id"] == "sr:competition:1"
    assert by_id.loc["sr:competition:1", "level"] == "atp_500"


def test_venues_are_flattened_with_their_complex(complexes_payload):
    complexes, venues = transform.parse_complexes(complexes_payload)
    assert len(complexes) == 3
    assert len(venues) == 3                                   # the empty complex adds a complex but no venue
    assert set(venues.loc[venues["venue_id"] == "sr:venue:1", "complex_id"]) == {"sr:complex:1"}


def test_missing_venue_fields_use_placeholders_and_codes_are_cut_to_three(complexes_payload):
    _, venues = transform.parse_complexes(complexes_payload)
    v2 = venues.set_index("venue_id").loc["sr:venue:2"]
    assert v2["timezone"] == "Unknown"
    assert v2["country_code"] == "CHI"                        # "CHILE" truncated to fit CHAR(3)
    v3 = venues.set_index("venue_id").loc["sr:venue:3"]
    assert (v3["city_name"], v3["country_code"]) == ("Unknown", "UNK")


def test_rankings_split_into_unique_competitors_and_ranking_rows(rankings_payload):
    competitors, rankings = transform.parse_doubles_rankings(rankings_payload)
    assert competitors["competitor_id"].is_unique
    assert set(competitors["competitor_id"]) == {"p1", "p2", "p3"}
    assert len(rankings) == 4                                 # p1 appears in two ranking lists
    assert set(rankings["ranking_name"]) == {"ATP", "WTA"}


def test_ranking_rows_carry_the_week_and_defaults(rankings_payload):
    competitors, rankings = transform.parse_doubles_rankings(rankings_payload)
    assert set(zip(rankings["year"], rankings["week"])) == {(2026, 42)}
    assert competitors.set_index("competitor_id").loc["p3", "abbreviation"] == "N/A"
    assert rankings["points"].min() >= 0


def test_empty_payloads_give_empty_tables():
    categories, comps = transform.parse_competitions({})
    assert categories.empty and comps.empty
    competitors, rankings = transform.parse_doubles_rankings({"rankings": []})
    assert competitors.empty and rankings.empty
