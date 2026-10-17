"""Tennis Rankings Explorer: a top-navigation Streamlit dashboard for tennis_db.

Run from the project root:  streamlit run app/streamlit_app.py
"""
import base64
import decimal
import html
import re
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api import config  # noqa: E402
from queries_loader import load_queries  # noqa: E402

st.set_page_config(page_title="Tennis Rankings Explorer", page_icon="🎾", layout="wide",
                   initial_sidebar_state="collapsed")

AUTHOR_NAME = "ABHIJIT SINHA"          # <-- change this to your name (shown on the last page and footer)
PALETTE = ["#c6ff3d", "#22d3ee", "#a78bfa", "#f472b6", "#fb923c", "#2dd4bf", "#facc15", "#60a5fa"]
SCALE = ["#16245f", "#22d3ee", "#c6ff3d"]

PAGES = [
    "🏠 Introduction", "📊 Overview", "🔎 Players", "🌍 Countries", "🏆 Leaderboards",
    "🎾 Competitions", "🏟️ Venues", "🧪 SQL Playground", "💡 Insights",
]

# ------------------------------------------------------------------ branding
BALL_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs>"
    "<radialGradient id='g' cx='35%' cy='30%' r='80%'><stop offset='0' stop-color='#f4ff8a'/>"
    "<stop offset='.55' stop-color='#c6ff3d'/><stop offset='1' stop-color='#7fbf1a'/></radialGradient></defs>"
    "<circle cx='50' cy='50' r='46' fill='url(#g)'/>"
    "<path d='M10 28 C 38 40, 38 60, 10 72' fill='none' stroke='white' stroke-width='4' stroke-linecap='round'/>"
    "<path d='M90 28 C 62 40, 62 60, 90 72' fill='none' stroke='white' stroke-width='4' stroke-linecap='round'/></svg>"
)
COURT_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='260' height='140' viewBox='0 0 260 140'>"
    "<g fill='none' stroke='white' stroke-opacity='0.05' stroke-width='1.5'>"
    "<rect x='10' y='10' width='240' height='120'/><line x1='130' y1='10' x2='130' y2='130'/>"
    "<line x1='10' y1='35' x2='250' y2='35'/><line x1='10' y1='105' x2='250' y2='105'/>"
    "<line x1='60' y1='35' x2='60' y2='105'/><line x1='200' y1='35' x2='200' y2='105'/>"
    "<line x1='60' y1='70' x2='200' y2='70'/></g></svg>"
)


def _data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


LOGO_URI = _data_uri(BALL_SVG)
COURT_URI = _data_uri(COURT_SVG)

TECH = [("python", "FFD43B", "Python"), ("mysql", "4DA6D9", "MySQL"), ("pandas", "E70488", "pandas"),
        ("plotly", "7A76FF", "Plotly"), ("streamlit", "FF4B4B", "Streamlit")]


def esc(value) -> str:
    return html.escape(str(value))


def tech_badges(with_sportradar: bool = True) -> str:
    badges = "".join(
        f"<span class='tech'><img src='https://cdn.simpleicons.org/{slug}/{color}' alt=''>{name}</span>"
        for slug, color, name in TECH)
    if with_sportradar:
        badges = "<span class='tech'>📡 Sportradar API</span>" + badges
    return badges


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
html, body, .stApp, button, input, textarea, select {font-family:'Poppins','Segoe UI',sans-serif;}
.stApp {
  background-image: url("__COURT__"),
    radial-gradient(circle at 12% 8%, rgba(198,255,61,.16), transparent 38%),
    radial-gradient(circle at 88% 18%, rgba(34,211,238,.18), transparent 42%),
    radial-gradient(circle at 60% 95%, rgba(167,139,250,.20), transparent 45%),
    linear-gradient(160deg, #060a22 0%, #0c1644 52%, #121d54 100%);
  background-attachment: fixed;
  color:#eaf0ff;
}
header[data-testid="stHeader"] {background:transparent;}
#MainMenu, footer {visibility:hidden;}
[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {display:none;}
.block-container {max-width:1260px; padding-top:1.2rem; padding-bottom:3rem;}

/* ---------- top bar ---------- */
.topbar {display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap;
  padding:.9rem 1.3rem; margin-bottom:.9rem; border-radius:22px;
  background:linear-gradient(135deg, rgba(255,255,255,.11), rgba(255,255,255,.04));
  border:1px solid rgba(255,255,255,.15); backdrop-filter:blur(14px); box-shadow:0 10px 40px rgba(0,0,0,.35);}
.brand {display:flex; align-items:center; gap:.9rem;}
.ball {width:54px; height:54px; animation:bounce 2.4s ease-in-out infinite; filter:drop-shadow(0 8px 12px rgba(198,255,61,.45));}
@keyframes bounce {0%,100%{transform:translateY(0)} 50%{transform:translateY(-9px)}}
.brand-title {font-weight:800; font-size:1.5rem; line-height:1.15;
  background:linear-gradient(90deg,#c6ff3d,#22d3ee,#a78bfa); -webkit-background-clip:text; background-clip:text; color:transparent;}
.brand-sub {font-size:.78rem; color:#a9b8ee;}
.tech-row {display:flex; gap:.5rem; flex-wrap:wrap;}
.tech {display:inline-flex; align-items:center; gap:.4rem; padding:.32rem .75rem; border-radius:999px;
  background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15); font-size:.74rem; font-weight:600; color:#eaf0ff;}
.tech img {height:16px; width:16px;}
.notice {padding:.6rem 1rem; border-radius:14px; margin-bottom:.8rem; font-size:.85rem; color:#fde68a;
  background:rgba(250,204,21,.10); border:1px solid rgba(250,204,21,.35);}

/* ---------- navigation pills (the only st.radio in the app) ---------- */
div[data-testid="stRadio"] > label {display:none;}
div[data-testid="stRadio"] div[role="radiogroup"] {display:flex; flex-wrap:wrap; gap:.35rem; justify-content:center;
  padding:.5rem; border-radius:999px; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.13);
  backdrop-filter:blur(10px); margin-bottom:1.1rem;}
div[data-testid="stRadio"] div[role="radiogroup"] label {margin:0; padding:.5rem 1.05rem; border-radius:999px; cursor:pointer; transition:all .2s ease;}
div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {display:none;}
div[data-testid="stRadio"] div[role="radiogroup"] label:hover {background:rgba(255,255,255,.12); transform:translateY(-1px);}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
  background:linear-gradient(135deg,#c6ff3d,#22d3ee); box-shadow:0 8px 22px rgba(34,211,238,.35);}
div[data-testid="stRadio"] div[role="radiogroup"] label p {font-weight:600; font-size:.88rem; margin:0;}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {color:#0b1230 !important; font-weight:800;}

/* ---------- hero ---------- */
.hero {display:flex; align-items:center; justify-content:space-between; gap:2rem; padding:2.2rem 2.4rem; border-radius:28px;
  background:linear-gradient(120deg, rgba(198,255,61,.16), rgba(34,211,238,.14) 55%, rgba(167,139,250,.18));
  border:1px solid rgba(255,255,255,.18); box-shadow:0 18px 60px rgba(0,0,0,.4); margin-bottom:1rem; animation:rise .7s ease both;}
.eyebrow {font-size:.78rem; letter-spacing:.18em; font-weight:700; color:#c6ff3d;}
.hero-title {font-size:2.35rem; font-weight:800; line-height:1.15; margin:.35rem 0 .6rem; color:#fff;}
.hero-p {font-size:1.02rem; color:#d6defa; max-width:720px; margin:0 0 .9rem;}
.hero-ball {width:170px; height:170px; animation:bounce 3s ease-in-out infinite; filter:drop-shadow(0 18px 24px rgba(198,255,61,.35));}
.chips {display:flex; flex-wrap:wrap; gap:.5rem;}
.chip {padding:.3rem .8rem; border-radius:999px; font-size:.8rem; font-weight:600; background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.2);}
@media (max-width:800px) {.hero {flex-direction:column; text-align:center;} .hero-title {font-size:1.7rem;} .hero-ball {width:110px; height:110px;}}

/* ---------- section titles ---------- */
.section {display:flex; align-items:baseline; gap:.7rem; flex-wrap:wrap; margin:1.3rem 0 .4rem;}
.section h2 {margin:0; font-size:1.45rem; font-weight:800; color:#fff;}
.section small {color:#a9b8ee; font-size:.88rem;}
.section::after {content:""; flex:1; min-width:40px; height:2px; background:linear-gradient(90deg,rgba(198,255,61,.7),transparent);}

/* ---------- cards ---------- */
.grid {display:grid; gap:1rem; margin:.6rem 0 1.1rem;}
.g2 {grid-template-columns:repeat(2,1fr);} .g3 {grid-template-columns:repeat(3,1fr);} .g4 {grid-template-columns:repeat(4,1fr);}
@media (max-width:1000px) {.g3,.g4 {grid-template-columns:repeat(2,1fr);}}
@media (max-width:640px) {.grid {grid-template-columns:1fr !important;}}
.card {position:relative; padding:1.2rem 1.3rem; border-radius:20px; overflow:hidden; animation:rise .6s ease both;
  background:linear-gradient(145deg, rgba(255,255,255,.10), rgba(255,255,255,.035));
  border:1px solid rgba(255,255,255,.14); box-shadow:0 10px 30px rgba(0,0,0,.28); transition:transform .25s ease, box-shadow .25s ease;}
.card::before {content:""; position:absolute; left:0; top:0; bottom:0; width:5px; background:var(--accent,#c6ff3d); box-shadow:0 0 18px var(--accent,#c6ff3d);}
.card:hover {transform:translateY(-5px); box-shadow:0 18px 40px rgba(0,0,0,.4);}
.card-icon {font-size:1.7rem; margin-bottom:.25rem;}
.card-title {font-weight:700; font-size:1.05rem; color:#fff; margin-bottom:.35rem;}
.card-body {font-size:.9rem; color:#cdd8fb; line-height:1.55;}
.step-no {position:absolute; right:14px; top:8px; font-size:2.6rem; font-weight:800; color:rgba(255,255,255,.07);}
@keyframes rise {from{opacity:0; transform:translateY(16px)} to{opacity:1; transform:none}}

.kpi {display:flex; align-items:center; gap:1rem; padding:1.1rem 1.2rem; border-radius:20px; position:relative; overflow:hidden; animation:rise .6s ease both;
  background:linear-gradient(145deg, rgba(255,255,255,.11), rgba(255,255,255,.03)); border:1px solid rgba(255,255,255,.15);
  box-shadow:0 10px 30px rgba(0,0,0,.28); transition:transform .25s ease;}
.kpi:hover {transform:translateY(-5px) scale(1.01);}
.kpi::after {content:""; position:absolute; right:-30px; top:-30px; width:110px; height:110px; border-radius:50%; background:var(--accent); opacity:.16; filter:blur(6px);}
.kpi-icon {font-size:1.9rem; width:58px; height:58px; display:flex; align-items:center; justify-content:center; border-radius:16px;
  background:rgba(255,255,255,.09); border:1px solid var(--accent); box-shadow:0 0 18px -4px var(--accent);}
.kpi-label {font-size:.76rem; text-transform:uppercase; letter-spacing:.09em; color:#a9b8ee; font-weight:600;}
.kpi-value {font-size:1.85rem; font-weight:800; color:#fff; line-height:1.1;}
.kpi-sub {font-size:.78rem; color:var(--accent); font-weight:600;}

/* ---------- leaderboard ---------- */
.lb {padding:1.1rem 1.2rem; border-radius:20px; background:linear-gradient(145deg, rgba(255,255,255,.10), rgba(255,255,255,.035));
  border:1px solid rgba(255,255,255,.14); box-shadow:0 10px 30px rgba(0,0,0,.28); animation:rise .6s ease both;}
.lb-title {font-weight:800; font-size:1.05rem; margin-bottom:.7rem; color:#fff;}
.lb-row {display:grid; grid-template-columns:42px 1fr auto; gap:.7rem; align-items:center; padding:.5rem .35rem; border-radius:12px; transition:background .2s;}
.lb-row:hover {background:rgba(255,255,255,.07);}
.lb-pos {font-size:1.25rem; font-weight:800; text-align:center; color:#c6ff3d;}
.lb-name {font-weight:600; font-size:.92rem; color:#fff;} .lb-name span {display:block; font-size:.74rem; color:#a9b8ee; font-weight:400;}
.lb-val {font-weight:800; color:var(--accent); font-size:.98rem; text-align:right;}
.bar {grid-column:2 / 4; height:5px; border-radius:999px; background:rgba(255,255,255,.09); overflow:hidden; margin-top:-.15rem;}
.bar i {display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,var(--accent),#22d3ee);}

/* ---------- profile ---------- */
.profile {display:flex; gap:1.2rem; align-items:center; flex-wrap:wrap; padding:1.3rem 1.5rem; border-radius:24px; margin:.5rem 0 1rem;
  background:linear-gradient(120deg, rgba(198,255,61,.14), rgba(34,211,238,.12)); border:1px solid rgba(255,255,255,.18);
  box-shadow:0 14px 40px rgba(0,0,0,.35); animation:rise .6s ease both;}
.avatar {width:76px; height:76px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.7rem; color:#0b1230;
  background:linear-gradient(135deg,#c6ff3d,#22d3ee); box-shadow:0 8px 22px rgba(34,211,238,.4);}
.profile h3 {margin:0; font-size:1.5rem; color:#fff;} .profile p {margin:.1rem 0 0; color:#c4d0f7;}
.stats {display:flex; gap:.8rem; flex-wrap:wrap; margin-left:auto;}
.stat {min-width:105px; text-align:center; padding:.6rem .9rem; border-radius:16px; background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.15);}
.stat b {display:block; font-size:1.35rem; color:#fff;} .stat span {font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; color:#a9b8ee;}
.up {color:#4ade80 !important;} .down {color:#f87171 !important;} .flat {color:#cbd5e1 !important;}

/* ---------- thank-you ---------- */
.thanks {text-align:center; padding:2.2rem 1.5rem; border-radius:28px; margin:1rem 0;
  background:linear-gradient(120deg, rgba(198,255,61,.20), rgba(34,211,238,.16), rgba(244,114,182,.18));
  border:1px solid rgba(255,255,255,.2); box-shadow:0 18px 60px rgba(0,0,0,.4);}
.thanks h2 {font-size:2rem; margin:.2rem 0; color:#fff;} .thanks p {color:#d6defa; margin:.2rem 0 1rem;}
.footer {text-align:center; margin-top:2rem; padding-top:1rem; border-top:1px solid rgba(255,255,255,.12); color:#8ea0d8; font-size:.8rem;}
.footer .tech-row {justify-content:center; margin-bottom:.6rem;}

/* ---------- native widgets ---------- */
div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {border-radius:18px; border:1px solid rgba(255,255,255,.13);
  background:rgba(255,255,255,.04); padding:6px; box-shadow:0 10px 30px rgba(0,0,0,.25); overflow:hidden;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:18px;}
div[data-testid="stExpander"] {border-radius:16px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.13);}
.stButton > button, .stDownloadButton > button {border-radius:999px; border:0; padding:.55rem 1.5rem; font-weight:700;
  background:linear-gradient(135deg,#c6ff3d,#22d3ee); color:#0b1230; box-shadow:0 8px 24px rgba(34,211,238,.28); transition:all .2s ease;}
.stButton > button:hover, .stDownloadButton > button:hover {transform:translateY(-2px); color:#0b1230; box-shadow:0 12px 30px rgba(198,255,61,.35);}
.stButton > button p, .stDownloadButton > button p {color:#0b1230 !important; font-weight:700;}
button[data-baseweb="tab"] {font-weight:600;}
textarea {font-family:'Consolas','Courier New',monospace !important; font-size:.92rem !important;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS.replace("__COURT__", COURT_URI), unsafe_allow_html=True)


def html_block(markup: str) -> None:
    """Render raw HTML. Lines are joined so Markdown never treats indentation as a code block."""
    st.markdown(" ".join(line.strip() for line in markup.strip().splitlines()), unsafe_allow_html=True)


def section(title: str, sub: str = "") -> None:
    small = f"<small>{esc(sub)}</small>" if sub else ""
    html_block(f"<div class='section'><h2>{esc(title)}</h2>{small}</div>")


def card_html(icon: str, title: str, body: str, accent: str = "#c6ff3d", number: str = "") -> str:
    num = f"<div class='step-no'>{number}</div>" if number else ""
    return (f"<div class='card' style='--accent:{accent}'>{num}<div class='card-icon'>{icon}</div>"
            f"<div class='card-title'>{esc(title)}</div><div class='card-body'>{body}</div></div>")


def card_grid(cards: list, cols: int = 3) -> None:
    html_block(f"<div class='grid g{cols}'>{''.join(cards)}</div>")


def kpi_grid(items: list, cols: int = 3) -> None:
    """items: (icon, label, value, sub, accent)."""
    cells = "".join(
        f"<div class='kpi' style='--accent:{a}'><div class='kpi-icon'>{i}</div><div>"
        f"<div class='kpi-label'>{esc(l)}</div><div class='kpi-value'>{esc(v)}</div>"
        f"<div class='kpi-sub'>{esc(s)}</div></div></div>" for i, l, v, s, a in items)
    html_block(f"<div class='grid g{cols}'>{cells}</div>")


def leaderboard_html(df: pd.DataFrame, title: str, accent: str, primary: str) -> str:
    """Styled top-N list. primary = 'rank' or 'points' (what is shown on the right)."""
    top = max(float(df["points"].max()), 1.0) if not df.empty else 1.0
    rows = ""
    for pos, (_, r) in enumerate(df.iterrows(), start=1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, str(pos))
        value = f"#{int(r['rank'])}" if primary == "rank" else f"{int(r['points']):,}"
        small = f"{r['country']} · {int(r['points']):,} pts" if primary == "rank" else f"{r['country']} · rank #{int(r['rank'])}"
        width = max(4, int(100 * float(r["points"]) / top))
        rows += (f"<div class='lb-row'><div class='lb-pos'>{medal}</div>"
                 f"<div class='lb-name'>{esc(r['name'])}<span>{esc(small)}</span></div>"
                 f"<div class='lb-val'>{value}</div><div class='bar'><i style='width:{width}%'></i></div></div>")
    return f"<div class='lb' style='--accent:{accent}'><div class='lb-title'>{esc(title)}</div>{rows}</div>"


# ----------------------------------------------------- version-safe helpers
def _st_version() -> tuple:
    try:
        return tuple(int(p) for p in st.__version__.split(".")[:2])
    except Exception:  # noqa: BLE001
        return (1, 0)


NEW_WIDTH_API = _st_version() >= (1, 50)


def call_stretch(fn, *args, **kwargs):
    """Call a Streamlit element so it fills its container on both old and new versions."""
    attempts = ({"width": "stretch"}, {"use_container_width": True})
    if not NEW_WIDTH_API:
        attempts = attempts[::-1]
    for opts in attempts:
        try:
            return fn(*args, **kwargs, **opts)
        except (TypeError, st.errors.StreamlitAPIException):
            continue
    return fn(*args, **kwargs)


def style_fig(fig, height: int = 360, legend: bool = True):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins, Segoe UI, sans-serif", color="#dbe4ff"), height=height,
        margin=dict(l=20, r=20, t=55, b=20), colorway=PALETTE, showlegend=legend,
        title=dict(font=dict(size=16, color="#ffffff")),
        legend=dict(bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False)
    return fig


def show_plot(fig, height: int = 360, legend: bool = True) -> None:
    call_stretch(st.plotly_chart, style_fig(fig, height, legend))


def show_df(df: pd.DataFrame, height: int | None = None) -> None:
    kwargs = {"hide_index": True}
    if height:
        kwargs["height"] = height
    call_stretch(st.dataframe, df, **kwargs)


def panel():
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def goto(label: str) -> None:
    st.session_state["nav"] = label


# ----------------------------------------------------------------- database
@st.cache_resource
def get_engine():
    """Shared engine for the dashboard pages."""
    return create_engine(config.DB_URL, pool_pre_ping=True, pool_recycle=1800,
                         connect_args=config.DB_CONNECT_ARGS)


@st.cache_resource
def get_readonly_engine():
    """Separate engine for the SQL Playground: read-only MySQL session, no connection reuse."""
    args = dict(config.DB_CONNECT_ARGS)
    if str(config.DB_URL).startswith("mysql"):
        args["init_command"] = "SET SESSION TRANSACTION READ ONLY"
    return create_engine(config.DB_URL, poolclass=NullPool, connect_args=args)


@st.cache_data(ttl=300, show_spinner=False)
def _run(sql: str, params: dict) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run a query and return a DataFrame; show a friendly error instead of crashing."""
    try:
        return _run(sql, params or {})
    except SQLAlchemyError as exc:
        st.error(f"Database error: {exc}")
        return pd.DataFrame()


def scalar(sql: str, params: dict | None = None, default=0):
    df = run_query(sql, params)
    if df.empty or pd.isna(df.iloc[0, 0]):
        return default
    return df.iloc[0, 0]


def in_clause(column: str, values: list, params: dict, prefix: str) -> str:
    names = []
    for i, value in enumerate(values):
        params[f"{prefix}{i}"] = value
        names.append(f":{prefix}{i}")
    return f"{column} IN ({', '.join(names)})"


def latest_period():
    df = run_query("SELECT year, week FROM Competitor_Rankings ORDER BY year DESC, week DESC LIMIT 1")
    return None if df.empty else (int(df["year"][0]), int(df["week"][0]))


@st.cache_data(ttl=300, show_spinner=False)
def load_rankings(year: int, week: int) -> pd.DataFrame:
    sql = """
        SELECT r.`rank`, r.movement, r.points, r.competitions_played, r.ranking_name, r.gender,
               c.competitor_id, c.name, c.country, c.country_code
        FROM Competitor_Rankings r
        JOIN Competitors c ON c.competitor_id = r.competitor_id
        WHERE r.year = :y AND r.week = :w
    """
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params={"y": year, "w": week})


# -------------------------------------------------------- SQL playground core
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|rename|call|load|lock|unlock|handler|"
    r"outfile|dumpfile|sleep|benchmark)\b|\breplace\s+into\b", re.I)
ALLOWED_START = ("select", "with", "show", "describe", "desc", "explain")


def strip_comments(sql: str) -> str:
    """Remove SQL comments while leaving quoted text untouched. Rejects MySQL executable comments."""
    out, i, n = [], 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch in "'\"`":
            j = i + 1
            while j < n:
                if sql[j] == "\\" and ch != "`":
                    j += 2
                    continue
                if sql[j] == ch:
                    if j + 1 < n and sql[j + 1] == ch:
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i:j + 1])
            i = j + 1
        elif sql.startswith("/*", i):
            if sql.startswith("/*!", i):
                raise ValueError("Executable comments are not allowed.")
            end = sql.find("*/", i + 2)
            i = n if end == -1 else end + 2
            out.append(" ")
        elif sql.startswith("--", i) or ch == "#":
            end = sql.find("\n", i)
            i = n if end == -1 else end
            out.append(" ")
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def validate_sql(sql: str) -> str:
    """Return a single safe read-only statement or raise ValueError with a friendly message."""
    code = strip_comments(sql).strip()
    masked = re.sub(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.|\"\")*\"", "''", code)
    masked = re.sub(r"`[^`]*`", "x", masked).strip().rstrip(";").strip()
    if not masked:
        raise ValueError("Please type a query first.")
    if ";" in masked:
        raise ValueError("Only one statement can be run at a time (remove the extra semicolon).")
    if not masked.lower().startswith(ALLOWED_START):
        raise ValueError("Only read-only queries are allowed: start with SELECT, WITH, SHOW, DESCRIBE or EXPLAIN.")
    if FORBIDDEN.search(masked):
        raise ValueError("This playground is read-only: data-changing or unsafe keywords are blocked.")
    return code.rstrip().rstrip(";")


def escape_colons(sql: str) -> str:
    """Stop SQLAlchemy text() from treating ' :word' inside a query as a bind parameter."""
    return re.sub(r"(?<![\w:\\]):(?=\w)", r"\\:", sql)


def execute_playground(sql: str, max_rows: int):
    stmt = validate_sql(sql)
    engine = get_readonly_engine()
    started = time.perf_counter()
    with engine.connect() as conn:
        if engine.dialect.name == "mysql":
            conn.exec_driver_sql("SET SESSION max_execution_time = 15000")
        result = conn.execute(text(escape_colons(stmt)))
        columns = list(result.keys())
        rows = [tuple(r) for r in result.fetchmany(max_rows + 1)]
    seen, unique = {}, []
    for col in columns:
        seen[col] = seen.get(col, 0) + 1
        unique.append(col if seen[col] == 1 else f"{col}_{seen[col]}")
    df = pd.DataFrame(rows, columns=unique)
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(1).tolist()
            if sample and isinstance(sample[0], decimal.Decimal):
                df[col] = df[col].astype(float)
    return df.head(max_rows), len(df) > max_rows, time.perf_counter() - started


FEATURED = [
    ("★ Top 10 countries by total points",
     "SELECT c.country, SUM(r.points) AS total_points\nFROM Competitor_Rankings r\n"
     "JOIN Competitors c ON c.competitor_id = r.competitor_id\nGROUP BY c.country\nORDER BY total_points DESC\nLIMIT 10"),
    ("★ Competitions per category",
     "SELECT cat.category_name, COUNT(*) AS competitions\nFROM Competitions c\n"
     "JOIN Categories cat ON cat.category_id = c.category_id\nGROUP BY cat.category_name\nORDER BY competitions DESC"),
    ("★ Venues per country (top 15)",
     "SELECT country_name, COUNT(*) AS venues\nFROM Venues\nGROUP BY country_name\nORDER BY venues DESC\nLIMIT 15"),
    ("★ Rank movement groups",
     "SELECT CASE WHEN movement > 0 THEN 'Positive movement' WHEN movement < 0 THEN 'Negative movement'\n"
     "            ELSE 'No movement' END AS movement_group,\n       COUNT(*) AS competitors\n"
     "FROM Competitor_Rankings\nGROUP BY movement_group"),
    ("★ Average points by ranking list",
     "SELECT ranking_name, ROUND(AVG(points), 1) AS avg_points, MAX(points) AS max_points\n"
     "FROM Competitor_Rankings\nGROUP BY ranking_name"),
]
SCHEMA_REF = {
    "Categories": ["category_id", "category_name"],
    "Competitions": ["competition_id", "competition_name", "parent_id", "type", "gender", "level", "category_id"],
    "Complexes": ["complex_id", "complex_name"],
    "Venues": ["venue_id", "venue_name", "city_name", "country_name", "country_code", "timezone", "complex_id"],
    "Competitors": ["competitor_id", "name", "country", "country_code", "abbreviation"],
    "Competitor_Rankings": ["rank_id", "`rank`", "movement", "points", "competitions_played", "competitor_id",
                            "ranking_name", "year", "week", "gender"],
}


# ------------------------------------------------------------------- layout
def render_header() -> None:
    html_block(f"""
    <div class="topbar">
      <div class="brand"><img class="ball" src="{LOGO_URI}" alt="logo">
        <div><div class="brand-title">Tennis Rankings Explorer</div>
        <div class="brand-sub">Game Analytics · Sportradar Tennis API · MySQL · Streamlit</div></div></div>
      <div class="tech-row">{tech_badges()}</div>
    </div>""")
    if st.get_option("theme.base") != "dark":
        html_block("<div class='notice'>🎨 For the best look, copy the <b>.streamlit/config.toml</b> file from the "
                   "project folder next to your app and restart Streamlit.</div>")


def render_footer() -> None:
    html_block(f"""
    <div class="footer"><div class="tech-row">{tech_badges()}</div>
    Tennis Rankings Explorer · Data courtesy of Sportradar · Built by {esc(AUTHOR_NAME)}</div>""")


def pager(label: str) -> None:
    idx = PAGES.index(label)
    left, mid, right = st.columns([1.2, 3, 1.2])
    if idx > 0:
        left.button(f"← {PAGES[idx - 1]}", on_click=goto, args=(PAGES[idx - 1],), key=f"prev_{idx}")
    if idx < len(PAGES) - 1:
        right.button(f"{PAGES[idx + 1]} →", on_click=goto, args=(PAGES[idx + 1],), key=f"next_{idx}")


def need_data(rk: pd.DataFrame) -> bool:
    if rk.empty:
        card_grid([card_html("📭", "No ranking data yet",
                             "Run <b>python -m api.extract</b> and <b>python -m api.load</b>, then refresh this page.",
                             "#fb923c")], 1)
        return False
    return True


def movement_html(value: int) -> str:
    if value > 0:
        return f"<b class='up'>▲ +{value}</b>"
    if value < 0:
        return f"<b class='down'>▼ {value}</b>"
    return "<b class='flat'>● 0</b>"


# -------------------------------------------------------------------- pages
def page_intro(rk: pd.DataFrame) -> None:
    html_block(f"""
    <div class="hero"><div>
      <div class="eyebrow">GAME ANALYTICS · SPORTS DATA PROJECT</div>
      <div class="hero-title">Unlocking Tennis Data with the Sportradar API</div>
      <p class="hero-p">From raw nested JSON to a relational database and an interactive dashboard: explore
      competitions, venues and doubles rankings in one place.</p>
      <div class="chips"><span class="chip">🎾 Competitions</span><span class="chip">🏟️ Venues</span>
      <span class="chip">🏆 Rankings</span><span class="chip">🧪 SQL Playground</span></div></div>
      <img class="hero-ball" src="{LOGO_URI}" alt="tennis ball"></div>""")
    st.button("Start exploring →", on_click=goto, args=(PAGES[1],), key="cta_start")

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
        card_html("🧭", "Navigate", "Use the pill menu at the top. Every page has its own filters, and ← → buttons at the bottom move you along.", "#c6ff3d"),
        card_html("🔍", "Filter and search", "Players, Competitions and Venues pages let you search by name and narrow results with filters.", "#22d3ee"),
        card_html("🧪", "Experiment", "Open the SQL Playground to run your own read-only queries and turn results into charts.", "#a78bfa"),
    ])


def page_overview(rk: pd.DataFrame, period) -> None:
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
                         color_continuous_scale=SCALE, title="Top 10 countries by competitors"),
                  legend=False)
    with right:
        by_cat = run_query("""SELECT cat.category_name, COUNT(*) AS competitions
                              FROM Competitions c JOIN Categories cat ON cat.category_id = c.category_id
                              GROUP BY cat.category_name ORDER BY competitions DESC""")
        if not by_cat.empty:
            show_plot(px.pie(by_cat, names="category_name", values="competitions", hole=0.55,
                             title="Competitions per category"))

    left, right = st.columns(2)
    with left:
        show_plot(px.histogram(rk, x="points", color="ranking_name", nbins=40, barmode="overlay", opacity=0.75,
                               title="Distribution of ranking points"))
    with right:
        groups = rk["movement"].map(lambda m: "Positive" if m > 0 else ("Negative" if m < 0 else "Stable"))
        mv = groups.value_counts().reset_index()
        mv.columns = ["movement", "competitors"]
        show_plot(px.pie(mv, names="movement", values="competitors", hole=0.55, title="Weekly rank movement",
                         color="movement", color_discrete_map={"Positive": "#4ade80", "Negative": "#f87171", "Stable": "#94a3b8"}))

    section("Spotlight", "top 5 of each ranking list")
    lists = sorted(rk["ranking_name"].unique())[:2]
    cols = st.columns(len(lists))
    for col, name in zip(cols, lists):
        sub = rk[rk["ranking_name"] == name].sort_values(["rank", "points"], ascending=[True, False]).head(5)
        col.markdown(" ".join(leaderboard_html(sub, f"{name} top 5", "#c6ff3d", "rank").split()), unsafe_allow_html=True)


def page_players(rk: pd.DataFrame) -> None:
    section("Players", "search, filter and open a profile")
    if not need_data(rk):
        return
    with panel():
        c1, c2, c3 = st.columns([1, 1.4, 2])
        tour = c1.selectbox("Ranking list", ["All"] + sorted(rk["ranking_name"].unique()))
        name_q = c2.text_input("Search by name", placeholder="e.g. Heliovaara")
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


def page_countries(rk: pd.DataFrame) -> None:
    section("Country insights", "who dominates the rankings")
    if not need_data(rk):
        return
    agg = (rk.groupby("country")
           .agg(competitors=("competitor_id", "nunique"), total_points=("points", "sum"),
                average_points=("points", "mean"), country_code=("country_code", "first"))
           .round(1).reset_index().sort_values("competitors", ascending=False))
    medals = ["🥇", "🥈", "🥉"]
    accents = ["#facc15", "#cbd5e1", "#fb923c"]
    card_grid([card_html(medals[i], r["country"],
                         f"<b>{int(r['competitors']):,}</b> competitors · <b>{int(r['total_points']):,}</b> points "
                         f"· avg <b>{r['average_points']:,.0f}</b>", accents[i])
               for i, (_, r) in enumerate(agg.head(3).iterrows())])

    metric = st.selectbox("Rank countries by", ["competitors", "total_points", "average_points"],
                          format_func=lambda m: m.replace("_", " ").title())
    left, right = st.columns(2)
    with left:
        show_plot(px.bar(agg.nlargest(15, metric), x="country", y=metric, color=metric, color_continuous_scale=SCALE,
                         title=f"Top 15 countries by {metric.replace('_', ' ')}"), legend=False)
    with right:
        show_plot(px.scatter(agg, x="competitors", y="average_points", size="total_points", color="total_points",
                             hover_name="country", color_continuous_scale=SCALE,
                             title="Depth vs quality (bubble size = total points)"), legend=False)

    fig = px.choropleth(agg, locations="country_code", color="competitors", hover_name="country",
                        color_continuous_scale=SCALE, title="Where the ranked competitors come from")
    fig.update_geos(bgcolor="rgba(0,0,0,0)", showframe=False, showcountries=True, countrycolor="rgba(255,255,255,.18)",
                    landcolor="rgba(255,255,255,.05)", showocean=False, projection_type="natural earth")
    show_plot(fig, height=460, legend=False)

    show_plot(px.treemap(agg.nlargest(40, "total_points"), path=["country"], values="total_points",
                         color="average_points", color_continuous_scale=SCALE,
                         title="Share of total points (top 40 countries)"), height=420, legend=False)
    with st.expander("📋 Full country table"):
        show_df(agg[["country", "competitors", "total_points", "average_points"]], height=340)


def page_leaderboards(rk: pd.DataFrame) -> None:
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
    chart_df = by_points.assign(label=by_points["name"])
    show_plot(px.bar(chart_df, x="points", y="label", orientation="h", color="points", color_continuous_scale=SCALE,
                     title=f"Points of the top {top_n} · {tour}").update_yaxes(autorange="reversed"),
              height=max(320, 32 * top_n + 120), legend=False)


def page_competitions() -> None:
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
        search = st.text_input("Search competition name", placeholder="e.g. Vienna")

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
    with right:
        gender = run_query("SELECT gender, COUNT(*) AS competitions FROM Competitions GROUP BY gender")
        if not gender.empty:
            show_plot(px.pie(gender, names="gender", values="competitions", hole=0.55, title="Competitions by gender"))

    lv = run_query("SELECT level, COUNT(*) AS competitions FROM Competitions WHERE level IS NOT NULL "
                   "GROUP BY level ORDER BY competitions DESC")
    if not lv.empty:
        show_plot(px.bar(lv, x="level", y="competitions", color="competitions", color_continuous_scale=SCALE,
                         title="Competitions by level"), legend=False)

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


def page_venues() -> None:
    section("Venues and complexes", "where tennis is played")
    countries = run_query("SELECT DISTINCT country_name FROM Venues ORDER BY country_name")
    if countries.empty:
        need_data(pd.DataFrame())
        return
    with panel():
        c1, c2 = st.columns([2, 1])
        sel = c1.multiselect("Country", countries["country_name"].tolist())
        search = c2.text_input("Search venue or complex", placeholder="e.g. Nacional")
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
    if not per_country.empty:
        fig = px.choropleth(per_country, locations="country_code", color="venues", hover_name="country_name",
                            color_continuous_scale=SCALE, title="Venues around the world")
        fig.update_geos(bgcolor="rgba(0,0,0,0)", showframe=False, showcountries=True, countrycolor="rgba(255,255,255,.18)",
                        landcolor="rgba(255,255,255,.05)", showocean=False, projection_type="natural earth")
        show_plot(fig, height=460, legend=False)
        left, right = st.columns(2)
        with left:
            show_plot(px.bar(per_country.head(15), x="country_name", y="venues", color="venues",
                             color_continuous_scale=SCALE, title="Top 15 countries by venues"), legend=False)
        with right:
            multi = run_query("""SELECT cx.complex_name, COUNT(v.venue_id) AS venues
                                 FROM Complexes cx JOIN Venues v ON v.complex_id = cx.complex_id
                                 GROUP BY cx.complex_id, cx.complex_name HAVING COUNT(v.venue_id) > 1
                                 ORDER BY venues DESC, cx.complex_name LIMIT 12""")
            if multi.empty:
                card_grid([card_html("🏛️", "Single-venue complexes", "Every complex has exactly one venue.", "#22d3ee")], 1)
            else:
                show_plot(px.bar(multi, x="venues", y="complex_name", orientation="h", color="venues",
                                 color_continuous_scale=SCALE, title="Complexes with more than one venue")
                          .update_yaxes(autorange="reversed"), legend=False)


def playground_chart(df: pd.DataFrame) -> None:
    numeric = df.select_dtypes("number").columns.tolist()
    others = [c for c in df.columns if c not in numeric]
    if not numeric:
        card_grid([card_html("📉", "No numeric column to chart",
                             "Add a number to your query, for example <b>COUNT(*)</b>, <b>SUM(points)</b> or <b>AVG(points)</b>.",
                             "#fb923c")], 1)
        return
    cols = list(df.columns)
    x_default = others[0] if others else cols[0]
    c1, c2, c3, c4 = st.columns(4)
    kind = c1.selectbox("Chart type", ["Bar", "Horizontal bar", "Line", "Area", "Pie / donut", "Scatter", "Histogram", "Box"], key="pg_kind")
    x = c2.selectbox("X axis / labels", cols, index=cols.index(x_default), key="pg_x")
    y_choices = [c for c in numeric if c != x] or numeric
    y = c3.selectbox("Y axis / values", y_choices, key="pg_y")
    colour = c4.selectbox("Colour by", ["None"] + others, key="pg_c")
    colour = None if colour == "None" else colour
    plot_df = df.head(60)
    if len(df) > 60:
        st.caption("Charting the first 60 rows to keep it readable.")
    try:
        if kind == "Bar":
            fig = px.bar(plot_df, x=x, y=y, color=colour or y, color_continuous_scale=SCALE if not colour else None)
        elif kind == "Horizontal bar":
            fig = px.bar(plot_df, x=y, y=x, orientation="h", color=colour or y,
                         color_continuous_scale=SCALE if not colour else None).update_yaxes(autorange="reversed")
        elif kind == "Line":
            fig = px.line(plot_df, x=x, y=y, color=colour, markers=True)
        elif kind == "Area":
            fig = px.area(plot_df, x=x, y=y, color=colour)
        elif kind == "Pie / donut":
            fig = px.pie(plot_df, names=x, values=y, hole=0.5)
        elif kind == "Scatter":
            fig = px.scatter(plot_df, x=x, y=y, color=colour)
        elif kind == "Histogram":
            fig = px.histogram(df, x=y, color=colour, nbins=30)
        else:
            fig = px.box(df, x=colour, y=y) if colour else px.box(df, y=y)
        show_plot(fig, height=420, legend=kind in ("Pie / donut",) or bool(colour))
    except Exception as exc:  # noqa: BLE001
        st.warning(f"This column combination cannot be drawn as a {kind.lower()} chart ({exc}). Try another one.")


def page_playground() -> None:
    section("SQL Playground", "write read-only SQL, see the table, draw the chart")
    path = PROJECT_ROOT / "sql" / "queries.sql"
    presets = list(FEATURED)
    if path.exists():
        presets += [(f"{qid}  {title}", sql) for qid, title, sql in load_queries(path)]
    names = ["✏️ Write my own query"] + [p[0] for p in presets]
    lookup = dict(presets)
    default_sql = FEATURED[0][1]
    st.session_state.setdefault("pg_sql", default_sql)

    def load_preset() -> None:
        choice = st.session_state.get("pg_preset")
        if choice in lookup:
            st.session_state["pg_sql"] = lookup[choice]

    card_grid([
        card_html("🛡️", "Safe by design", "Only one read-only statement runs per click. Data-changing keywords are blocked and the session is read-only.", "#c6ff3d"),
        card_html("⚡", "Instant charts", "Run any SELECT, then pick a chart type and columns in the Chart tab.", "#22d3ee"),
        card_html("💡", "Tip", "Wrap the column <b>`rank`</b> in backticks, because RANK is a reserved word in MySQL 8.", "#a78bfa"),
    ])
    with panel():
        c1, c2 = st.columns([3, 1])
        c1.selectbox("Start from an example", names, key="pg_preset", on_change=load_preset)
        max_rows = c2.selectbox("Max rows", [100, 500, 1000, 5000], index=2)
        st.text_area("SQL query", key="pg_sql", height=210, label_visibility="collapsed")
        run = st.button("▶ Run query", key="pg_run")
    with st.expander("📚 Tables and columns"):
        card_grid([card_html("🗂️", table, "<br>".join(f"• {esc(c)}" for c in cols), PALETTE[i % len(PALETTE)])
                   for i, (table, cols) in enumerate(SCHEMA_REF.items())])

    if run:
        try:
            df, truncated, elapsed = execute_playground(st.session_state["pg_sql"], int(max_rows))
            st.session_state["pg_result"] = {"df": df, "truncated": truncated, "elapsed": elapsed, "error": None}
        except ValueError as exc:
            st.session_state["pg_result"] = {"error": str(exc)}
        except SQLAlchemyError as exc:
            st.session_state["pg_result"] = {"error": f"Database error: {getattr(exc, 'orig', exc)}"}

    result = st.session_state.get("pg_result")
    if not result:
        card_grid([card_html("👆", "Ready when you are", "Pick an example or write a query, then press <b>Run query</b>.", "#22d3ee")], 1)
        return
    if result.get("error"):
        card_grid([card_html("⚠️", "Query could not run", esc(result["error"]), "#f87171")], 1)
        return
    df = result["df"]
    kpi_grid([
        ("📄", "Rows returned", f"{len(df):,}", "capped at the max rows setting" if result["truncated"] else "complete result", "#c6ff3d"),
        ("🧱", "Columns", f"{len(df.columns):,}", ", ".join(map(str, df.columns[:4])), "#22d3ee"),
        ("⏱️", "Run time", f"{result['elapsed'] * 1000:,.0f} ms", "round trip to MySQL", "#a78bfa"),
    ])
    if df.empty:
        card_grid([card_html("🫥", "No rows returned", "The query ran but nothing matched. Check your WHERE conditions.", "#fb923c")], 1)
        return
    tab_table, tab_chart = st.tabs(["📋 Result table", "📊 Chart"])
    with tab_table:
        show_df(df, height=380)
        st.download_button("⬇ Download CSV", df.to_csv(index=False), "playground_result.csv", "text/csv")
    with tab_chart:
        playground_chart(df)


def compute_insights(rk: pd.DataFrame) -> list:
    items = []
    if not rk.empty:
        by_c = rk.groupby("country")["competitor_id"].nunique().sort_values(ascending=False)
        share = 100 * by_c.iloc[0] / rk["competitor_id"].nunique()
        items.append(("🌍", "Most represented country", f"{by_c.index[0]} has {int(by_c.iloc[0]):,} ranked competitors, {share:.1f}% of the field.", "#22d3ee"))
        best = rk.loc[rk["points"].idxmax()]
        items.append(("⭐", "Points leader", f"{best['name']} ({best['country']}) tops the table with {int(best['points']):,} points.", "#facc15"))
        pts = rk.groupby("country")["points"].sum().sort_values(ascending=False)
        items.append(("💎", "Points powerhouse", f"{pts.index[0]} collects the most ranking points in total: {int(pts.iloc[0]):,}.", "#c6ff3d"))
        stable = 100 * (rk["movement"] == 0).mean()
        items.append(("⚖️", "Rankings are sticky", f"{stable:.0f}% of competitors kept the same rank as the previous week.", "#a78bfa"))
        mover = rk.loc[rk["movement"].abs().idxmax()]
        items.append(("🚀", "Biggest weekly mover", f"{mover['name']} moved {int(mover['movement']):+d} places in one week.", "#f472b6"))
        top10 = rk.nsmallest(10, "rank")["competitions_played"].mean()
        items.append(("🎽", "Top players play more", f"The top 10 have played {top10:.1f} competitions on average versus {rk['competitions_played'].mean():.1f} for everyone.", "#fb923c"))
    cats = run_query("""SELECT cat.category_name, COUNT(*) AS n FROM Competitions c
                        JOIN Categories cat ON cat.category_id = c.category_id
                        GROUP BY cat.category_name ORDER BY n DESC LIMIT 1""")
    total_c = int(scalar("SELECT COUNT(*) FROM Competitions"))
    if not cats.empty and total_c:
        n = int(cats.iloc[0]["n"])
        items.append(("🎾", "Biggest category", f"{cats.iloc[0]['category_name']} holds {n:,} of {total_c:,} competitions ({100 * n / total_c:.0f}%).", "#2dd4bf"))
    types = run_query("SELECT type, COUNT(*) AS n FROM Competitions GROUP BY type ORDER BY n DESC LIMIT 1")
    if not types.empty and total_c:
        items.append(("🧩", "Dominant event type", f"{types.iloc[0]['type'].title()} events make up {100 * int(types.iloc[0]['n']) / total_c:.0f}% of all competitions.", "#60a5fa"))
    v = run_query("SELECT country_name, COUNT(*) AS n FROM Venues GROUP BY country_name ORDER BY n DESC LIMIT 1")
    if not v.empty:
        items.append(("🏟️", "Venue hotspot", f"{v.iloc[0]['country_name']} hosts the most venues in the data: {int(v.iloc[0]['n']):,}.", "#c6ff3d"))
    return items


def page_insights(rk: pd.DataFrame) -> None:
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
        card_html("📸", "Snapshot data", f"Only the latest ranking week is loaded ({rows:,} ranking rows), so long-term trends are not visible yet.", "#fb923c"),
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
    <p>Game, set and match. I hope this dashboard made tennis data easier to explore.<br>Built by <b>{esc(AUTHOR_NAME)}</b></p>
    <div class="tech-row" style="justify-content:center">{tech_badges()}</div></div>""")


# --------------------------------------------------------------------- main
def main() -> None:
    inject_css()
    render_header()
    st.session_state.setdefault("nav", PAGES[0])
    label = st.radio("Navigation", PAGES, key="nav", horizontal=True, label_visibility="collapsed")

    period = latest_period()
    rk = load_rankings(*period) if period else pd.DataFrame()

    try:
        if label == PAGES[0]:
            page_intro(rk)
        elif label == PAGES[1]:
            page_overview(rk, period)
        elif label == PAGES[2]:
            page_players(rk)
        elif label == PAGES[3]:
            page_countries(rk)
        elif label == PAGES[4]:
            page_leaderboards(rk)
        elif label == PAGES[5]:
            page_competitions()
        elif label == PAGES[6]:
            page_venues()
        elif label == PAGES[7]:
            page_playground()
        else:
            page_insights(rk)
    except Exception as exc:  # noqa: BLE001  keep the app alive and explain the problem
        card_grid([card_html("🛠️", "Something went wrong on this page", esc(exc), "#f87171")], 1)

    pager(label)
    render_footer()


main()
