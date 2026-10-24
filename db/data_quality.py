"""Data-quality audit for the tennis database.

Run from the project root:   python -m db.data_quality

It writes two files you can paste straight into your report:
    docs/reports/data_quality_report.md        (all sections)
    docs/reports/data_quality_placeholders.csv (the missing-value table)

Every check is plain SQL plus a little pandas, so it works on MySQL, MariaDB (Aiven) and SQLite (tests).
"""
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from api import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPORT_DIR = config.PROJECT_ROOT / "docs" / "reports"
TABLES = ["Categories", "Competitions", "Complexes", "Venues", "Competitors", "Competitor_Rankings"]

# (table, column label, SQL condition, issue, treatment in the pipeline, why that treatment is justified)
PLACEHOLDER_RULES = [
    ("Venues", "city_name", "city_name = 'Unknown'", "City missing in API",
     "Stored as 'Unknown'", "Column is NOT NULL; the venue is still useful for its country and timezone."),
    ("Venues", "country_name", "country_name = 'Unknown'", "Country missing in API",
     "Stored as 'Unknown'", "Keeps the venue row instead of silently dropping it."),
    ("Venues", "country_code", "country_code = 'UNK'", "Country code missing in API",
     "Stored as 'UNK'", "CHAR(3) NOT NULL; 'UNK' is easy to filter out and cannot be mistaken for a real code."),
    ("Venues", "timezone", "timezone = 'Unknown'", "Timezone missing in API",
     "Stored as 'Unknown'", "Guessing a timezone from the country would invent data."),
    ("Competitions", "level", "level IS NULL", "No level label in API",
     "Left NULL", "Level is optional; most events have none, so a default would distort the level chart."),
    ("Competitions", "gender", "gender = 'unknown'", "Gender missing in API",
     "Stored as 'unknown'", "NOT NULL column; keeps the event visible in type and category analysis."),
    ("Competitions", "type", "type = 'unknown'", "Type missing in API",
     "Stored as 'unknown'", "NOT NULL column; flagged value is easy to exclude."),
    ("Competitions", "category_id", "category_id IS NULL", "No category in API",
     "Left NULL", "The foreign key allows NULL, and a fake category would corrupt the category counts."),
    ("Competitions", "parent_id", "parent_id IS NULL", "Top-level event (not an error)",
     "Left NULL", "Top-level competitions have no parent by design (query 1.7 depends on this)."),
    ("Competitors", "country", "country = 'Unknown'", "Country missing in API",
     "Stored as 'Unknown'", "Keeps the player in rankings; excluded from country analysis by name."),
    ("Competitors", "country_code", "country_code = 'UNK'", "Country code missing in API",
     "Stored as 'UNK'", "Needed as CHAR(3) NOT NULL; the map page ignores unknown codes."),
    ("Competitors", "abbreviation", "abbreviation = 'N/A'", "Abbreviation missing in API",
     "Stored as 'N/A'", "Abbreviation is cosmetic and not used in any analysis."),
    ("Competitor_Rankings", "points", "points = 0", "Zero points",
     "Kept as 0", "A real value for players with no points, not a missing one."),
    ("Competitor_Rankings", "competitions_played", "competitions_played = 0", "Zero competitions played",
     "Kept as 0", "A real value; also the default if the field is absent."),
    ("Competitor_Rankings", "rank", "`rank` = 0", "Rank 0 (not possible for a real rank)",
     "Kept as 0 so it is detectable", "Ranks start at 1, so any 0 would indicate a parsing problem."),
]

# (label, SQL returning one number, expected, explanation)  expected: "zero" = must be 0, "info" = just report
INTEGRITY_CHECKS = [
    ("Orphan category links (Competitions → Categories)",
     "SELECT COUNT(*) FROM Competitions c LEFT JOIN Categories k ON k.category_id = c.category_id "
     "WHERE c.category_id IS NOT NULL AND k.category_id IS NULL", "zero", "Enforced by a foreign key."),
    ("Orphan complex links (Venues → Complexes)",
     "SELECT COUNT(*) FROM Venues v LEFT JOIN Complexes x ON x.complex_id = v.complex_id "
     "WHERE v.complex_id IS NOT NULL AND x.complex_id IS NULL", "zero", "Enforced by a foreign key."),
    ("Orphan competitor links (Rankings → Competitors)",
     "SELECT COUNT(*) FROM Competitor_Rankings r LEFT JOIN Competitors c ON c.competitor_id = r.competitor_id "
     "WHERE r.competitor_id IS NOT NULL AND c.competitor_id IS NULL", "zero", "Enforced by a foreign key."),
    ("Duplicate ranking snapshots",
     "SELECT COUNT(*) FROM (SELECT competitor_id, ranking_name, year, week FROM Competitor_Rankings "
     "GROUP BY competitor_id, ranking_name, year, week HAVING COUNT(*) > 1) t", "zero",
     "The unique key uq_ranking_snapshot prevents this."),
    ("Parent ids that point to a missing competition",
     "SELECT COUNT(*) FROM Competitions c LEFT JOIN Competitions p ON p.competition_id = c.parent_id "
     "WHERE c.parent_id IS NOT NULL AND p.competition_id IS NULL", "info",
     "Not enforced on purpose: the API can reference a parent it does not return."),
    ("Complexes without any venue",
     "SELECT COUNT(*) FROM Complexes x LEFT JOIN Venues v ON v.complex_id = x.complex_id WHERE v.venue_id IS NULL",
     "info", "Possible when the API lists a complex with an empty venue list."),
    ("Players sharing a name (different ids)",
     "SELECT COUNT(*) FROM (SELECT name FROM Competitors GROUP BY name HAVING COUNT(*) > 1) t", "info",
     "Can be two real players with the same name; ids are the identity."),
    ("Venues sharing name, city and country",
     "SELECT COUNT(*) FROM (SELECT venue_name, city_name, country_name FROM Venues "
     "GROUP BY venue_name, city_name, country_name HAVING COUNT(*) > 1) t", "info",
     "Generic names such as 'Court 1' repeat across complexes; ids are the identity."),
    ("Tied rank groups (doubles partners share a rank)",
     "SELECT COUNT(*) FROM (SELECT ranking_name, year, week, `rank` FROM Competitor_Rankings "
     "GROUP BY ranking_name, year, week, `rank` HAVING COUNT(*) > 1) t", "info",
     "Expected: both partners of a doubles team carry the same rank."),
]

DOMAIN_CHECKS = [
    ("Rank is at least 1", "SELECT COUNT(*) FROM Competitor_Rankings WHERE `rank` < 1"),
    ("Points are not negative", "SELECT COUNT(*) FROM Competitor_Rankings WHERE points < 0"),
    ("Competitions played is not negative", "SELECT COUNT(*) FROM Competitor_Rankings WHERE competitions_played < 0"),
    ("Week number is between 1 and 53", "SELECT COUNT(*) FROM Competitor_Rankings WHERE week < 1 OR week > 53"),
    ("Competitor country codes have 3 letters", "SELECT COUNT(*) FROM Competitors WHERE LENGTH(country_code) <> 3"),
    ("Venue country codes have 3 letters", "SELECT COUNT(*) FROM Venues WHERE LENGTH(country_code) <> 3"),
]


# ------------------------------------------------------------------ helpers
def md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavoured Markdown table (no extra packages needed)."""
    if df.empty:
        return "_No rows._"
    clean = df.astype(object).where(df.notna(), "")
    head = "| " + " | ".join(str(c) for c in clean.columns) + " |"
    sep = "|" + "|".join("---" for _ in clean.columns) + "|"
    rows = ["| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in row) + " |"
            for row in clean.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def scalar(engine, sql: str, params: dict | None = None) -> int:
    with engine.connect() as conn:
        value = conn.execute(text(sql), params or {}).scalar()
    return int(value or 0)


def status_for(value: int, expected: str) -> str:
    """PASS / WARN for must-be-zero checks, INFO for descriptive ones."""
    if expected == "info":
        return "INFO"
    return "PASS" if value == 0 else "WARN"


def iqr_summary(values: pd.Series) -> dict:
    """Quartiles and the upper outlier fence (Q3 + 1.5 * IQR) for a numeric series."""
    v = pd.to_numeric(values, errors="coerce").dropna()
    if v.empty:
        return {"n": 0, "min": 0, "q1": 0, "median": 0, "q3": 0, "max": 0, "upper_fence": 0, "above_fence": 0}
    q1, q3 = v.quantile(0.25), v.quantile(0.75)
    fence = q3 + 1.5 * (q3 - q1)
    return {"n": int(len(v)), "min": float(v.min()), "q1": float(q1), "median": float(v.median()),
            "q3": float(q3), "max": float(v.max()), "upper_fence": float(fence), "above_fence": int((v > fence).sum())}


# ------------------------------------------------------------------- checks
def table_sizes(engine) -> pd.DataFrame:
    return pd.DataFrame([{"Table": t, "Rows": scalar(engine, f"SELECT COUNT(*) FROM {t}")} for t in TABLES])


def placeholder_table(engine) -> pd.DataFrame:
    """Missing or placeholder values per column, with the treatment and its justification."""
    totals = {t: scalar(engine, f"SELECT COUNT(*) FROM {t}") for t in {r[0] for r in PLACEHOLDER_RULES}}
    rows = []
    for table, column, condition, issue, treatment, why in PLACEHOLDER_RULES:
        n = scalar(engine, f"SELECT COUNT(*) FROM {table} WHERE {condition}")
        total = totals[table]
        rows.append({"Table": table, "Column": column.strip("`"), "Issue": issue, "Rows affected": n,
                     "% of table": round(100 * n / total, 2) if total else 0.0,
                     "Treatment": treatment, "Why this is justified": why})
    return pd.DataFrame(rows)


def integrity_checks(engine) -> pd.DataFrame:
    rows = []
    for label, sql, expected, note in INTEGRITY_CHECKS:
        value = scalar(engine, sql)
        rows.append({"Check": label, "Result": value, "Status": status_for(value, expected), "Note": note})
    return pd.DataFrame(rows)


def domain_checks(engine) -> pd.DataFrame:
    rows = []
    for label, sql in DOMAIN_CHECKS:
        value = scalar(engine, sql)
        rows.append({"Check": label, "Violations": value, "Status": status_for(value, "zero")})
    return pd.DataFrame(rows)


def latest_period(engine):
    with engine.connect() as conn:
        row = conn.execute(text("SELECT year, week FROM Competitor_Rankings ORDER BY year DESC, week DESC LIMIT 1")).first()
    return (int(row[0]), int(row[1])) if row else None


def outlier_table(engine) -> pd.DataFrame:
    """Points and competitions-played spread per ranking list for the latest week (IQR rule)."""
    period = latest_period(engine)
    if not period:
        return pd.DataFrame()
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT ranking_name, points, competitions_played FROM Competitor_Rankings "
                              "WHERE year = :y AND week = :w"), conn, params={"y": period[0], "w": period[1]})
    rows = []
    for name, group in df.groupby("ranking_name"):
        for column in ("points", "competitions_played"):
            s = iqr_summary(group[column])
            rows.append({"Ranking list": name, "Column": column, "Players": s["n"], "Min": s["min"], "Median": s["median"],
                         "Max": s["max"], "Upper fence": round(s["upper_fence"], 1), "Above fence": s["above_fence"],
                         "Decision": ("No values above the fence" if s["above_fence"] == 0 else
                                      "Kept: genuine elite values, removing them would delete the top players")})
    return pd.DataFrame(rows)


def movement_validation(engine) -> dict | None:
    """Compare the stored `movement` with the real change in rank between the two newest weeks.

    Returns None when fewer than two weeks are stored.
    """
    with engine.connect() as conn:
        periods = conn.execute(text("SELECT DISTINCT year, week FROM Competitor_Rankings "
                                    "ORDER BY year DESC, week DESC LIMIT 2")).fetchall()
        if len(periods) < 2:
            return None
        (cy, cw), (py, pw) = periods[0], periods[1]
        sql = ("SELECT competitor_id, ranking_name, `rank` AS rank_value, movement FROM Competitor_Rankings "
               "WHERE year = :y AND week = :w")
        cur = pd.read_sql(text(sql), conn, params={"y": int(cy), "w": int(cw)})
        prev = pd.read_sql(text(sql), conn, params={"y": int(py), "w": int(pw)})
    merged = cur.merge(prev[["competitor_id", "ranking_name", "rank_value"]], on=["competitor_id", "ranking_name"],
                       suffixes=("", "_prev"))
    if merged.empty:
        return {"current": (int(cy), int(cw)), "previous": (int(py), int(pw)), "compared": 0, "match_up_pct": 0.0,
                "match_down_pct": 0.0, "new_players": int(len(cur)), "convention": "no overlap"}
    real_change = merged["rank_value_prev"] - merged["rank_value"]       # positive = moved up the table
    up = float((merged["movement"] == real_change).mean() * 100)
    down = float((merged["movement"] == -real_change).mean() * 100)
    convention = ("positive movement = moved up" if up >= down else "positive movement = moved down")
    return {"current": (int(cy), int(cw)), "previous": (int(py), int(pw)), "compared": int(len(merged)),
            "match_up_pct": round(up, 1), "match_down_pct": round(down, 1),
            "new_players": int(len(cur) - len(merged)), "convention": convention}


# ------------------------------------------------------------------- report
def build_report(engine) -> tuple[str, pd.DataFrame, dict]:
    sizes, placeholders = table_sizes(engine), placeholder_table(engine)
    integrity, domain, outliers = integrity_checks(engine), domain_checks(engine), outlier_table(engine)
    movement = movement_validation(engine)
    statuses = pd.concat([integrity["Status"], domain["Status"]])
    summary = {"pass": int((statuses == "PASS").sum()), "warn": int((statuses == "WARN").sum()),
               "info": int((statuses == "INFO").sum())}
    period = latest_period(engine)

    parts = [
        "# Data quality report",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · database `{config.DB_URL.database}` · "
        f"latest ranking snapshot: {f'year {period[0]}, week {period[1]}' if period else 'none'}",
        f"**Summary:** {summary['pass']} checks passed, {summary['warn']} warnings, {summary['info']} informational findings.",
        "## 1. Table sizes", md_table(sizes),
        "## 2. Missing values and placeholders",
        "Each row shows how many values were missing in the API data, what the pipeline did, and why.",
        md_table(placeholders),
        "## 3. Integrity, duplicates and ties", md_table(integrity),
        "## 4. Domain checks (values must make sense)", md_table(domain),
        "## 5. Outliers (IQR rule: above Q3 + 1.5 × IQR)", md_table(outliers),
        "Outliers are **kept**: very high points belong to the best players, who are the most important rows. "
        "ATP and WTA points use different scales, so they are summarised per list.",
        "## 6. Week-over-week validation of `movement`",
    ]
    if movement is None:
        parts.append("Only one ranking week is stored, so this check is skipped. Run the weekly refresh "
                     "(`python -m api.refresh`) after the next ranking week appears.")
    else:
        parts.append(
            f"Compared week {movement['current']} with week {movement['previous']} for {movement['compared']:,} players "
            f"present in both ({movement['new_players']:,} new). The stored `movement` equals the real rank change for "
            f"**{max(movement['match_up_pct'], movement['match_down_pct'])}%** of them, which means: **{movement['convention']}**.")
    return "\n\n".join(parts) + "\n", placeholders, summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit the quality of the data in the tennis database.")
    parser.add_argument("--out", default=str(REPORT_DIR), help="folder for the report files")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        engine = create_engine(config.DB_URL, connect_args=config.DB_CONNECT_ARGS)
        report, placeholders, summary = build_report(engine)
    except SQLAlchemyError as exc:
        logger.error("Database error: %s", exc)
        return 1
    (out / "data_quality_report.md").write_text(report, encoding="utf-8")
    placeholders.to_csv(out / "data_quality_placeholders.csv", index=False)
    logger.info("Wrote %s and data_quality_placeholders.csv", out / "data_quality_report.md")
    logger.info("Checks passed: %d | warnings: %d | informational: %d", summary["pass"], summary["warn"], summary["info"])
    return 0 if summary["warn"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
