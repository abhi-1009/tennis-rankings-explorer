"""Step 2: flatten nested JSON into DataFrames matching the SQL tables.

!! Key names below are based on the usual SportRadar v3 response shape.
!! Open data/raw/*.json after extraction and adjust any key that differs.
"""
import json

import pandas as pd

from api import config


def load_raw(name: str) -> dict:
    return json.loads((config.RAW_DIR / f"{name}.json").read_text(encoding="utf-8"))


def parse_competitions(raw: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (categories_df, competitions_df)."""
    categories, competitions = {}, []
    for item in raw.get("competitions", []):
        category = item.get("category") or {}
        if category.get("id"):
            categories[category["id"]] = category.get("name", "Unknown")
        competitions.append({
            "competition_id": item["id"],
            "competition_name": item.get("name", "Unknown"),
            "parent_id": item.get("parent_id"),            # may legitimately be None
            "type": item.get("type") or "unknown",
            "gender": item.get("gender") or "unknown",
            "level": item.get("level"),                    # optional, many competitions have none
            "category_id": category.get("id"),
        })
    categories_df = pd.DataFrame(
        [{"category_id": k, "category_name": v} for k, v in categories.items()]
    )
    return categories_df, pd.DataFrame(competitions)


def parse_complexes(raw: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (complexes_df, venues_df)."""
    complexes, venues = [], []
    for item in raw.get("complexes", []):
        complexes.append({"complex_id": item["id"], "complex_name": item.get("name", "Unknown")})
        for venue in item.get("venues", []):
            venues.append({
                "venue_id": venue["id"],
                "venue_name": venue.get("name", "Unknown"),
                "city_name": venue.get("city_name") or "Unknown",
                "country_name": venue.get("country_name") or "Unknown",
                "country_code": (venue.get("country_code") or "UNK")[:3],
                "timezone": venue.get("timezone") or "Unknown",
                "complex_id": item["id"],
            })
    return pd.DataFrame(complexes), pd.DataFrame(venues)


def parse_doubles_rankings(raw: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (competitors_df, rankings_df)."""
    competitors, rankings = {}, []
    for ranking_list in raw.get("rankings", []):
        for entry in ranking_list.get("competitor_rankings", []):
            comp = entry.get("competitor") or {}
            if not comp.get("id"):
                continue
            competitors[comp["id"]] = {
                "competitor_id": comp["id"],
                "name": comp.get("name", "Unknown"),
                "country": comp.get("country") or "Unknown",
                "country_code": (comp.get("country_code") or "UNK")[:3],
                "abbreviation": comp.get("abbreviation") or "N/A",
            }
            rankings.append({
                "rank": entry.get("rank", 0),
                "movement": entry.get("movement", 0),
                "points": entry.get("points", 0),
                "competitions_played": entry.get("competitions_played", 0),
                "competitor_id": comp["id"],
                "ranking_name": ranking_list.get("name", "unknown"),
                "year": ranking_list.get("year", 0),
                "week": ranking_list.get("week", 0),
                "gender": ranking_list.get("gender", "unknown"),
            })
    return pd.DataFrame(list(competitors.values())), pd.DataFrame(rankings)
