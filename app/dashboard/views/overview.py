"""Overview page: KPI cards, headline charts (each with a takeaway) and the top-5 spotlight."""
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import settings
from dashboard.charts import show_plot
from dashboard.components import kpi_grid, leaderboard_html, need_data, pct, section, takeaway
from dashboard.database import run_query, scalar


def render(rk: pd.DataFrame, period) -> None:
    section("Dashboard overview", f"rankings snapshot: year {period[0]}, week {period[1]}" if period else "")
    if not need_data(rk):
        return
    best = rk.loc[rk["points"].idxmax()]
    kpi_grid([
        ("🧑‍🤝‍🧑", "Total competitors", f"{int(scalar('SELECT COUNT(*) FROM Competitors')):,}", "in the database", "#c6ff3d"),
        ("🌍", "Countries represented", f"{int(scalar('SELECT COUNT(DISTINCT country) FROM Competitors')):,}", "by ranked players", "#22d3ee"),
        ("⭐", "Highest points", f"{int(best['points']):,}", str(best["name"]), "#facc15"),
        ("🎾", "Competitions", f"{int(scalar('SELECT COUNT(*) FROM Competitions')):,}", "events and sub-events", "#a78bfa"),
        ("🏟️", "Venues", f"{int(scalar('SELECT COUNT(*) FROM Venues')):,}", "courts and stadiums", "#f472b6"),
        ("🗺️", "Venue countries", f"{int(scalar('SELECT COUNT(DISTINCT country_name) FROM Venues')):,}", "hosting tennis", "#fb923c"),
    ])

    left, right = st.columns(2)
    with left:
        by_country = (rk.groupby("country")["competitor_id"].nunique().reset_index(name="competitors")
                      .nlargest(10, "competitors"))
        show_plot(px.bar(by_country, x="country", y="competitors", color="competitors",
                         color_continuous_scale=settings.SCALE, title="Top 10 countries by competitors"), legend=False)
        field = rk["competitor_id"].nunique()
        lead, top3 = by_country.iloc[0], by_country.head(3)["competitors"].sum()
        takeaway(f"{lead['country']} has the most ranked players ({int(lead['competitors'])}, "
                 f"{pct(lead['competitors'], field):.0f}% of the field); the top 3 countries hold {pct(top3, field):.0f}%.")
    with right:
        by_cat = run_query("""SELECT cat.category_name, COUNT(*) AS competitions
                              FROM Competitions c JOIN Categories cat ON cat.category_id = c.category_id
                              GROUP BY cat.category_name ORDER BY competitions DESC""")
        if not by_cat.empty:
            show_plot(px.pie(by_cat, names="category_name", values="competitions", hole=0.55,
                             title="Competitions per category"))
            top = by_cat.iloc[0]
            takeaway(f"{top['category_name']} is the largest category with {int(top['competitions']):,} competitions "
                     f"({pct(top['competitions'], by_cat['competitions'].sum()):.0f}%).")

    left, right = st.columns(2)
    with left:
        show_plot(px.histogram(rk, x="points", color="ranking_name", nbins=40, barmode="overlay", opacity=0.75,
                               title="Distribution of ranking points"))
        med = rk.groupby("ranking_name")["points"].median()
        medians = ", ".join(f"{name} {value:,.0f}" for name, value in med.items())
        takeaway(f"Most players sit in the low-points tail: median points are {medians}, versus {int(rk['points'].max()):,} "
                 "for the leader. Lists use different scales.")
    with right:
        groups = rk["movement"].map(lambda m: "Positive" if m > 0 else ("Negative" if m < 0 else "Stable"))
        mv = groups.value_counts().reset_index()
        mv.columns = ["movement", "competitors"]
        show_plot(px.pie(mv, names="movement", values="competitors", hole=0.55, title="Weekly rank movement",
                         color="movement", color_discrete_map={"Positive": "#4ade80", "Negative": "#f87171", "Stable": "#94a3b8"}))
        counts = groups.value_counts()
        n = len(rk)
        takeaway(f"{pct(counts.get('Stable', 0), n):.0f}% of players kept the same rank this week, "
                 f"{pct(counts.get('Positive', 0), n):.0f}% show positive movement and {pct(counts.get('Negative', 0), n):.0f}% negative.")

    section("Spotlight", "top 5 of each ranking list")
    lists = sorted(rk["ranking_name"].unique())[:2]
    for col, name in zip(st.columns(len(lists)), lists):
        sub = rk[rk["ranking_name"] == name].sort_values(["rank", "points"], ascending=[True, False]).head(5)
        col.markdown(" ".join(leaderboard_html(sub, f"{name} top 5", "#c6ff3d", "rank").split()), unsafe_allow_html=True)
