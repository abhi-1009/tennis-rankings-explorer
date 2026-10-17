"""Step 3: upsert DataFrames into MySQL (safe to re-run).

Run from the project root:  python -m api.load
Prerequisite: run db/schema.sql once, then python -m api.extract.
"""
import logging

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from api import config, transform

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def upsert(engine, table: str, df: pd.DataFrame) -> None:
    """INSERT ... ON DUPLICATE KEY UPDATE for every row of df."""
    if df.empty:
        logger.warning("No rows for %s, skipping.", table)
        return
    df = df.astype(object).where(df.notna(), None)  # NaN -> NULL
    cols = list(df.columns)
    col_list = ", ".join(f"`{c}`" for c in cols)
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in cols)
    sql = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
               f"ON DUPLICATE KEY UPDATE {updates}")
    with engine.begin() as conn:
        conn.execute(sql, df.to_dict(orient="records"))
    logger.info("Upserted %d rows into %s", len(df), table)


def main() -> None:
    engine = create_engine(config.DB_URL, connect_args=config.DB_CONNECT_ARGS)
    try:
        categories, competitions = transform.parse_competitions(transform.load_raw("competitions"))
        complexes, venues = transform.parse_complexes(transform.load_raw("complexes"))
        competitors, rankings = transform.parse_doubles_rankings(transform.load_raw("doubles_rankings"))

        # Parents before children (foreign keys)
        upsert(engine, "Categories", categories)
        upsert(engine, "Competitions", competitions)
        upsert(engine, "Complexes", complexes)
        upsert(engine, "Venues", venues)
        upsert(engine, "Competitors", competitors)
        upsert(engine, "Competitor_Rankings", rankings)
    except FileNotFoundError as exc:
        logger.error("Raw file missing, run `python -m api.extract` first: %s", exc)
    except SQLAlchemyError as exc:
        logger.error("Database error: %s", exc)


if __name__ == "__main__":
    main()
