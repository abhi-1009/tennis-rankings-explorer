"""Small UI helpers: they must escape text, avoid division by zero and describe movement correctly."""
import pandas as pd

from dashboard import components


def test_pct_is_safe_when_the_total_is_zero():
    assert components.pct(5, 0) == 0.0
    assert components.pct(1, 4) == 25.0


def test_text_is_html_escaped():
    assert components.esc("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert "&lt;b&gt;" in components.card_html("x", "<b>", "body")


def test_movement_arrows():
    assert "▲" in components.movement_html(3) and "up" in components.movement_html(3)
    assert "▼" in components.movement_html(-2) and "down" in components.movement_html(-2)
    assert "●" in components.movement_html(0)


def test_leaderboard_escapes_names_and_orders_rows():
    df = pd.DataFrame({"name": ["<i>Evil</i>", "Good"], "country": ["A", "B"], "rank": [1, 2], "points": [100, 50]})
    html = components.leaderboard_html(df, "Title", "#fff", "rank")
    assert "&lt;i&gt;Evil" in html and "<i>Evil" not in html
    assert html.index("Evil") < html.index("Good")
    assert "🥇" in html and "🥈" in html


def test_leaderboard_handles_an_empty_table():
    empty = pd.DataFrame(columns=["name", "country", "rank", "points"])
    assert "lb-title" in components.leaderboard_html(empty, "Nobody", "#fff", "points")
