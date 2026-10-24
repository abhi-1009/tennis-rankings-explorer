"""Introduction page: story, problem statement, key result and the assumptions box."""
import pandas as pd
import streamlit as st

from dashboard import settings
from dashboard.components import card_grid, card_html, esc, goto, html_block, kpi_grid, pct, section
from dashboard.database import scalar
from dashboard.insights_calc import key_result, top_category
from dashboard.theme import LOGO_URI


def _assumption_cards(rk: pd.DataFrame, period) -> list:
    snapshot = f"year {period[0]}, week {period[1]}" if period else "the latest week"
    cat = top_category()
    coverage = (f"{cat[0]} makes up {pct(cat[1], cat[2]):.0f}% of competitions, and counts reflect what the "
                "Sportradar API covers." if cat else "Counts reflect what the Sportradar API covers.")

    def body(what: str, effect: str) -> str:
        return f"{esc(what)}<span class='effect'>Effect: {esc(effect)}</span>"

    return [
        card_html("🎯", "Selection bias", body(f"Only ranked doubles players are included ({len(rk):,} rows).",
                  "unranked and junior players are invisible, so findings describe the ranked elite."), "#c6ff3d"),
        card_html("📸", "Time window", body(f"One ranking snapshot is shown: {snapshot}.",
                  "movement covers one week; long-term trends need more snapshots."), "#22d3ee"),
        card_html("📡", "Coverage bias", body(coverage, "lower-tier events may look more common than they really are."), "#a78bfa"),
        card_html("⚖️", "Not like-for-like", body("ATP and WTA points use different scales.",
                  "compare ranks within a list, not points across lists."), "#f472b6"),
        card_html("👥", "Doubles partners", body("Each partner is stored as a separate competitor.",
                  "country counts are players, not pairs."), "#fb923c"),
        card_html("🧩", "Placeholders", body("Missing API values are stored as Unknown or N/A.",
                  "a small share of venue and competitor fields carry no real value."), "#facc15"),
        card_html("🔒", "No data leakage", body("This is descriptive analytics; nothing is predicted, so there is no train/test split to leak.",
                  "rank and points are linked by definition, so they are not independent."), "#2dd4bf"),
        card_html("⏳", "Trial API key", body("The trial has a time limit and a request quota.",
                  "data is refreshed weekly; the live app reads from the database only."), "#60a5fa"),
    ]


def render(rk: pd.DataFrame, period) -> None:
    html_block(f"""
    <div class="hero"><div>
      <div class="eyebrow">GAME ANALYTICS · SPORTS DATA PROJECT</div>
      <div class="hero-title">Unlocking Tennis Data with the Sportradar API</div>
      <p class="hero-p">From raw nested JSON to a relational database and an interactive dashboard: explore
      competitions, venues and doubles rankings in one place.</p>
      <div class="chips"><span class="chip">🎾 Competitions</span><span class="chip">🏟️ Venues</span>
      <span class="chip">🏆 Rankings</span><span class="chip">🧪 SQL Playground</span></div></div>
      <img class="hero-ball" src="{LOGO_URI}" alt="tennis ball"></div>""")
    st.button("Start exploring →", on_click=goto, args=(settings.OVERVIEW,), key="cta_start")

    section("Introduction and problem statement")
    card_grid([
        card_html("📘", "Introduction",
                  "Tennis produces a huge amount of structured data: tournaments, venues and weekly rankings. "
                  "This project collects it from the <b>Sportradar Tennis API</b>, stores it in a clean "
                  "<b>MySQL</b> schema and presents it through this <b>Streamlit</b> app, so fans, analysts and "
                  "organisers can understand how the sport is organised and who is leading it.", "#c6ff3d"),
        card_html("🎯", "Problem statement",
                  "Sports data arrives as deeply nested JSON that is hard to search, compare or reuse. The "
                  "<b>Sportradar Event Explorer</b> solves this by parsing the API responses, storing them in a "
                  "relational database and offering interactive insight into tournaments, competition hierarchies "
                  "and event details.", "#22d3ee"),
    ], 2)

    section("Who it is for and the key result")
    result_html = "<br>".join(f"• {esc(line)}" for line in key_result(rk))
    card_grid([
        card_html("👥", "Stakeholders", "Tennis analysts, event organisers and sports bodies who plan events, venues and resources.", "#c6ff3d"),
        card_html("❓", "Business question", "How are tennis competitions, venues and doubles rankings organised, and where is activity concentrated?", "#a78bfa"),
        card_html("✅", "Key result", result_html, "#22d3ee"),
    ])

    section("Assumptions, limits and biases", "read these before drawing conclusions")
    card_grid(_assumption_cards(rk, period), 4)

    section("Business use cases")
    card_grid([
        card_html("🧭", "Event exploration", "Navigate competition hierarchies, from parent tournaments to their sub-events.", "#c6ff3d"),
        card_html("📈", "Trend analysis", "See how events spread by type, gender and competition level.", "#22d3ee"),
        card_html("🎽", "Performance insights", "Compare player participation and points across countries and ranking lists.", "#a78bfa"),
        card_html("🧩", "Decision support", "Give organisers and sports bodies data to guide resource allocation.", "#f472b6"),
    ], 4)

    section("How it works", "from API to insight")
    card_grid([
        card_html("🛰️", "Extract", "Python scripts call the Sportradar API with retries and rate-limit handling.", "#c6ff3d", "01"),
        card_html("🧹", "Transform", "pandas flattens nested JSON into clean tables and fills missing values.", "#22d3ee", "02"),
        card_html("🗄️", "Store", "A normalised MySQL schema with primary keys, foreign keys and indexes.", "#a78bfa", "03"),
        card_html("📊", "Visualise", "Streamlit and Plotly turn live SQL results into interactive charts.", "#f472b6", "04"),
    ], 4)

    section("Dataset at a glance", "live counts from MySQL")
    kpi_grid([
        ("🎾", "Competitions", f"{int(scalar('SELECT COUNT(*) FROM Competitions')):,}", "events and sub-events", "#c6ff3d"),
        ("🏷️", "Categories", f"{int(scalar('SELECT COUNT(*) FROM Categories')):,}", "ATP, WTA, ITF and more", "#22d3ee"),
        ("🏛️", "Complexes", f"{int(scalar('SELECT COUNT(*) FROM Complexes')):,}", "sports complexes", "#a78bfa"),
        ("🏟️", "Venues", f"{int(scalar('SELECT COUNT(*) FROM Venues')):,}", "courts and stadiums", "#f472b6"),
        ("🧑‍🤝‍🧑", "Competitors", f"{int(scalar('SELECT COUNT(*) FROM Competitors')):,}", "ranked players", "#fb923c"),
        ("🏆", "Ranking rows", f"{int(scalar('SELECT COUNT(*) FROM Competitor_Rankings')):,}", "doubles rankings", "#facc15"),
    ])

    section("How to use this dashboard")
    card_grid([
        card_html("🧭", "Navigate", "Use the pill menu at the top. Every page has its own filters, and the ← → buttons at the bottom move you along.", "#c6ff3d"),
        card_html("🔍", "Filter and search", "Players, Competitions and Venues pages let you search by name and narrow results with filters.", "#22d3ee"),
        card_html("🧪", "Experiment", "Open the SQL Playground to run your own read-only queries and turn results into charts.", "#a78bfa"),
    ])
