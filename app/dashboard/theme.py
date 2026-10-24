"""Look and feel: CSS, logos, header and footer."""
import base64

import streamlit as st

from dashboard import settings
from dashboard.components import esc, html_block

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


def tech_badges(with_sportradar: bool = True) -> str:
    """HTML for the technology pills shown in the header, footer and thank-you card."""
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

/* ---------- takeaway strip under charts ---------- */
.takeaway {display:flex; gap:.6rem; align-items:flex-start; margin:.2rem 0 1.1rem; padding:.7rem 1rem; border-radius:14px;
  background:rgba(198,255,61,.07); border:1px solid rgba(198,255,61,.25); border-left:4px solid #c6ff3d;
  color:#dbe4ff; font-size:.88rem; line-height:1.5;}
.takeaway b {color:#c6ff3d;}
.effect {display:block; margin-top:.35rem; color:#c6ff3d; font-weight:600;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS.replace("__COURT__", COURT_URI), unsafe_allow_html=True)


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
    Tennis Rankings Explorer · Data courtesy of Sportradar · Built by {esc(settings.AUTHOR_NAME)}</div>""")
