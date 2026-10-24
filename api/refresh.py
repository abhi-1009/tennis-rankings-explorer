"""One-command weekly refresh: extract -> check the raw data -> load -> check the database -> log.

Run from the project root:
    python -m api.refresh                 # full refresh (calls the Sportradar API)
    python -m api.refresh --skip-extract  # reuse the JSON already in data/raw/

Every run appends one line to docs/reports/refresh_log.csv, which is your monitoring evidence.
Exit code 0 = healthy, 1 = failed, 2 = loaded but with warnings.
"""
import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from api import config, extract, load
from db import data_quality

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LOG_FILE = config.PROJECT_ROOT / "docs" / "reports" / "refresh_log.csv"
LOG_COLUMNS = ["run_at_utc", "status", "ranking_year", "ranking_week", "week_status", "competitions", "venues",
               "competitors", "ranking_rows", "integrity_warnings", "notes"]
DROP_TOLERANCE = 0.20   # warn if a table loses more than 20% of its rows between runs


def summarise_raw(raw: dict) -> dict:
    """Counts and the ranking week found in the three raw API payloads. Raises ValueError if a payload is empty."""
    competitions = len(raw["competitions"].get("competitions", []))
    complexes = raw["complexes"].get("complexes", [])
    venues = sum(len(c.get("venues", [])) for c in complexes)
    lists = raw["doubles_rankings"].get("rankings", [])
    entries = sum(len(r.get("competitor_rankings", [])) for r in lists)
    if not competitions or not complexes or not entries:
        raise ValueError(f"Empty payload: competitions={competitions}, complexes={len(complexes)}, ranking rows={entries}")
    year = max((r.get("year", 0) for r in lists), default=0)
    week = max((r.get("week", 0) for r in lists if r.get("year", 0) == year), default=0)
    return {"competitions": competitions, "complexes": len(complexes), "venues": venues,
            "ranking_rows": entries, "year": year, "week": week}


def classify_week(raw_period: tuple, db_period) -> str:
    """Is the downloaded ranking week new, a repeat, or older than what the database already holds?"""
    if db_period is None:
        return "first load"
    if raw_period == db_period:
        return "same week (rows updated in place)"
    return "new week" if raw_period > db_period else "OLDER than database (check the API)"


def evaluate_counts(current: dict, previous: dict | None, tolerance: float = DROP_TOLERANCE) -> list:
    """Warnings when a table shrank by more than `tolerance` compared with the previous logged run."""
    if not previous:
        return []
    warnings = []
    for key in ("competitions", "venues", "competitors"):
        before, now = int(previous.get(key) or 0), int(current.get(key) or 0)
        if before and now < before * (1 - tolerance):
            warnings.append(f"{key} dropped from {before:,} to {now:,}")
    return warnings


def read_last_log(path: Path = LOG_FILE) -> dict | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("status") != "FAILED"]
    return rows[-1] if rows else None


def append_log(row: dict, path: Path = LOG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in LOG_COLUMNS})


def load_raw_payloads() -> dict:
    return {name: json.loads((config.RAW_DIR / f"{name}.json").read_text(encoding="utf-8")) for name in config.ENDPOINTS}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Weekly refresh of the tennis database.")
    parser.add_argument("--skip-extract", action="store_true", help="reuse the JSON already in data/raw/")
    args = parser.parse_args(argv)
    row = {"run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "status": "FAILED", "notes": ""}

    # 1) extract
    if not args.skip_extract:
        results = extract.run()
        failed = [name for name, ok in results.items() if not ok]
        if failed:
            row["notes"] = "extract failed: " + ", ".join(failed)
            append_log(row)
            logger.error("Refresh stopped: %s. The database was not changed.", row["notes"])
            return 1

    # 2) check the raw data before touching the database
    try:
        summary = summarise_raw(load_raw_payloads())
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        row["notes"] = f"raw data problem: {exc}"
        append_log(row)
        logger.error("Refresh stopped: %s. The database was not changed.", row["notes"])
        return 1
    logger.info("Raw data: %s competitions, %s venues, %s ranking rows, ranking week %s/%s",
                f"{summary['competitions']:,}", f"{summary['venues']:,}", f"{summary['ranking_rows']:,}",
                summary["year"], summary["week"])

    # 3) load and verify
    try:
        engine = create_engine(config.DB_URL, connect_args=config.DB_CONNECT_ARGS)
        row["week_status"] = classify_week((summary["year"], summary["week"]), data_quality.latest_period(engine))
        logger.info("Ranking week status: %s", row["week_status"])
        if not load.main():
            row["notes"] = "load failed"
            append_log(row)
            return 1
        sizes = data_quality.table_sizes(engine).set_index("Table")["Rows"]
        integrity = data_quality.integrity_checks(engine)
        domain = data_quality.domain_checks(engine)
        movement = data_quality.movement_validation(engine)
    except SQLAlchemyError as exc:
        row["notes"] = f"database error: {exc}"
        append_log(row)
        logger.error("Refresh failed: %s", row["notes"])
        return 1

    counts = {"competitions": int(sizes["Competitions"]), "venues": int(sizes["Venues"]),
              "competitors": int(sizes["Competitors"]), "ranking_rows": int(sizes["Competitor_Rankings"])}
    warnings = evaluate_counts(counts, read_last_log())
    bad = list(integrity.loc[integrity["Status"] == "WARN", "Check"]) + list(domain.loc[domain["Status"] == "WARN", "Check"])
    warnings += [f"check failed: {name}" for name in bad]
    if "OLDER" in row["week_status"]:
        warnings.append("downloaded ranking week is older than the database")
    if movement:
        pct = max(movement["match_up_pct"], movement["match_down_pct"])
        logger.info("Movement check %s vs %s: %.1f%% of %s players match (%s)", movement["current"], movement["previous"],
                    pct, f"{movement['compared']:,}", movement["convention"])
        if pct < 90:
            warnings.append(f"movement matches the real rank change for only {pct:.0f}% of players")

    row.update({"status": "OK" if not warnings else "WARNINGS", "ranking_year": summary["year"],
                "ranking_week": summary["week"], **counts, "integrity_warnings": len(bad), "notes": "; ".join(warnings)})
    append_log(row)
    for w in warnings:
        logger.warning(w)
    logger.info("Refresh finished with status %s. Logged to %s", row["status"], LOG_FILE)
    return 0 if row["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
