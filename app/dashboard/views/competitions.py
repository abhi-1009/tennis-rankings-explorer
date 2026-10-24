"""Competitions page: filters, paginated table, distribution charts (with takeaways) and hierarchy viewer."""
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import settings
from dashboard.charts import panel, show_df, show_plot
from dashboard.components import card_grid, card_html, kpi_grid, need_data, pct, section, takeaway
from dashboard.database import in_clause, run_query, scalar


def render() -> None:
    section("Competitions explorer", "types, levels, categories and hierarchies")
    types = run_query("SELECT DISTINCT type FROM Competitions ORDER BY type")
    genders = run_query("SELECT DISTINCT gender FROM Competitions ORDER BY gender")
    levels = run_query("SELECT DISTINCT level FROM Competitions WHERE level IS NOT NULL ORDER BY level")
    cats = run_query("SELECT category_name FROM Categories ORDER BY category_name")
    if types.empty:
        need_data(pd.DataFrame())
        return
    with panel():
        c1, c2, c3, c4 = st.columns(4)
        sel_types = c1.multiselect("Type", types["type"].tolist())
        sel_genders = c2.multiselect("Gender", genders["gender"].tolist())
        sel_levels = c3.multiselect("Level", levels["level"].tolist() if not levels.empty else [])
        sel_cats = c4.multiselect("Category", cats["category_name"].tolist())
        search = st.text_input("Search competition name", placeholder="e.g. Vienna", max_chars=80).strip()

    params: dict = {}
    where = ["1=1"]
    if sel_types:
        where.append(in_clause("c.type", sel_types, params, "t"))
    if sel_genders:
        where.append(in_clause("c.gender", sel_genders, params, "g"))
    if sel_levels:
        where.append(in_clause("c.level", sel_levels, params, "l"))
    if sel_cats:
        where.append(in_clause("cat.category_name", sel_cats, params, "k"))
    if search:
        where.append("c.competition_name LIKE :q")
        params["q"] = f"%{search}%"
    base = ("FROM Competitions c LEFT JOIN Categories cat ON cat.category_id = c.category_id "
            f"WHERE {' AND '.join(where)}")
    total = int(scalar(f"SELECT COUNT(*) {base}", params))
    page_size = 100
    pages = max(1, -(-total // page_size))

    kpi_grid([
        ("🎾", "Matching competitions", f"{total:,}", "after filters", "#c6ff3d"),
        ("🗂️", "Categories", f"{int(scalar(f'SELECT COUNT(DISTINCT cat.category_name) {base}', params)):,}", "in this selection", "#22d3ee"),
        ("🌳", "Top-level events", f"{int(scalar(f'SELECT COUNT(*) {base} AND c.parent_id IS NULL', params)):,}", "no parent competition", "#a78bfa"),
    ])
    page = st.number_input("Page", min_value=1, max_value=pages, value=1, help=f"{page_size} rows per page")
    df = run_query("SELECT c.competition_id, c.competition_name, c.type, c.gender, c.level, cat.category_name, c.parent_id "
                   f"{base} ORDER BY c.competition_name LIMIT :limit OFFSET :offset",
                   {**params, "limit": page_size, "offset": int((page - 1) * page_size)})
    show_df(df, height=340)

    left, right = st.columns(2)
    with left:
        dist = run_query("""SELECT cat.category_name, c.type, COUNT(*) AS competitions
                            FROM Competitions c JOIN Categories cat ON cat.category_id = c.category_id
                            GROUP BY cat.category_name, c.type""")
        if not dist.empty:
            show_plot(px.bar(dist, x="category_name", y="competitions", color="type", barmode="stack",
                             title="Competition types by category"))
            by_type = dist.groupby("type")["competitions"].sum().sort_values(ascending=False)
            takeaway(f"{str(by_type.index[0]).title()} is the most common event type, with "
                     f"{pct(by_type.iloc[0], by_type.sum()):.0f}% of competitions.")
    with right:
        gender = run_query("SELECT gender, COUNT(*) AS competitions FROM Competitions GROUP BY gender ORDER BY competitions DESC")
        if not gender.empty:
            show_plot(px.pie(gender, names="gender", values="competitions", hole=0.55, title="Competitions by gender"))
            takeaway(f"{str(gender.iloc[0]['gender']).title()} events make up "
                     f"{pct(gender.iloc[0]['competitions'], gender['competitions'].sum()):.0f}% of competitions.")

    lv = run_query("SELECT level, COUNT(*) AS competitions FROM Competitions WHERE level IS NOT NULL "
                   "GROUP BY level ORDER BY competitions DESC")
    if not lv.empty:
        show_plot(px.bar(lv, x="level", y="competitions", color="competitions", color_continuous_scale=settings.SCALE,
                         title="Competitions by level"), legend=False)
        total_all = int(scalar("SELECT COUNT(*) FROM Competitions"))
        takeaway(f"{lv.iloc[0]['level']} is the most common labelled level, but only "
                 f"{pct(lv['competitions'].sum(), total_all):.0f}% of competitions carry a level label, so level analysis covers a minority of events.")

    section("Competition hierarchy", "parent events and their sub-competitions")
    parents = run_query("""SELECT p.competition_id, p.competition_name, COUNT(s.competition_id) AS sub_competitions
                           FROM Competitions p JOIN Competitions s ON s.parent_id = p.competition_id
                           GROUP BY p.competition_id, p.competition_name
                           ORDER BY sub_competitions DESC, p.competition_name LIMIT 300""")
    if parents.empty:
        card_grid([card_html("🌱", "No hierarchy found", "No competition has sub-competitions in this dataset.", "#fb923c")], 1)
        return
    labels = (parents["competition_name"] + " (" + parents["sub_competitions"].astype(str) + " sub-events)").tolist()
    pick = st.selectbox("Parent competition", labels)
    parent_id = parents.iloc[labels.index(pick)]["competition_id"]
    subs = run_query("SELECT competition_id, competition_name, type, gender, level FROM Competitions "
                     "WHERE parent_id = :p ORDER BY competition_name", {"p": parent_id})
    show_df(subs, height=300)
