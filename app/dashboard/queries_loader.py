"""Parse sql/queries.sql into (id, title, sql) tuples for the SQL Playground."""
import re
from pathlib import Path

HEADING = re.compile(r"^--\s*(\d+\.\d+)\s+(.*\S)\s*$")


def load_queries(path: Path) -> list[tuple[str, str, str]]:
    """Return a list of (query_id, title, sql_text) from the queries file.

    A query starts at a comment like '-- 1.1 List all competitions ...'
    and ends at the next such heading. Comment lines and USE statements are dropped.
    """
    queries, current = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING.match(line.strip())
        if match:
            if current:
                queries.append(current)
            current = [match.group(1), match.group(2), []]
        elif current and line.strip() and not line.lstrip().startswith("--"):
            if not line.strip().upper().startswith("USE "):
                current[2].append(line)
    if current:
        queries.append(current)
    return [(qid, title, "\n".join(lines).strip().rstrip(";")) for qid, title, lines in queries]
