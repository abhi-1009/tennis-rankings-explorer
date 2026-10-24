"""Countries page: podium, ranking charts, bubble chart, world map and treemap, each with a takeaway."""
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import settings
from dashboard.charts import show_df, show_plot
from dashboard.components import card_grid, card_html, need_data, pct, section, takeaway


def _geo(fig):
    fig.update_geos(bgcolor="rgba(0,0,0,0)", showframe=False, showcountries=True, countrycolor="rgba(255,255,255,.18)",
                    landcolor="rgba(255,255,255,.05)", showocean=False, projection_type="natural earth")
    return fig


def render(rk: pd.DataFrame) -> None:
    section("Country insights", "who dominates the rankings")
    if not need_data(rk):
        return
    agg = (rk.groupby("country")
           .agg(competitors=("competitor_id", "nunique"), total_points=("points", "sum"),
                average_points=("points", "mean"), country_code=("country_code", "first"))
           .round(1).reset_index().sort_values("competitors", ascending=False))
    medals, accents = ["🥇", "🥈", "🥉"], ["#facc15", "#cbd5e1", "#fb923c"]
    card_grid([card_html(medals[i], r["country"],
                         f"<b>{int(r['competitors']):,}</b> competitors · <b>{int(r['total_points']):,}</b> points "
                         f"· avg <b>{r['average_points']:,.0f}</b>", accents[i])
               for i, (_, r) in enumerate(agg.head(3).iterrows())])

    labels = {"competitors": "competitors", "total_points": "total points", "average_points": "average points"}
    metric = st.selectbox("Rank countries by", list(labels), format_func=lambda m: labels[m].title())
    left, right = st.columns(2)
    with left:
        show_plot(px.bar(agg.nlargest(15, metric), x="country", y=metric, color=metric, color_continuous_scale=settings.SCALE,
                         title=f"Top 15 countries by {labels[metric]}"), legend=False)
        lead = agg.nlargest(1, metric).iloc[0]
        takeaway(f"{lead['country']} leads on {labels[metric]} with {lead[metric]:,.0f}.")
    with right:
        show_plot(px.scatter(agg, x="competitors", y="average_points", size="total_points", color="total_points",
                             hover_name="country", color_continuous_scale=settings.SCALE,
                             title="Depth vs quality (bubble size = total points)"), legend=False)
        deep = agg.nlargest(1, "competitors").iloc[0]
        solid = agg[agg["competitors"] >= 5]
        if not solid.empty:
            best = solid.nlargest(1, "average_points").iloc[0]
            takeaway(f"{deep['country']} has the most players ({int(deep['competitors'])}), while {best['country']} has the "
                     f"highest average points ({best['average_points']:,.0f}) among countries with at least 5 players.")

    show_plot(_geo(px.choropleth(agg, locations="country_code", color="competitors", hover_name="country",
                                 color_continuous_scale=settings.SCALE, title="Where the ranked competitors come from")),
              height=460, legend=False)
    top5 = agg.head(5)["competitors"].sum()
    takeaway(f"Ranked players come from {len(agg)} countries; the 5 largest account for "
             f"{pct(top5, agg['competitors'].sum()):.0f}% of all competitors.")

    show_plot(px.treemap(agg.nlargest(40, "total_points"), path=["country"], values="total_points",
                         color="average_points", color_continuous_scale=settings.SCALE,
                         title="Share of total points (top 40 countries)"), height=420, legend=False)
    by_points = agg.sort_values("total_points", ascending=False)
    total_pts = by_points["total_points"].sum()
    takeaway(f"{by_points.iloc[0]['country']} holds {pct(by_points.iloc[0]['total_points'], total_pts):.0f}% of all ranking points; "
             f"the top 5 countries hold {pct(by_points.head(5)['total_points'].sum(), total_pts):.0f}%.")
    with st.expander("📋 Full country table"):
        show_df(agg[["country", "competitors", "total_points", "average_points"]], height=340)
