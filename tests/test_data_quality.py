"""The data-quality audit must count placeholders, flag bad data and validate weekly movement correctly."""
import pandas as pd
from sqlalchemy import text

from db import data_quality as dq


def test_status_for_zero_and_info_checks():
    assert dq.status_for(0, "zero") == "PASS"
    assert dq.status_for(3, "zero") == "WARN"
    assert dq.status_for(99, "info") == "INFO"


def test_iqr_summary_finds_an_outlier():
    s = dq.iqr_summary(pd.Series([10, 11, 12, 13, 14, 100]))
    assert s["n"] == 6 and s["max"] == 100
    assert s["above_fence"] == 1
    assert dq.iqr_summary(pd.Series([], dtype=float))["n"] == 0


def test_markdown_table_escapes_pipes_and_handles_empty_frames():
    table = dq.md_table(pd.DataFrame({"a": ["x|y"], "b": [1]}))
    assert table.splitlines()[0] == "| a | b |"
    assert "x\\|y" in table
    assert dq.md_table(pd.DataFrame()) == "_No rows._"


def test_placeholder_table_counts_missing_values(sqlite_engine):
    table = dq.placeholder_table(sqlite_engine).set_index(["Table", "Column"])
    assert table.loc[("Venues", "city_name"), "Rows affected"] == 1
    assert table.loc[("Venues", "timezone"), "Rows affected"] == 1
    assert table.loc[("Competitors", "abbreviation"), "Rows affected"] == 1
    assert table.loc[("Competitions", "level"), "Rows affected"] == 2
    assert table.loc[("Venues", "city_name"), "% of table"] == 50.0
    assert (table["Treatment"].str.len() > 0).all() and (table["Why this is justified"].str.len() > 0).all()


def test_integrity_checks_pass_on_clean_keys_and_report_orphan_parents(sqlite_engine):
    checks = dq.integrity_checks(sqlite_engine).set_index("Check")
    assert checks.loc["Orphan competitor links (Rankings → Competitors)", "Status"] == "PASS"
    assert checks.loc["Duplicate ranking snapshots", "Result"] == 0
    assert checks.loc["Parent ids that point to a missing competition", "Result"] == 1
    assert checks.loc["Tied rank groups (doubles partners share a rank)", "Result"] == 1


def test_domain_checks_flag_an_impossible_rank(sqlite_engine):
    assert set(dq.domain_checks(sqlite_engine)["Status"]) == {"PASS"}
    with sqlite_engine.begin() as conn:
        conn.execute(text("UPDATE Competitor_Rankings SET `rank` = 0 WHERE competitor_id = 'p3'"))
    result = dq.domain_checks(sqlite_engine).set_index("Check")
    assert result.loc["Rank is at least 1", "Status"] == "WARN"


def test_movement_validation_is_skipped_with_one_week(sqlite_engine):
    assert dq.movement_validation(sqlite_engine) is None


def test_movement_validation_matches_real_rank_changes(two_week_engine):
    result = dq.movement_validation(two_week_engine)
    assert result["compared"] == 3
    assert result["current"] == (2026, 43) and result["previous"] == (2026, 42)
    assert result["match_up_pct"] == 100.0
    assert result["convention"] == "positive movement = moved up"


def test_full_report_builds_and_lists_every_section(two_week_engine):
    report, placeholders, summary = dq.build_report(two_week_engine)
    for heading in ("## 1. Table sizes", "## 2. Missing values", "## 3. Integrity", "## 4. Domain checks",
                    "## 5. Outliers", "## 6. Week-over-week"):
        assert heading in report
    assert summary["warn"] == 0
    assert len(placeholders) == len(dq.PLACEHOLDER_RULES)
