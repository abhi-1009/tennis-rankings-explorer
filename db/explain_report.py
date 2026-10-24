"""Query-efficiency evidence: EXPLAIN plans and timings, with and without each index.

Run from the project root:   python -m db.explain_report

For every case it runs the same query twice, once normally and once with the index switched off
(IGNORE INDEX), then writes docs/reports/explain_report.md with the access type, the index used,
the estimated rows and the median run time. Needs MySQL or MariaDB (Aiven).

How to read the plan:  type = ALL means a full table scan;  ref / range / const / eq_ref mean an index lookup.
"""
import argparse
import logging
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from api import config
from db.data_quality import md_table

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPORT_DIR = config.PROJECT_ROOT / "docs" / "reports"
RUNS = 7  # timed runs per variant; the first one is discarded as a warm-up

# {ignore} is replaced by "IGNORE INDEX (name)" in the "without index" variant.
CASES = [
    {"id": "A", "title": "Venues in a country", "index": "idx_venues_country",
     "sql": "SELECT venue_name, city_name FROM Venues {ignore} WHERE country_name = 'Chile'"},
    {"id": "B", "title": "Players of one country", "index": "idx_competitors_country",
     "sql": "SELECT name, abbreviation FROM Competitors {ignore} WHERE country = 'Croatia'"},
    {"id": "C", "title": "Top 5 ranks", "index": "idx_rankings_rank",
     "sql": "SELECT competitor_id, points FROM Competitor_Rankings {ignore} WHERE `rank` <= 5"},
    {"id": "D", "title": "Doubles competitions", "index": "idx_competitions_type",
     "sql": "SELECT competition_name FROM Competitions {ignore} WHERE type = 'doubles'"},
    {"id": "E", "title": "Sub-competitions of the busiest parent", "index": "idx_competitions_parent",
     "sql": "SELECT competition_name FROM Competitions {ignore} WHERE parent_id = '{busiest_parent}'"},
]
# Queries on columns that have no index at all, to show what a full scan looks like.
NO_INDEX_CASES = [
    {"id": "F", "title": "Venues by city (no index on city_name)",
     "sql": "SELECT venue_name FROM Venues WHERE city_name = 'Santiago'"},
    {"id": "G", "title": "Players by competitions played (no index)",
     "sql": "SELECT competitor_id FROM Competitor_Rankings WHERE competitions_played = 20"},
]
JOIN_CASES = [
    {"id": "H", "title": "Query 1.1: competitions with category name (JOIN on the foreign key)",
     "sql": "SELECT c.competition_id, c.competition_name, cat.category_name FROM Competitions c "
            "LEFT JOIN Categories cat ON cat.category_id = c.category_id"},
    {"id": "I", "title": "Query 2.5: complexes with more than one venue (JOIN + GROUP BY)",
     "sql": "SELECT cx.complex_name, COUNT(v.venue_id) FROM Complexes cx JOIN Venues v ON v.complex_id = cx.complex_id "
            "GROUP BY cx.complex_id, cx.complex_name HAVING COUNT(v.venue_id) > 1"},
]


def render_sql(template: str, index: str | None, busiest_parent: str = "") -> str:
    """Fill in the IGNORE INDEX clause (or remove it) and the parent id placeholder."""
    ignore = f"IGNORE INDEX ({index})" if index else ""
    return " ".join(template.replace("{ignore}", ignore).replace("{busiest_parent}", busiest_parent).split())


def pick_plan_row(rows: list[dict]) -> dict:
    """Choose the main plan row: the first one that reads a real table."""
    for row in rows:
        if row.get("table") and row.get("type"):
            return row
    return rows[0] if rows else {}


def explain(conn, sql: str) -> dict:
    """EXPLAIN a query. `steps` lists every table the plan touches (useful for JOINs)."""
    result = conn.execute(text("EXPLAIN " + sql.replace(":", "\\:")))
    rows = [{k.lower(): v for k, v in dict(r._mapping).items()} for r in result]
    row = pick_plan_row(rows)
    steps = [(str(r.get("table")), str(r.get("type")), str(r.get("key") or "none")) for r in rows if r.get("table")]
    return {"type": str(row.get("type", "")), "key": str(row.get("key") or "none"),
            "rows": int(row.get("rows") or 0), "extra": str(row.get("extra") or ""), "steps": steps}


def median_ms(conn, sql: str, runs: int = RUNS) -> float:
    safe = text(sql.replace(":", "\\:"))
    times = []
    for _ in range(runs):
        started = time.perf_counter()
        conn.execute(safe).fetchall()
        times.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(times[1:]), 2)


def summarise(label: str, with_idx: dict, without_idx: dict, ms_with: float, ms_without: float) -> str:
    """One honest sentence about what the index did for this query."""
    if with_idx["key"] == "none":
        return (f"{label}: the optimizer chose a full scan even with the index available "
                f"(low selectivity or a small table), so the index did not change the plan.")
    ratio = without_idx["rows"] / max(with_idx["rows"], 1)
    return (f"{label}: with the index the plan reads about {with_idx['rows']:,} rows ({with_idx['type']}) instead of "
            f"{without_idx['rows']:,} ({without_idx['type']}), roughly {ratio:.1f}x fewer. "
            f"Median time {ms_with} ms vs {ms_without} ms.")


def build_report(engine) -> str:
    rows, findings = [], []
    with engine.connect() as conn:
        parent = conn.execute(text("SELECT parent_id FROM Competitions WHERE parent_id IS NOT NULL "
                                   "GROUP BY parent_id ORDER BY COUNT(*) DESC LIMIT 1")).scalar() or ""
        version = conn.execute(text("SELECT VERSION()")).scalar()
        for case in CASES:
            idx = case["index"]
            sql_with, sql_without = render_sql(case["sql"], None, parent), render_sql(case["sql"], idx, parent)
            plan_with, plan_without = explain(conn, sql_with), explain(conn, sql_without)
            ms_with, ms_without = median_ms(conn, sql_with), median_ms(conn, sql_without)
            for variant, plan, ms in (("with index", plan_with, ms_with), ("index ignored", plan_without, ms_without)):
                rows.append({"Case": case["id"], "Query": case["title"], "Variant": variant, "Access type": plan["type"],
                             "Index used": plan["key"], "Est. rows": plan["rows"], "Median ms": ms})
            findings.append(summarise(f"Case {case['id']} ({case['title']})", plan_with, plan_without, ms_with, ms_without))
        for case in NO_INDEX_CASES + JOIN_CASES:
            sql = render_sql(case["sql"], None)
            plan, ms = explain(conn, sql), median_ms(conn, sql)
            is_join = len(plan["steps"]) > 1
            access = "; ".join(f"{t}: {ty}" for t, ty, _ in plan["steps"]) if is_join else plan["type"]
            keys = "; ".join(f"{t}: {k}" for t, _, k in plan["steps"]) if is_join else plan["key"]
            rows.append({"Case": case["id"], "Query": case["title"], "Variant": "as written", "Access type": access,
                         "Index used": keys, "Est. rows": plan["rows"], "Median ms": ms})
    table = pd.DataFrame(rows)
    parts = [
        "# Query efficiency report (EXPLAIN and timings)",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · server `{version}` · database `{config.DB_URL.database}`",
        "Each indexed case is run twice: normally, and with `IGNORE INDEX` to simulate a table without that index. "
        f"Times are the median of {RUNS - 1} runs and include network latency to the database, so compare the "
        "variants with each other rather than reading the absolute numbers.",
        "## Results", md_table(table),
        "## What the numbers say", "\n".join(f"- {f}" for f in findings),
        "## How to read this",
        "- **type = ALL** is a full table scan. **ref, range, const and eq_ref** are index lookups.\n"
        "- **Est. rows** is how many rows MySQL expects to read. Fewer is better.\n"
        "- On small tables the optimizer may choose a scan even when an index exists. That is correct behaviour, and the "
        "index pays off as the data grows (a larger refresh history, more players, more competitions).\n"
        "- Cases F and G have no index on the filtered column and show the full-scan baseline.\n"
        "- Cases H and I are JOINs: the first table is read in full because the query returns every row, and the joined "
        "table is reached through an index lookup (eq_ref / ref) on the key, not by scanning it again.",
    ]
    return "\n\n".join(parts) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write an EXPLAIN and timing report for the main indexes.")
    parser.add_argument("--out", default=str(REPORT_DIR), help="folder for the report")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        engine = create_engine(config.DB_URL, connect_args=config.DB_CONNECT_ARGS)
        report = build_report(engine)
    except SQLAlchemyError as exc:
        logger.error("Database error (this report needs MySQL or MariaDB): %s", exc)
        return 1
    (out / "explain_report.md").write_text(report, encoding="utf-8")
    logger.info("Wrote %s", out / "explain_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
