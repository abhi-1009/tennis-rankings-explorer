"""Project-wide constants: names, links, colours and page labels."""

# ---- the team (edit here once; the app footer, Introduction page, Insights page and the report all use it)
# "work" = what that member did. Leave it empty ("") and it is simply not shown.
TEAM = [
    {"name": "Abhijit Sinha", "role": "Team leader", "work": "Introduction, full Streamlit dashboard and conclusion"},
    {"name": "Chanchal Hudda", "role": "Team member", "work": "Data extraction"},
    {"name": "Patel Bhagyashree Arvindkumar", "role": "Team member", "work": "SQL part"},
    {"name": "Shubham Priyadarshi Nath", "role": "Team member", "work": "Data cleaning and preparation"},
]
TEAM_NAMES = ", ".join(m["name"] for m in TEAM)
AUTHOR_NAME = TEAM_NAMES               # kept so older code that reads AUTHOR_NAME still works
LIVE_URL = "https://tennis-rankings-explorer-stjtrxsnyclfiewespoedo.streamlit.app/"
REPO_URL = "https://github.com/abhi-1009/tennis-rankings-explorer"

PALETTE = ["#c6ff3d", "#22d3ee", "#a78bfa", "#f472b6", "#fb923c", "#2dd4bf", "#facc15", "#60a5fa"]
SCALE = ["#16245f", "#22d3ee", "#c6ff3d"]

INTRO = "🏠 Introduction"
OVERVIEW = "📊 Overview"
PLAYERS = "🔎 Players"
COUNTRIES = "🌍 Countries"
LEADERBOARDS = "🏆 Leaderboards"
COMPETITIONS = "🎾 Competitions"
VENUES = "🏟️ Venues"
PLAYGROUND = "🧪 SQL Playground"
INSIGHTS = "💡 Insights"
PAGES = [INTRO, OVERVIEW, PLAYERS, COUNTRIES, LEADERBOARDS, COMPETITIONS, VENUES, PLAYGROUND, INSIGHTS]
