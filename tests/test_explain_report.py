"""Helpers of the EXPLAIN report: query templates, plan row choice and the plain-English summary."""
from db import explain_report as er


def test_ignore_index_clause_is_added_or_removed():
    template = "SELECT x FROM Venues {ignore} WHERE country_name = 'Chile'"
    assert er.render_sql(template, None) == "SELECT x FROM Venues WHERE country_name = 'Chile'"
    assert er.render_sql(template, "idx_venues_country") == (
        "SELECT x FROM Venues IGNORE INDEX (idx_venues_country) WHERE country_name = 'Chile'")


def test_parent_id_placeholder_is_filled():
    sql = er.render_sql("SELECT 1 FROM Competitions {ignore} WHERE parent_id = '{busiest_parent}'", None, "sr:competition:7")
    assert "sr:competition:7" in sql and "{" not in sql


def test_plan_row_choice_skips_rows_without_a_table():
    rows = [{"id": 1, "table": None, "type": None}, {"id": 2, "table": "Venues", "type": "ref", "key": "idx"}]
    assert er.pick_plan_row(rows)["table"] == "Venues"
    assert er.pick_plan_row([]) == {}


def test_summary_explains_an_index_win_and_an_ignored_index():
    win = er.summarise("Case A", {"key": "idx", "type": "ref", "rows": 10}, {"key": "none", "type": "ALL", "rows": 100}, 0.2, 0.9)
    assert "10 rows" in win and "10.0x fewer" in win
    ignored = er.summarise("Case D", {"key": "none", "type": "ALL", "rows": 100}, {"key": "none", "type": "ALL", "rows": 100}, 1, 1)
    assert "full scan" in ignored
