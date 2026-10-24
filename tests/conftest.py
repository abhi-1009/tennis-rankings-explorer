"""Shared fixtures: import paths, sample API payloads and a small in-memory SQLite database."""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))            # `api` and `db` packages
sys.path.insert(0, str(ROOT / "app"))    # `dashboard` package


@pytest.fixture
def competitions_payload():
    return {"competitions": [
        {"id": "sr:competition:1", "name": "Vienna Open", "type": "singles", "gender": "men", "level": "atp_500",
         "category": {"id": "sr:category:3", "name": "ATP"}},
        {"id": "sr:competition:2", "name": "Vienna Open Doubles", "type": "doubles", "gender": "men",
         "parent_id": "sr:competition:1", "category": {"id": "sr:category:72", "name": "Challenger"}},
        {"id": "sr:competition:3", "name": "Mystery Cup", "type": "mixed"},          # no gender, no category
    ]}


@pytest.fixture
def complexes_payload():
    return {"complexes": [
        {"id": "sr:complex:1", "name": "Nacional", "venues": [
            {"id": "sr:venue:1", "name": "Cancha Central", "city_name": "Santiago", "country_name": "Chile",
             "country_code": "CHL", "timezone": "America/Santiago"},
            {"id": "sr:venue:2", "name": "Court 2", "city_name": "Santiago", "country_name": "Chile",
             "country_code": "CHILE"}]},                                              # code too long, no timezone
        {"id": "sr:complex:2", "name": "Empty complex", "venues": []},
        {"id": "sr:complex:3", "name": "Seville", "venues": [{"id": "sr:venue:3", "name": "Centre Court"}]},
    ]}


@pytest.fixture
def rankings_payload():
    def entry(pid, rank, points, **extra):
        comp = {"id": pid, "name": f"Player {pid}", "country": "Spain", "country_code": "ESP", "abbreviation": "PLY"}
        comp.update(extra)
        return {"rank": rank, "movement": 0, "points": points, "competitions_played": 12, "competitor": comp}
    return {"rankings": [
        {"name": "ATP", "year": 2026, "week": 42, "gender": "men",
         "competitor_rankings": [entry("p1", 1, 1000), entry("p2", 1, 1000), entry("p3", 3, 800, abbreviation=None)]},
        {"name": "WTA", "year": 2026, "week": 42, "gender": "women",
         "competitor_rankings": [entry("p1", 2, 900)]},                               # same player id in two lists
    ]}


SQLITE_SCHEMA = """
CREATE TABLE Categories (category_id TEXT PRIMARY KEY, category_name TEXT);
CREATE TABLE Competitions (competition_id TEXT PRIMARY KEY, competition_name TEXT, parent_id TEXT, type TEXT,
    gender TEXT, level TEXT, category_id TEXT);
CREATE TABLE Complexes (complex_id TEXT PRIMARY KEY, complex_name TEXT);
CREATE TABLE Venues (venue_id TEXT PRIMARY KEY, venue_name TEXT, city_name TEXT, country_name TEXT,
    country_code TEXT, timezone TEXT, complex_id TEXT);
CREATE TABLE Competitors (competitor_id TEXT PRIMARY KEY, name TEXT, country TEXT, country_code TEXT, abbreviation TEXT);
CREATE TABLE Competitor_Rankings (rank_id INTEGER PRIMARY KEY AUTOINCREMENT, `rank` INT, movement INT, points INT,
    competitions_played INT, competitor_id TEXT, ranking_name TEXT, year INT, week INT, gender TEXT);
"""


@pytest.fixture
def sqlite_engine():
    """A tiny in-memory database with the same table and column names as the real schema."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        for statement in SQLITE_SCHEMA.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        conn.execute(text("INSERT INTO Categories VALUES ('c1', 'ATP')"))
        conn.execute(text("""INSERT INTO Competitions VALUES
            ('k1', 'Open', NULL, 'singles', 'men', 'atp_250', 'c1'),
            ('k2', 'Open Doubles', 'k1', 'doubles', 'men', NULL, 'c1'),
            ('k3', 'Orphan Cup', 'missing-parent', 'doubles', 'unknown', NULL, NULL)"""))
        conn.execute(text("INSERT INTO Complexes VALUES ('x1', 'Nacional'), ('x2', 'Lonely')"))
        conn.execute(text("""INSERT INTO Venues VALUES
            ('v1', 'Court 1', 'Santiago', 'Chile', 'CHL', 'America/Santiago', 'x1'),
            ('v2', 'Court 2', 'Unknown', 'Chile', 'UNK', 'Unknown', 'x1')"""))
        conn.execute(text("""INSERT INTO Competitors VALUES
            ('p1', 'Alpha, A', 'Spain', 'ESP', 'ALP'), ('p2', 'Beta, B', 'Spain', 'ESP', 'N/A'),
            ('p3', 'Gamma, G', 'Chile', 'CHL', 'GAM')"""))
        conn.execute(text("""INSERT INTO Competitor_Rankings (`rank`, movement, points, competitions_played, competitor_id,
            ranking_name, year, week, gender) VALUES
            (1, 0, 1000, 10, 'p1', 'ATP', 2026, 42, 'men'), (1, 0, 1000, 10, 'p2', 'ATP', 2026, 42, 'men'),
            (3, 0, 800, 8, 'p3', 'ATP', 2026, 42, 'men')"""))
    return engine


@pytest.fixture
def two_week_engine(sqlite_engine):
    """Adds a second week where movement equals (previous rank - new rank), i.e. positive = moved up."""
    with sqlite_engine.begin() as conn:
        conn.execute(text("""INSERT INTO Competitor_Rankings (`rank`, movement, points, competitions_played, competitor_id,
            ranking_name, year, week, gender) VALUES
            (2, -1, 950, 11, 'p1', 'ATP', 2026, 43, 'men'), (1, 0, 1000, 11, 'p2', 'ATP', 2026, 43, 'men'),
            (2, 1, 960, 9, 'p3', 'ATP', 2026, 43, 'men')"""))
    return sqlite_engine
