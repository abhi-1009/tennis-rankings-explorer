"""The weekly refresh must refuse bad downloads, recognise new weeks and keep an honest log."""
import pytest

from api import refresh


def raw(competitions=2, venues=3, entries=4, year=2026, week=42):
    return {
        "competitions": {"competitions": [{"id": str(i)} for i in range(competitions)]},
        "complexes": {"complexes": [{"id": "c1", "venues": [{"id": str(i)} for i in range(venues)]}]},
        "doubles_rankings": {"rankings": [{"year": year, "week": week,
                                           "competitor_rankings": [{"rank": i} for i in range(entries)]}]},
    }


def test_summary_counts_rows_and_finds_the_ranking_week():
    s = refresh.summarise_raw(raw(competitions=5, venues=7, entries=9, week=43))
    assert (s["competitions"], s["venues"], s["ranking_rows"]) == (5, 7, 9)
    assert (s["year"], s["week"]) == (2026, 43)


@pytest.mark.parametrize("bad", [raw(competitions=0), raw(entries=0)])
def test_empty_payloads_are_rejected(bad):
    with pytest.raises(ValueError, match="Empty payload"):
        refresh.summarise_raw(bad)


def test_missing_keys_raise_key_error():
    with pytest.raises(KeyError):
        refresh.summarise_raw({"competitions": {}})


def test_week_classification():
    assert refresh.classify_week((2026, 42), None) == "first load"
    assert refresh.classify_week((2026, 42), (2026, 42)).startswith("same week")
    assert refresh.classify_week((2026, 43), (2026, 42)) == "new week"
    assert "OLDER" in refresh.classify_week((2026, 41), (2026, 42))
    assert refresh.classify_week((2027, 1), (2026, 52)) == "new week"


def test_big_drops_are_warned_about_and_small_ones_are_not():
    previous = {"competitions": "1000", "venues": "500", "competitors": "100"}
    assert refresh.evaluate_counts({"competitions": 1000, "venues": 480, "competitors": 100}, previous) == []
    warnings = refresh.evaluate_counts({"competitions": 600, "venues": 500, "competitors": 100}, previous)
    assert len(warnings) == 1 and "competitions dropped" in warnings[0]
    assert refresh.evaluate_counts({"competitions": 1}, None) == []


def test_log_is_appended_and_failed_runs_are_ignored_when_comparing(tmp_path):
    log = tmp_path / "refresh_log.csv"
    assert refresh.read_last_log(log) is None
    refresh.append_log({"run_at_utc": "t1", "status": "OK", "competitions": 10}, log)
    refresh.append_log({"run_at_utc": "t2", "status": "FAILED", "notes": "boom"}, log)
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3 and lines[0].startswith("run_at_utc,status")
    assert refresh.read_last_log(log)["run_at_utc"] == "t1"
