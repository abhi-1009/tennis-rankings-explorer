"""Venues page: filters, world map and rankings of countries and complexes, each with a takeaway."""
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import settings
from dashboard.charts import panel, show_df, show_plot
from dashboard.components import card_grid, card_html, kpi_grid, need_data, pct, section, takeaway
from dashboard.database import in_clause, run_query, scalar


def render() -> None:
    section("Venues and complexes", "where tennis is played")
    countries = run_query("SELECT DISTINCT country_name FROM Venues ORDER BY country_name")
    if countries.empty:
        need_data(pd.DataFrame())
        return
    with panel():
        c1, c2 = st.columns([2, 1])
        sel = c1.multiselect("Country", countries["country_name"].tolist())
        search = c2.text_input("Search venue or complex", placeholder="e.g. Nacional", max_chars=80).strip()
    params: dict = {}
    where = ["1=1"]
    if sel:
        where.append(in_clause("v.country_name", sel, params, "c"))
    if search:
        where.append("(v.venue_name LIKE :q OR cx.complex_name LIKE :q)")
        params["q"] = f"%{search}%"
    base = f"FROM Venues v LEFT JOIN Complexes cx ON cx.complex_id = v.complex_id WHERE {' AND '.join(where)}"
    total = int(scalar(f"SELECT COUNT(*) {base}", params))
    kpi_grid([
        ("🏟️", "Matching venues", f"{total:,}", "after filters", "#c6ff3d"),
        ("🏙️", "Cities", f"{int(scalar(f'SELECT COUNT(DISTINCT v.city_name) {base}', params)):,}", "in this selection", "#22d3ee"),
        ("🕒", "Timezones", f"{int(scalar(f'SELECT COUNT(DISTINCT v.timezone) {base}', params)):,}", "in this selection", "#a78bfa"),
    ])
    show_df(run_query("SELECT v.venue_name, cx.complex_name, v.city_name, v.country_name, v.timezone "
                      f"{base} ORDER BY v.country_name, v.venue_name LIMIT 300", params), height=340)
    st.caption("Showing up to 300 rows. Use the filters to narrow the list.")

    per_country = run_query("SELECT country_name, country_code, COUNT(*) AS venues FROM Venues "
                            "GROUP BY country_name, country_code ORDER BY venues DESC")
    if per_country.empty:
        return
    all_venues = int(per_country["venues"].sum())
    fig = px.choropleth(per_country, locations="country_code", color="venues", hover_name="country_name",
                        color_continuous_scale=settings.SCALE, title="Venues around the world")
    fig.update_geos(bgcolor="rgba(0,0,0,0)", showframe=False, showcountries=True, countrycolor="rgba(255,255,255,.18)",
                    landcolor="rgba(255,255,255,.05)", showocean=False, projection_type="natural earth")
    show_plot(fig, height=460, legend=False)
    lead = per_country.iloc[0]
    takeaway(f"Venues exist in {len(per_country)} countries; {lead['country_name']} hosts the most "
             f"({int(lead['venues']):,}, {pct(lead['venues'], all_venues):.0f}% of all venues).")

    left, right = st.columns(2)
    with left:
        show_plot(px.bar(per_country.head(15), x="country_name", y="venues", color="venues",
                         color_continuous_scale=settings.SCALE, title="Top 15 countries by venues"), legend=False)
        takeaway(f"The 5 busiest countries host {pct(per_country.head(5)['venues'].sum(), all_venues):.0f}% of all venues.")
    with right:
        multi = run_query("""SELECT cx.complex_name, COUNT(v.venue_id) AS venues
                             FROM Complexes cx JOIN Venues v ON v.complex_id = cx.complex_id
                             GROUP BY cx.complex_id, cx.complex_name HAVING COUNT(v.venue_id) > 1
                             ORDER BY venues DESC, cx.complex_name LIMIT 12""")
        if multi.empty:
            card_grid([card_html("🏛️", "Single-venue complexes", "Every complex has exactly one venue.", "#22d3ee")], 1)
        else:
            show_plot(px.bar(multi, x="venues", y="complex_name", orientation="h", color="venues",
                             color_continuous_scale=settings.SCALE, title="Complexes with more than one venue")
                      .update_yaxes(autorange="reversed"), legend=False)
            takeaway(f"{multi.iloc[0]['complex_name']} is the largest complex, with {int(multi.iloc[0]['venues'])} venues.")
