"""Create the database (if missing) and all tables on whichever MySQL your settings point to.

Works for local MySQL and for Aiven.  Run from the project root:  python -m db.init_db
"""
import logging
import re
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

from api import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SCHEMA_FILE = Path(__file__).with_name("schema_aiven.sql")


def split_statements(sql: str) -> list:
    """Remove -- comments and split the script into individual statements."""
    sql = re.sub(r"--[^\n]*", "", sql)
    return [part.strip() for part in sql.split(";") if part.strip()]


def main() -> None:
    db_name = config.DB_URL.database
    try:
        # 1) connect to the server (no database selected yet) and create the database
        u = config.DB_URL
        server_url = URL.create(drivername=u.drivername, username=u.username, password=u.password,
                                host=u.host, port=u.port)
        server = create_engine(server_url, connect_args=config.DB_CONNECT_ARGS)
        with server.begin() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                              "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        logger.info("Database %s is ready.", db_name)

        # 2) create the tables
        engine = create_engine(config.DB_URL, connect_args=config.DB_CONNECT_ARGS)
        statements = split_statements(SCHEMA_FILE.read_text(encoding="utf-8"))
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
        logger.info("Ran %d statements from %s", len(statements), SCHEMA_FILE.name)

        with engine.connect() as conn:
            tables = [row[0] for row in conn.execute(text("SHOW TABLES"))]
        logger.info("Tables now in %s: %s", db_name, ", ".join(tables))
    except SQLAlchemyError as exc:
        logger.error("Database error: %s", exc)


if __name__ == "__main__":
    main()
