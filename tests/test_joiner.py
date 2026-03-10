from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from logjoiner.errors import SqlExecutionError
from logjoiner.joiner import (
    enforce_timestamp_sort,
    export_final_csv,
    run_final_join_sqls,
)


def test_run_final_join_sql(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    all_logs = tmp_path / "temp_all_logs.csv"
    errors = tmp_path / "temp_errors.csv"
    all_logs.write_text(
        "@timestamp,traceId,userId,level,@message\n"
        "2026-03-10T00:00:02Z,t2,u2,ERROR,msg2\n"
        "2026-03-10T00:00:01Z,t1,u1,INFO,msg1\n",
        encoding="utf-8",
    )
    errors.write_text("traceId,count_star()\nt2,1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    df = run_final_join_sqls(
        ["""
SELECT a.*
FROM 'temp_all_logs.csv' a
JOIN 'temp_errors.csv' e ON a.traceId = e.traceId
"""]
    )
    assert len(df) == 1
    assert df.iloc[0]["traceId"] == "t2"


def test_run_final_join_sql_with_source_tables(tmp_path: Path) -> None:
    all_logs = tmp_path / "all_logs.csv"
    errors = tmp_path / "errors.csv"
    all_logs.write_text(
        "@timestamp,traceId,userId,level,@message\n"
        "2026-03-10T00:00:02Z,t2,u2,ERROR,msg2\n"
        "2026-03-10T00:00:01Z,t1,u1,INFO,msg1\n",
        encoding="utf-8",
    )
    errors.write_text("traceId,count_star()\nt2,1\n", encoding="utf-8")

    df = run_final_join_sqls(
        [
            """
SELECT a.*
FROM all_logs a
JOIN errors e ON a.traceId = e.traceId
"""
        ],
        source_tables={
            "all_logs": str(all_logs),
            "errors": str(errors),
        },
    )
    assert len(df) == 1
    assert df.iloc[0]["traceId"] == "t2"


def test_enforce_timestamp_sort_missing_column() -> None:
    with pytest.raises(SqlExecutionError) as exc_info:
        enforce_timestamp_sort(pd.DataFrame([{"traceId": "t1"}]))
    assert "[LJ201]" in str(exc_info.value)


def test_enforce_timestamp_sort() -> None:
    df = pd.DataFrame(
        [
            {"@timestamp": "2026-03-10T00:00:02Z", "traceId": "t2"},
            {"@timestamp": "2026-03-10T00:00:01Z", "traceId": "t1"},
        ]
    )
    sorted_df = enforce_timestamp_sort(df)
    assert sorted_df.iloc[0]["traceId"] == "t1"


def test_run_final_join_sqls_with_input_placeholder() -> None:
    df = run_final_join_sqls(
        [
            "select 1 as a union all select 2 as a",
            "select * from __input__ where a = 2",
        ]
    )
    assert len(df) == 1
    assert int(df.iloc[0]["a"]) == 2


def test_export_final_csv_utf8_bom(tmp_path: Path) -> None:
    df = pd.DataFrame([{"@timestamp": "2026-03-10T00:00:01Z", "traceId": "t1"}])
    out = export_final_csv(df, str(tmp_path / "result.csv"))
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
