"""Tennis Rankings Explorer: entry point of the Streamlit dashboard.

The code is split into the `dashboard` package:
    settings.py       constants (names, links, colours, page labels)
    database.py       engines, cached queries, read-only playground runner
    sqlguard.py       SQL safety checks (pure Python)
    charts.py         Plotly / dataframe helpers
    components.py     cards, KPI tiles, takeaways, pager
    theme.py          CSS, logos, header and footer
    insights_calc.py  numbers behind the insight cards
    queries_loader.py reads sql/queries.sql
    views/            one module per page
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR.parent))   # project root: makes the `api` package importable
sys.path.insert(0, str(APP_DIR))          # makes the `dashboard` package importable

st.set_page_config(page_title="Tennis Rankings Explorer", page_icon="🎾", layout="wide",
                   initial_sidebar_state="collapsed")

from dashboard import settings  # noqa: E402
from dashboard.components import card_grid, card_html, esc, pager  # noqa: E402
from dashboard.database import latest_period, load_rankings  # noqa: E402
from dashboard.theme import inject_css, render_footer, render_header  # noqa: E402
from dashboard.views import (competitions, countries, intro, insights, leaderboards,  # noqa: E402
                             overview, players, playground, venues)


def main() -> None:
    inject_css()
    render_header()
    st.session_state.setdefault("nav", settings.PAGES[0])
    label = st.radio("Navigation", settings.PAGES, key="nav", horizontal=True, label_visibility="collapsed")

    period = latest_period()
    rk = load_rankings(*period) if period else pd.DataFrame()

    renderers = {
        settings.INTRO: lambda: intro.render(rk, period),
        settings.OVERVIEW: lambda: overview.render(rk, period),
        settings.PLAYERS: lambda: players.render(rk),
        settings.COUNTRIES: lambda: countries.render(rk),
        settings.LEADERBOARDS: lambda: leaderboards.render(rk),
        settings.COMPETITIONS: competitions.render,
        settings.VENUES: venues.render,
        settings.PLAYGROUND: playground.render,
        settings.INSIGHTS: lambda: insights.render(rk),
    }
    try:
        renderers[label]()
    except Exception as exc:  # noqa: BLE001  keep the app alive and explain the problem
        card_grid([card_html("🛠️", "Something went wrong on this page", esc(exc), "#f87171")], 1)

    pager(label)
    render_footer()


main()
