"""sql/queries.sql must contain the 20 required queries in a form the app can run."""
from pathlib import Path

from dashboard.queries_loader import load_queries

QUERY_FILE = Path(__file__).resolve().parent.parent / "sql" / "queries.sql"
EXPECTED_IDS = ([f"1.{i}" for i in range(1, 8)] + [f"2.{i}" for i in range(1, 8)] + [f"3.{i}" for i in range(1, 7)])


def test_all_twenty_queries_are_found_in_order():
    queries = load_queries(QUERY_FILE)
    assert [q[0] for q in queries] == EXPECTED_IDS
    assert len(queries) == 20


def test_every_query_is_a_single_read_only_statement():
    for qid, title, sql in load_queries(QUERY_FILE):
        assert title, qid
        assert sql.lstrip().upper().startswith("SELECT"), qid
        assert ";" not in sql, qid
        assert not sql.upper().startswith("USE "), qid
