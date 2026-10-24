"""Insights page: live insights, recommendations, limitations, acknowledgements and thank-you."""
import pandas as pd

from dashboard import settings
from dashboard.components import card_grid, card_html, esc, html_block, need_data, section
from dashboard.database import scalar
from dashboard.insights_calc import compute_insights
from dashboard.theme import tech_badges


def render(rk: pd.DataFrame) -> None:
    section("Key insights", "calculated live from the database")
    insights = compute_insights(rk)
    if insights:
        card_grid([card_html(i, t, esc(b), a) for i, t, b, a in insights])
    else:
        need_data(rk)

    rows = int(scalar("SELECT COUNT(*) FROM Competitor_Rankings"))
    section("Recommendations")
    card_grid([
        card_html("🔁", "Automate weekly refresh", "Schedule the extract and load scripts so rankings stay current without manual work.", "#c6ff3d"),
        card_html("🕰️", "Keep ranking history", "The year and week columns already allow many weeks, so store them to unlock trend lines.", "#22d3ee"),
        card_html("➕", "Add singles and match data", "Include singles rankings, results and head-to-head records for deeper performance analysis.", "#a78bfa"),
        card_html("⚡", "Tune and scale", "Add summary tables for heavy queries, and host MySQL and the app in the cloud for sharing.", "#f472b6"),
        card_html("🔐", "Harden access", "Give the app a dedicated read-only database user and keep keys in environment variables.", "#fb923c"),
        card_html("🧭", "Improve exploration", "Add player comparison, bookmarks and exports to make analysis faster.", "#facc15"),
    ])

    section("Limitations")
    card_grid([
        card_html("⏳", "Trial API limits", "The trial key has a time limit, a request quota and rate limits, which restrict how often data can be refreshed.", "#f87171"),
        card_html("📸", "Snapshot data", f"The ranking table holds {rows:,} rows in total, so long-term trends are limited by how many weekly snapshots are stored.", "#fb923c"),
        card_html("🧩", "Placeholders", "Missing API values are stored as 'Unknown' or 'N/A' to satisfy NOT NULL constraints.", "#facc15"),
        card_html("👥", "Doubles partners", "Partners appear as separate competitors; the pairing itself is not modelled in the schema.", "#a78bfa"),
        card_html("🗺️", "Coarse geography", "Venues have no coordinates, so maps work at country level only.", "#22d3ee"),
        card_html("🎯", "No match results", "The dataset covers events, venues and rankings, not match scores or player statistics.", "#c6ff3d"),
    ])

    section("Acknowledgement")
    card_grid([
        card_html("📡", "Data provider", "Sincere thanks to <b>Sportradar</b> for the Tennis API and the data behind this project.", "#c6ff3d"),
        card_html("🎓", "Mentors and sessions", "Thanks to the project orientation, Streamlit and doubt-clarification sessions and everyone who offered guidance.", "#22d3ee"),
        card_html("🛠️", "Open-source tools", "Python, pandas, SQLAlchemy, MySQL, Streamlit and Plotly made this build possible.", "#a78bfa"),
    ])
    html_block(f"""
    <div class="thanks"><div style="font-size:3rem">🎾</div><h2>Thank you for exploring!</h2>
    <p>Game, set and match. I hope this dashboard made tennis data easier to explore.<br>Built by <b>{esc(settings.AUTHOR_NAME)}</b></p>
    <div class="tech-row" style="justify-content:center">{tech_badges()}</div></div>""")
