from csvs_to_sqlite import utils
import pytest
import sqlite3
import pandas as pd
import os
import tempfile

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


def test_load_csv_returns_encoding_utf8(tmp_path):
    csv_file = tmp_path / "utf8.csv"
    csv_file.write_text("name,value\nalice,1\nbob,2\n", encoding="utf-8")
    df, encoding = utils.load_csv(str(csv_file), ",", False, 0, None)
    assert encoding == "utf-8"
    assert len(df) == 2
    assert list(df.columns) == ["name", "value"]


def test_load_csv_returns_encoding_latin1(tmp_path):
    csv_file = tmp_path / "latin1.csv"
    csv_file.write_bytes(
        "name,city\nalice,M\xfcnchen\nbob,Z\xfcrich\n".encode("latin-1")
    )
    df, encoding = utils.load_csv(str(csv_file), ",", False, 0, None)
    assert encoding == "latin-1"
    assert list(df["city"]) == ["München", "Zürich"]


def test_load_csv_custom_encoding_order(tmp_path):
    csv_file = tmp_path / "cp1252.csv"
    csv_file.write_bytes(
        b"name,symbol\nalice,\x93smart\x94\n"
    )
    df, encoding = utils.load_csv(
        str(csv_file), ",", False, 0, None,
        encodings_to_try=("cp1252", "utf-8"),
    )
    assert encoding == "cp1252"
    assert "“" in df["symbol"].iloc[0]


def test_load_csv_all_encodings_fail(tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_bytes(b"name\n\x80\x81\x82\xff\xfe")
    with pytest.raises(utils.LoadCsvError, match="Could not decode"):
        utils.load_csv(
            str(csv_file), ",", False, 0, None,
            encodings_to_try=("ascii",),
        )
