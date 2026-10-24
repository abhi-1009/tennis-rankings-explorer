"""Players page: search, filters, CSV export and a profile card."""
import pandas as pd
import streamlit as st

from dashboard.charts import panel, show_df
from dashboard.components import card_grid, card_html, esc, html_block, movement_html, need_data, section


def render(rk: pd.DataFrame) -> None:
    section("Players", "search, filter and open a profile")
    if not need_data(rk):
        return
    with panel():
        c1, c2, c3 = st.columns([1, 1.4, 2])
        tour = c1.selectbox("Ranking list", ["All"] + sorted(rk["ranking_name"].unique()))
        name_q = c2.text_input("Search by name", placeholder="e.g. Heliovaara", max_chars=60).strip()
        countries = c3.multiselect("Country", sorted(rk["country"].unique()))
        c4, c5 = st.columns(2)
        max_rank = int(rk["rank"].max())
        rank_range = c4.slider("Rank range", 1, max_rank, (1, min(100, max_rank)))
        min_points = c5.slider("Minimum points", 0, int(rk["points"].max()), 0)

    df = rk[rk["rank"].between(*rank_range) & (rk["points"] >= min_points)]
    if tour != "All":
        df = df[df["ranking_name"] == tour]
    if name_q:
        df = df[df["name"].str.contains(name_q, case=False, na=False, regex=False)]
    if countries:
        df = df[df["country"].isin(countries)]
    df = df.sort_values(["ranking_name", "rank", "points"], ascending=[True, True, False])

    html_block(f"<div class='chips' style='margin:.6rem 0'><span class='chip'>✅ {len(df):,} competitors match</span>"
               f"<span class='chip'>🌍 {df['country'].nunique():,} countries</span></div>")
    show_df(df[["ranking_name", "rank", "name", "country", "points", "movement", "competitions_played"]]
            .rename(columns={"ranking_name": "list", "competitions_played": "played"}), height=360)
    st.download_button("⬇ Download filtered results (CSV)", df.to_csv(index=False), "players.csv", "text/csv")

    section("Competitor profile")
    if df.empty:
        card_grid([card_html("🔍", "Nothing to show", "No competitor matches the current filters. Widen the filters above.", "#fb923c")], 1)
        return
    options = df.head(500)
    labels = (options["name"] + " · " + options["country_code"] + " · " + options["ranking_name"]
              + " #" + options["rank"].astype(str)).tolist()
    choice = st.selectbox("Choose a competitor", labels)
    row = options.iloc[labels.index(choice)]
    initials = "".join(part[0] for part in str(row["name"]).replace(",", " ").split()[:2]).upper() or "?"
    html_block(f"""
    <div class="profile"><div class="avatar">{esc(initials)}</div>
      <div><h3>{esc(row['name'])}</h3><p>{esc(row['country'])} ({esc(row['country_code'])}) · {esc(row['ranking_name'])} · {esc(row['gender'])}</p></div>
      <div class="stats">
        <div class="stat"><b>#{int(row['rank'])}</b><span>Rank</span></div>
        <div class="stat">{movement_html(int(row['movement']))}<span>Movement</span></div>
        <div class="stat"><b>{int(row['points']):,}</b><span>Points</span></div>
        <div class="stat"><b>{int(row['competitions_played'])}</b><span>Played</span></div>
      </div></div>""")
