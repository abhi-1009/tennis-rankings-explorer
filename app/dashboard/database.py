"""Database access: shared engines, cached queries and the read-only playground runner."""
import decimal
import time

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from api import config
from dashboard.sqlguard import escape_colons, validate_sql


@st.cache_resource
def get_engine():
    """Shared engine for the dashboard pages."""
    return create_engine(config.DB_URL, pool_pre_ping=True, pool_recycle=1800,
                         connect_args=config.DB_CONNECT_ARGS)


@st.cache_resource
def get_readonly_engine():
    """Separate engine for the SQL Playground: read-only MySQL session, no connection reuse."""
    args = dict(config.DB_CONNECT_ARGS)
    if str(config.DB_URL).startswith("mysql"):
        args["init_command"] = "SET SESSION TRANSACTION READ ONLY"
    return create_engine(config.DB_URL, poolclass=NullPool, connect_args=args)


@st.cache_data(ttl=300, show_spinner=False)
def _run(sql: str, params: dict) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run a query and return a DataFrame; show a friendly error instead of crashing."""
    try:
        return _run(sql, params or {})
    except SQLAlchemyError as exc:
        st.error(f"Database error: {exc}")
        return pd.DataFrame()


def scalar(sql: str, params: dict | None = None, default=0):
    """Return the first value of the first row (or `default` when empty)."""
    df = run_query(sql, params)
    if df.empty or pd.isna(df.iloc[0, 0]):
        return default
    return df.iloc[0, 0]


def in_clause(column: str, values: list, params: dict, prefix: str) -> str:
    """Build 'column IN (:p0, :p1, ...)' and register the bound values in params."""
    names = []
    for i, value in enumerate(values):
        params[f"{prefix}{i}"] = value
        names.append(f":{prefix}{i}")
    return f"{column} IN ({', '.join(names)})"


def latest_snapshot() -> dict:
    """Newest (year, week) of EACH ranking list: {'ATP': (2026, 46), 'WTA': (2026, 45)}.

    ATP and WTA publish on different days, so for a few days each week the lists are a week apart.
    """
    df = run_query("SELECT ranking_name, MAX(year * 100 + week) AS yw FROM Competitor_Rankings "
                   "GROUP BY ranking_name ORDER BY ranking_name")
    return {r.ranking_name: (int(r.yw) // 100, int(r.yw) % 100) for r in df.itertuples()}


def snapshot_label(snapshot: dict) -> str:
    """'year 2026, week 44' when all lists agree, otherwise 'ATP week 46 · WTA week 45'."""
    if not snapshot:
        return ""
    if len(set(snapshot.values())) == 1:
        year, week = next(iter(snapshot.values()))
        return f"year {year}, week {week}"
    return " · ".join(f"{name} week {week}" for name, (year, week) in sorted(snapshot.items()))


@st.cache_data(ttl=300, show_spinner=False)
def load_rankings() -> pd.DataFrame:
    """Current rows of every ranking list (each list at its own newest week) joined with competitor details."""
    sql = """
        SELECT r.`rank`, r.movement, r.points, r.competitions_played, r.ranking_name, r.gender,
               c.competitor_id, c.name, c.country, c.country_code
        FROM Competitor_Rankings r
        JOIN (SELECT ranking_name, MAX(year * 100 + week) AS latest_yw
              FROM Competitor_Rankings GROUP BY ranking_name) cur
          ON cur.ranking_name = r.ranking_name AND cur.latest_yw = r.year * 100 + r.week
        JOIN Competitors c ON c.competitor_id = r.competitor_id
    """
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def execute_playground(sql: str, max_rows: int):
    """Validate and run one read-only statement. Returns (dataframe, was_truncated, seconds)."""
    stmt = validate_sql(sql)
    engine = get_readonly_engine()
    started = time.perf_counter()
    with engine.connect() as conn:
        if engine.dialect.name == "mysql":
            conn.exec_driver_sql("SET SESSION max_execution_time = 15000")
        result = conn.execute(text(escape_colons(stmt)))
        columns = list(result.keys())
        rows = [tuple(r) for r in result.fetchmany(max_rows + 1)]
    seen, unique = {}, []
    for col in columns:
        seen[col] = seen.get(col, 0) + 1
        unique.append(col if seen[col] == 1 else f"{col}_{seen[col]}")
    df = pd.DataFrame(rows, columns=unique)
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(1).tolist()
            if sample and isinstance(sample[0], decimal.Decimal):
                df[col] = df[col].astype(float)
    return df.head(max_rows), len(df) > max_rows, time.perf_counter() - started
