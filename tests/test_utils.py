from csvs_to_sqlite import utils
import pytest
import sqlite3
import os
import pandas as pd

TEST_TABLES = """
CREATE TABLE foo (
  id integer primary key,
  value text
);
"""


@pytest.mark.parametrize("table,expected", [("foo", True), ("bar", False)])
def test_table_exists(table, expected):
    conn = sqlite3.connect(":memory:")
    conn.executescript(TEST_TABLES)
    assert expected == utils.table_exists(conn, table)


def test_get_create_table_sql():
    df = pd.DataFrame([{"number": 1, "letter": "a"}])
    sql, columns = utils.get_create_table_sql("hello", df)
    assert (
        'CREATE TABLE "hello" (\n'
        '"index" INTEGER,\n'
        '  "number" INTEGER,\n'
        '  "letter" TEXT\n'
        ")"
    ) == sql
    assert {"index", "letter", "number"} == set(columns)


def test_refactor_dataframes():
    df = pd.DataFrame(
        [
            {"name": "Terry", "score": 0.5},
            {"name": "Terry", "score": 0.8},
            {"name": "Owen", "score": 0.7},
        ]
    )
    conn = sqlite3.connect(":memory:")
    output = utils.refactor_dataframes(
        conn, [df], {"name": ("People", "first_name")}, False
    )
    assert 1 == len(output)
    dataframe = output[0]
    # There should be a 'People' table in sqlite
    assert [(1, "Terry"), (2, "Owen")] == conn.execute(
        "select id, first_name from People"
    ).fetchall()
    assert (
        "   name  score\n" "0     1    0.5\n" "1     1    0.8\n" "2     2    0.7"
    ) == str(dataframe)


@pytest.fixture
def csv_dir(tmp_path):
    (tmp_path / "daily_sales.csv").write_text("a,b\n1,2\n")
    (tmp_path / "daily_returns.csv").write_text("a,b\n3,4\n")
    (tmp_path / "archive_2023.csv").write_text("a,b\n5,6\n")
    sub = tmp_path / "reports"
    sub.mkdir()
    (sub / "summary.csv").write_text("a,b\n7,8\n")
    return tmp_path


def test_csvs_from_paths_include(csv_dir):
    result = utils.csvs_from_paths(
        [str(csv_dir)], include_patterns=["daily_*.csv"]
    )
    names = set(result.keys())
    assert names == {"./daily_sales", "./daily_returns"}


def test_csvs_from_paths_exclude(csv_dir):
    result = utils.csvs_from_paths(
        [str(csv_dir)], exclude_patterns=["archive_*.csv"]
    )
    names = set(result.keys())
    assert "./archive_2023" not in names
    assert "./daily_sales" in names
    assert "./daily_returns" in names
    assert "reports/summary" in names


def test_csvs_from_paths_include_and_exclude(csv_dir):
    result = utils.csvs_from_paths(
        [str(csv_dir)],
        include_patterns=["daily_*.csv"],
        exclude_patterns=["*returns*"],
    )
    names = set(result.keys())
    assert names == {"./daily_sales"}


def test_csvs_from_paths_include_subdir(csv_dir):
    result = utils.csvs_from_paths(
        [str(csv_dir)], include_patterns=["reports/*.csv"]
    )
    names = set(result.keys())
    assert names == {"reports/summary"}


def test_csvs_from_paths_no_patterns(csv_dir):
    result = utils.csvs_from_paths([str(csv_dir)])
    assert len(result) == 4


def test_csvs_from_paths_single_file_ignores_patterns(csv_dir):
    single = str(csv_dir / "archive_2023.csv")
    result = utils.csvs_from_paths(
        [single], include_patterns=["daily_*.csv"], exclude_patterns=["archive*"]
    )
    assert "archive_2023" in result
