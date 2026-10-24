"""SQL Playground: run a read-only query, see the table and draw a chart with an automatic takeaway."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from dashboard import settings
from dashboard.charts import panel, show_df, show_plot
from dashboard.components import card_grid, card_html, esc, kpi_grid, section, takeaway
from dashboard.database import execute_playground
from dashboard.queries_loader import load_queries

PROJECT_ROOT = Path(__file__).resolve().parents[3]   # app/dashboard/views/playground.py -> project root

FEATURED = [
    ("★ Top 10 countries by total points",
     "SELECT c.country, SUM(r.points) AS total_points\nFROM Competitor_Rankings r\n"
     "JOIN Competitors c ON c.competitor_id = r.competitor_id\nGROUP BY c.country\nORDER BY total_points DESC\nLIMIT 10"),
    ("★ Competitions per category",
     "SELECT cat.category_name, COUNT(*) AS competitions\nFROM Competitions c\n"
     "JOIN Categories cat ON cat.category_id = c.category_id\nGROUP BY cat.category_name\nORDER BY competitions DESC"),
    ("★ Venues per country (top 15)",
     "SELECT country_name, COUNT(*) AS venues\nFROM Venues\nGROUP BY country_name\nORDER BY venues DESC\nLIMIT 15"),
    ("★ Rank movement groups",
     "SELECT CASE WHEN movement > 0 THEN 'Positive movement' WHEN movement < 0 THEN 'Negative movement'\n"
     "            ELSE 'No movement' END AS movement_group,\n       COUNT(*) AS competitors\n"
     "FROM Competitor_Rankings\nGROUP BY movement_group"),
    ("★ Average points by ranking list",
     "SELECT ranking_name, ROUND(AVG(points), 1) AS avg_points, MAX(points) AS max_points\n"
     "FROM Competitor_Rankings\nGROUP BY ranking_name"),
]
SCHEMA_REF = {
    "Categories": ["category_id", "category_name"],
    "Competitions": ["competition_id", "competition_name", "parent_id", "type", "gender", "level", "category_id"],
    "Complexes": ["complex_id", "complex_name"],
    "Venues": ["venue_id", "venue_name", "city_name", "country_name", "country_code", "timezone", "complex_id"],
    "Competitors": ["competitor_id", "name", "country", "country_code", "abbreviation"],
    "Competitor_Rankings": ["rank_id", "`rank`", "movement", "points", "competitions_played", "competitor_id",
                            "ranking_name", "year", "week", "gender"],
}


def auto_takeaway(plot_df: pd.DataFrame, kind: str, x: str, y: str) -> None:
    """Write a one-line takeaway that fits the chart the user just drew."""
    values = pd.to_numeric(plot_df[y], errors="coerce")
    if values.dropna().empty:
        return
    if kind in ("Histogram", "Box"):
        takeaway(f"{y} ranges from {values.min():,.1f} to {values.max():,.1f}, with a median of {values.median():,.1f}.")
        return
    if kind == "Scatter" and pd.api.types.is_numeric_dtype(plot_df[x]):
        corr = pd.to_numeric(plot_df[x], errors="coerce").corr(values)
        if pd.notna(corr):
            takeaway(f"The correlation between {x} and {y} is {corr:.2f}.")
            return
    hi, lo = values.idxmax(), values.idxmin()
    if kind == "Pie / donut" and values.sum():
        takeaway(f"{plot_df.loc[hi, x]} is the largest slice, with {100 * values.max() / values.sum():.0f}% of the total {y}.")
    else:
        takeaway(f"Highest {y}: {plot_df.loc[hi, x]} ({values.max():,.1f}); lowest: {plot_df.loc[lo, x]} ({values.min():,.1f}).")


def chart_builder(df: pd.DataFrame) -> None:
    numeric = df.select_dtypes("number").columns.tolist()
    others = [c for c in df.columns if c not in numeric]
    if not numeric:
        card_grid([card_html("📉", "No numeric column to chart",
                             "Add a number to your query, for example <b>COUNT(*)</b>, <b>SUM(points)</b> or <b>AVG(points)</b>.",
                             "#fb923c")], 1)
        return
    cols = list(df.columns)
    x_default = others[0] if others else cols[0]
    c1, c2, c3, c4 = st.columns(4)
    kind = c1.selectbox("Chart type", ["Bar", "Horizontal bar", "Line", "Area", "Pie / donut", "Scatter", "Histogram", "Box"], key="pg_kind")
    x = c2.selectbox("X axis / labels", cols, index=cols.index(x_default), key="pg_x")
    y = c3.selectbox("Y axis / values", [c for c in numeric if c != x] or numeric, key="pg_y")
    colour = c4.selectbox("Colour by", ["None"] + others, key="pg_c")
    colour = None if colour == "None" else colour
    plot_df = df.head(60)
    if len(df) > 60:
        st.caption("Charting the first 60 rows to keep it readable.")
    try:
        if kind == "Bar":
            fig = px.bar(plot_df, x=x, y=y, color=colour or y, color_continuous_scale=settings.SCALE if not colour else None)
        elif kind == "Horizontal bar":
            fig = px.bar(plot_df, x=y, y=x, orientation="h", color=colour or y,
                         color_continuous_scale=settings.SCALE if not colour else None).update_yaxes(autorange="reversed")
        elif kind == "Line":
            fig = px.line(plot_df, x=x, y=y, color=colour, markers=True)
        elif kind == "Area":
            fig = px.area(plot_df, x=x, y=y, color=colour)
        elif kind == "Pie / donut":
            fig = px.pie(plot_df, names=x, values=y, hole=0.5)
        elif kind == "Scatter":
            fig = px.scatter(plot_df, x=x, y=y, color=colour)
        elif kind == "Histogram":
            fig = px.histogram(df, x=y, color=colour, nbins=30)
        else:
            fig = px.box(df, x=colour, y=y) if colour else px.box(df, y=y)
        show_plot(fig, height=420, legend=kind == "Pie / donut" or bool(colour))
        auto_takeaway(df if kind in ("Histogram", "Box") else plot_df, kind, x, y)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"This column combination cannot be drawn as a {kind.lower()} chart ({exc}). Try another one.")


def render() -> None:
    section("SQL Playground", "write read-only SQL, see the table, draw the chart")
    path = PROJECT_ROOT / "sql" / "queries.sql"
    presets = list(FEATURED)
    if path.exists():
        presets += [(f"{qid}  {title}", sql) for qid, title, sql in load_queries(path)]
    names = ["✏️ Write my own query"] + [p[0] for p in presets]
    lookup = dict(presets)
    st.session_state.setdefault("pg_sql", FEATURED[0][1])

    def load_preset() -> None:
        choice = st.session_state.get("pg_preset")
        if choice in lookup:
            st.session_state["pg_sql"] = lookup[choice]

    card_grid([
        card_html("🛡️", "Safe by design", "Only one read-only statement runs per click. Data-changing keywords are blocked and the session is read-only.", "#c6ff3d"),
        card_html("⚡", "Instant charts", "Run any SELECT, then pick a chart type and columns in the Chart tab.", "#22d3ee"),
        card_html("💡", "Tip", "Wrap the column <b>`rank`</b> in backticks, because RANK is a reserved word in MySQL 8.", "#a78bfa"),
    ])
    with panel():
        c1, c2 = st.columns([3, 1])
        c1.selectbox("Start from an example", names, key="pg_preset", on_change=load_preset)
        max_rows = c2.selectbox("Max rows", [100, 500, 1000, 5000], index=2)
        st.text_area("SQL query", key="pg_sql", height=210, label_visibility="collapsed")
        run = st.button("▶ Run query", key="pg_run")
    with st.expander("📚 Tables and columns"):
        card_grid([card_html("🗂️", table, "<br>".join(f"• {esc(c)}" for c in cols), settings.PALETTE[i % len(settings.PALETTE)])
                   for i, (table, cols) in enumerate(SCHEMA_REF.items())])

    if run:
        try:
            df, truncated, elapsed = execute_playground(st.session_state["pg_sql"], int(max_rows))
            st.session_state["pg_result"] = {"df": df, "truncated": truncated, "elapsed": elapsed, "error": None}
        except ValueError as exc:
            st.session_state["pg_result"] = {"error": str(exc)}
        except SQLAlchemyError as exc:
            st.session_state["pg_result"] = {"error": f"Database error: {getattr(exc, 'orig', exc)}"}

    result = st.session_state.get("pg_result")
    if not result:
        card_grid([card_html("👆", "Ready when you are", "Pick an example or write a query, then press <b>Run query</b>.", "#22d3ee")], 1)
        return
    if result.get("error"):
        card_grid([card_html("⚠️", "Query could not run", esc(result["error"]), "#f87171")], 1)
        return
    df = result["df"]
    kpi_grid([
        ("📄", "Rows returned", f"{len(df):,}", "capped at the max rows setting" if result["truncated"] else "complete result", "#c6ff3d"),
        ("🧱", "Columns", f"{len(df.columns):,}", ", ".join(map(str, df.columns[:4])), "#22d3ee"),
        ("⏱️", "Run time", f"{result['elapsed'] * 1000:,.0f} ms", "round trip to MySQL", "#a78bfa"),
    ])
    if df.empty:
        card_grid([card_html("🫥", "No rows returned", "The query ran but nothing matched. Check your WHERE conditions.", "#fb923c")], 1)
        return
    tab_table, tab_chart = st.tabs(["📋 Result table", "📊 Chart"])
    with tab_table:
        show_df(df, height=380)
        st.download_button("⬇ Download CSV", df.to_csv(index=False), "playground_result.csv", "text/csv")
    with tab_chart:
        chart_builder(df)
