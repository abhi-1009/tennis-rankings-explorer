"""Safety checks for the SQL Playground. Pure Python (no Streamlit), so it is easy to unit-test."""
import re

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|rename|call|load|lock|unlock|handler|"
    r"outfile|dumpfile|sleep|benchmark)\b|\breplace\s+into\b", re.I)
ALLOWED_START = ("select", "with", "show", "describe", "desc", "explain")


def strip_comments(sql: str) -> str:
    """Remove SQL comments while leaving quoted text untouched.

    Raises ValueError for MySQL executable comments (/*! ... */), which could hide a command.
    """
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
    """Return one safe, read-only statement, or raise ValueError with a friendly message."""
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
