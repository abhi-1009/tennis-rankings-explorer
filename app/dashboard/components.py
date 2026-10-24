"""Small HTML building blocks (cards, KPI tiles, leaderboards, takeaways) and navigation helpers."""
import html

import pandas as pd
import streamlit as st

from dashboard import settings


def esc(value) -> str:
    """HTML-escape any value."""
    return html.escape(str(value))


def pct(part, whole) -> float:
    """Percentage of part in whole, safe against division by zero."""
    return 100.0 * part / whole if whole else 0.0


def html_block(markup: str) -> None:
    """Render raw HTML. Lines are joined so Markdown never treats indentation as a code block."""
    st.markdown(" ".join(line.strip() for line in markup.strip().splitlines()), unsafe_allow_html=True)


def section(title: str, sub: str = "") -> None:
    small = f"<small>{esc(sub)}</small>" if sub else ""
    html_block(f"<div class='section'><h2>{esc(title)}</h2>{small}</div>")


def takeaway(message: str) -> None:
    """One-line 'so what' shown under a chart."""
    html_block(f"<div class='takeaway'><span>💡</span><div><b>Takeaway:</b> {esc(message)}</div></div>")


def card_html(icon: str, title: str, body: str, accent: str = "#c6ff3d", number: str = "") -> str:
    """Return the HTML of one glass card. `body` may contain trusted HTML."""
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
        small = (f"{r['country']} · {int(r['points']):,} pts" if primary == "rank"
                 else f"{r['country']} · rank #{int(r['rank'])}")
        width = max(4, int(100 * float(r["points"]) / top))
        rows += (f"<div class='lb-row'><div class='lb-pos'>{medal}</div>"
                 f"<div class='lb-name'>{esc(r['name'])}<span>{esc(small)}</span></div>"
                 f"<div class='lb-val'>{value}</div><div class='bar'><i style='width:{width}%'></i></div></div>")
    return f"<div class='lb' style='--accent:{accent}'><div class='lb-title'>{esc(title)}</div>{rows}</div>"


def movement_html(value: int) -> str:
    if value > 0:
        return f"<b class='up'>▲ +{value}</b>"
    if value < 0:
        return f"<b class='down'>▼ {value}</b>"
    return "<b class='flat'>● 0</b>"


def need_data(rk: pd.DataFrame) -> bool:
    """Show a friendly card and return False when there is no ranking data."""
    if rk.empty:
        card_grid([card_html("📭", "No ranking data yet",
                             "Run <b>python -m api.extract</b> and <b>python -m api.load</b>, then refresh this page.",
                             "#fb923c")], 1)
        return False
    return True


def goto(label: str) -> None:
    st.session_state["nav"] = label


def pager(label: str) -> None:
    """Previous / next buttons at the bottom of every page."""
    pages = settings.PAGES
    idx = pages.index(label)
    left, _, right = st.columns([1.2, 3, 1.2])
    if idx > 0:
        left.button(f"← {pages[idx - 1]}", on_click=goto, args=(pages[idx - 1],), key=f"prev_{idx}")
    if idx < len(pages) - 1:
        right.button(f"{pages[idx + 1]} →", on_click=goto, args=(pages[idx + 1],), key=f"next_{idx}")
