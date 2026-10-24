"""The SQL Playground must accept read-only queries and refuse anything that could change data."""
import pytest

from dashboard.sqlguard import escape_colons, strip_comments, validate_sql

ALLOWED = [
    "SELECT 1",
    "select * from Venues where venue_name like '%a%';",
    "WITH t AS (SELECT 1 AS a) SELECT * FROM t",
    "SHOW TABLES",
    "DESCRIBE Venues",
    "EXPLAIN SELECT * FROM Venues",
    "SELECT 'drop table x' AS note",                    # dangerous words inside a string are harmless
    "-- a comment first\nSELECT 1",
    "SELECT `rank` FROM Competitor_Rankings",
    "SELECT 'a;b' AS semicolon_in_text",
]
BLOCKED = [
    "DROP TABLE Venues",
    "SELECT 1; DROP TABLE Venues",
    "DELETE FROM Venues",
    "UPDATE Venues SET venue_name = 'x'",
    "INSERT INTO Categories VALUES (1, 2)",
    "TRUNCATE Venues",
    "ALTER TABLE Venues ADD COLUMN x INT",
    "CREATE TABLE t (a INT)",
    "GRANT ALL ON *.* TO 'x'@'%'",
    "SELECT 1 /*! DROP TABLE x */",                    # MySQL executable comment
    "SELECT * INTO OUTFILE '/tmp/x' FROM Venues",
    "SELECT SLEEP(10)",
    "SET @a = 1",
    "CALL some_procedure()",
    "",
    "   ;  ",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_read_only_queries_are_accepted(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize("sql", BLOCKED)
def test_unsafe_queries_are_rejected(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)


def test_trailing_semicolon_is_removed():
    assert not validate_sql("SELECT 1;").endswith(";")


def test_comments_are_removed_but_quoted_text_is_kept():
    assert "--" in strip_comments("SELECT '--not a comment' -- real comment")
    assert "real comment" not in strip_comments("SELECT 1 -- real comment")
    assert "hidden" not in strip_comments("SELECT /* hidden */ 1")


def test_colons_inside_text_do_not_become_bind_parameters():
    assert escape_colons("SELECT 'sr:competition:6'") == "SELECT 'sr:competition:6'"
    assert escape_colons("SELECT ' :param'") == "SELECT ' \\:param'"
