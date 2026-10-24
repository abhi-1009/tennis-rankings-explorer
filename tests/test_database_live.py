"""Sanity checks on the REAL database (local MySQL or Aiven).

They run automatically when the database in your .env can be reached, and are skipped otherwise.
Run only these:   pytest -m db        Skip them:   pytest -m "not db"
"""
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from api import config
from db import data_quality as dq
from dashboard.queries_loader import load_queries

pytestmark = pytest.mark.db
QUERY_FILE = Path(__file__).resolve().parent.parent / "sql" / "queries.sql"
EXPECTED_INDEXES = {"idx_competitions_category", "idx_competitions_parent", "idx_competitions_type", "idx_competitions_level",
                    "idx_venues_complex", "idx_venues_country", "idx_competitors_country", "idx_competitors_name",
                    "uq_ranking_snapshot", "idx_rankings_rank", "idx_rankings_points", "idx_rankings_period"}


@pytest.fixture(scope="module")
def engine():
    try:
        eng = create_engine(config.DB_URL, connect_args={**config.DB_CONNECT_ARGS, "connect_timeout": 8})
        with eng.connect() as conn:
            conn.execute(text("SELECT COUNT(*) FROM Competitor_Rankings")).scalar()
    except SQLAlchemyError as exc:
        pytest.skip(f"database not reachable or not loaded: {type(exc).__name__}")
    return eng


def test_every_table_has_rows(engine):
    sizes = dq.table_sizes(engine).set_index("Table")["Rows"]
    assert (sizes > 0).all(), sizes.to_dict()


def test_no_integrity_problems(engine):
    checks = dq.integrity_checks(engine)
    assert "WARN" not in set(checks["Status"]), checks[checks["Status"] == "WARN"].to_dict("records")


def test_no_impossible_values(engine):
    checks = dq.domain_checks(engine)
    assert "WARN" not in set(checks["Status"]), checks[checks["Status"] == "WARN"].to_dict("records")


def test_latest_ranking_week_has_rows_in_every_list(engine):
    period = dq.latest_period(engine)
    assert period is not None
    with engine.connect() as conn:
        counts = conn.execute(text("SELECT ranking_name, COUNT(*) FROM Competitor_Rankings WHERE year = :y AND week = :w "
                                   "GROUP BY ranking_name"), {"y": period[0], "w": period[1]}).fetchall()
    assert counts and all(n > 0 for _, n in counts)


def test_expected_indexes_exist(engine):
    with engine.connect() as conn:
        found = {row[0] for row in conn.execute(text(
            "SELECT DISTINCT index_name FROM information_schema.statistics WHERE table_schema = DATABASE()"))}
    assert EXPECTED_INDEXES <= found, sorted(EXPECTED_INDEXES - found)


def test_movement_matches_real_rank_change_when_two_weeks_exist(engine):
    result = dq.movement_validation(engine)
    if result is None:
        pytest.skip("only one ranking week is stored yet")
    assert max(result["match_up_pct"], result["match_down_pct"]) >= 90


@pytest.mark.parametrize("qid,title,sql", load_queries(QUERY_FILE), ids=[q[0] for q in load_queries(QUERY_FILE)])
def test_each_project_query_runs(engine, qid, title, sql):
    with engine.connect() as conn:
        rows = conn.execute(text(sql.replace(":", "\\:"))).fetchall()
    assert rows is not None
