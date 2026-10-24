"""Calculations behind the key-result and insight cards (no layout code)."""
import pandas as pd

from dashboard.components import pct
from dashboard.database import run_query, scalar


def top_category():
    """(name, count, total) of the biggest competition category, or None."""
    df = run_query("""SELECT cat.category_name, COUNT(*) AS n FROM Competitions c
                      JOIN Categories cat ON cat.category_id = c.category_id
                      GROUP BY cat.category_name ORDER BY n DESC LIMIT 1""")
    total = int(scalar("SELECT COUNT(*) FROM Competitions"))
    if df.empty or not total:
        return None
    return str(df.iloc[0]["category_name"]), int(df.iloc[0]["n"]), total


def top_venue_country():
    """(country, venues, total venues) for the country with most venues, or None."""
    df = run_query("SELECT country_name, COUNT(*) AS n FROM Venues GROUP BY country_name ORDER BY n DESC LIMIT 1")
    total = int(scalar("SELECT COUNT(*) FROM Venues"))
    if df.empty or not total:
        return None
    return str(df.iloc[0]["country_name"]), int(df.iloc[0]["n"]), total


def key_result(rk: pd.DataFrame) -> list:
    """Three plain-English sentences that answer the business question with numbers."""
    lines = []
    if not rk.empty:
        by_c = rk.groupby("country")["competitor_id"].nunique().sort_values(ascending=False)
        field = rk["competitor_id"].nunique()
        lines.append(f"{by_c.index[0]} has the most ranked doubles players: {int(by_c.iloc[0]):,} "
                     f"({pct(by_c.iloc[0], field):.0f}% of {field:,}).")
    venue = top_venue_country()
    if venue:
        lines.append(f"{venue[0]} hosts the most venues: {venue[1]:,} of {venue[2]:,} ({pct(venue[1], venue[2]):.0f}%).")
    cat = top_category()
    if cat:
        lines.append(f"{cat[0]} is the largest competition category: {cat[1]:,} of {cat[2]:,} ({pct(cat[1], cat[2]):.0f}%).")
    return lines or ["Load the data to see the key result."]


def compute_insights(rk: pd.DataFrame) -> list:
    """List of (icon, title, text, accent) insight cards calculated live from the data."""
    items = []
    if not rk.empty:
        by_c = rk.groupby("country")["competitor_id"].nunique().sort_values(ascending=False)
        share = pct(by_c.iloc[0], rk["competitor_id"].nunique())
        items.append(("🌍", "Most represented country", f"{by_c.index[0]} has {int(by_c.iloc[0]):,} ranked competitors, {share:.1f}% of the field.", "#22d3ee"))
        best = rk.loc[rk["points"].idxmax()]
        items.append(("⭐", "Points leader", f"{best['name']} ({best['country']}) tops the table with {int(best['points']):,} points.", "#facc15"))
        pts = rk.groupby("country")["points"].sum().sort_values(ascending=False)
        items.append(("💎", "Points powerhouse", f"{pts.index[0]} collects the most ranking points in total: {int(pts.iloc[0]):,}.", "#c6ff3d"))
        stable = pct((rk["movement"] == 0).sum(), len(rk))
        items.append(("⚖️", "Rankings are sticky", f"{stable:.0f}% of competitors kept the same rank as the previous week.", "#a78bfa"))
        mover = rk.loc[rk["movement"].abs().idxmax()]
        items.append(("🚀", "Biggest weekly mover", f"{mover['name']} moved {int(mover['movement']):+d} places in one week.", "#f472b6"))
        top10 = rk.nsmallest(10, "rank")["competitions_played"].mean()
        items.append(("🎽", "Top players play more", f"The top 10 have played {top10:.1f} competitions on average versus {rk['competitions_played'].mean():.1f} for everyone.", "#fb923c"))
    cat = top_category()
    if cat:
        items.append(("🎾", "Biggest category", f"{cat[0]} holds {cat[1]:,} of {cat[2]:,} competitions ({pct(cat[1], cat[2]):.0f}%).", "#2dd4bf"))
    types = run_query("SELECT type, COUNT(*) AS n FROM Competitions GROUP BY type ORDER BY n DESC LIMIT 1")
    if not types.empty and cat:
        items.append(("🧩", "Dominant event type", f"{types.iloc[0]['type'].title()} events make up {pct(int(types.iloc[0]['n']), cat[2]):.0f}% of all competitions.", "#60a5fa"))
    venue = top_venue_country()
    if venue:
        items.append(("🏟️", "Venue hotspot", f"{venue[0]} hosts the most venues in the data: {venue[1]:,}.", "#c6ff3d"))
    return items
