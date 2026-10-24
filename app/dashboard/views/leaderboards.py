"""Leaderboards page: top-ranked and highest-points lists plus a points chart."""
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import settings
from dashboard.charts import panel, show_plot
from dashboard.components import leaderboard_html, need_data, section, takeaway


def render(rk: pd.DataFrame) -> None:
    section("Leaderboards", "the best of the best")
    if not need_data(rk):
        return
    with panel():
        c1, c2 = st.columns([1, 2])
        tour = c1.selectbox("Ranking list", sorted(rk["ranking_name"].unique()), key="lb_tour")
        top_n = c2.slider("How many players", 5, 25, 10, key="lb_n")
    df = rk[rk["ranking_name"] == tour]
    by_rank = df.sort_values(["rank", "points"], ascending=[True, False]).head(top_n)
    by_points = df.sort_values(["points", "rank"], ascending=[False, True]).head(top_n)
    left, right = st.columns(2)
    left.markdown(" ".join(leaderboard_html(by_rank, f"👑 Top ranked · {tour}", "#c6ff3d", "rank").split()), unsafe_allow_html=True)
    right.markdown(" ".join(leaderboard_html(by_points, f"⚡ Highest points · {tour}", "#22d3ee", "points").split()), unsafe_allow_html=True)
    show_plot(px.bar(by_points.assign(label=by_points["name"]), x="points", y="label", orientation="h", color="points",
                     color_continuous_scale=settings.SCALE, title=f"Points of the top {top_n} · {tour}")
              .update_yaxes(autorange="reversed"), height=max(320, 32 * top_n + 120), legend=False)
    first = by_points.iloc[0]
    takeaway(f"{first['name']} leads the {tour} points table with {int(first['points']):,}; the top {top_n} range from "
             f"{int(by_points['points'].min()):,} to {int(by_points['points'].max()):,} points.")
