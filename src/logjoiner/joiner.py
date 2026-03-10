from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from logjoiner.errors import FileIOError, SqlExecutionError


def _escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def run_final_join_sqls(
    final_join_sqls: list[str],
    source_tables: dict[str, str] | None = None,
) -> pd.DataFrame:
    try:
        with duckdb.connect(database=":memory:") as conn:
            if source_tables:
                for table_name, csv_path in source_tables.items():
                    escaped_path = _escape_sql_string(csv_path)
                    conn.execute(
                        f'CREATE OR REPLACE VIEW "{table_name}" AS '
                        f"SELECT * FROM read_csv_auto('{escaped_path}', header=true)"
                    )
            last_df: pd.DataFrame | None = None
            for idx, sql in enumerate(final_join_sqls, start=1):
                try:
                    if last_df is not None:
                        conn.register("__prev__", last_df)
                    effective_sql = sql.replace("__input__", "__prev__")
                    last_df = conn.execute(effective_sql).fetchdf()
                except duckdb.Error as exc:
                    raise SqlExecutionError(detail=f"final_join_sqls[{idx}] 실행 실패: {exc}") from exc
            if last_df is None:
                raise SqlExecutionError(detail="실행할 final_join_sql이 없습니다.")
            return last_df
    except duckdb.Error as exc:
        raise SqlExecutionError(detail=f"final_join_sql 실행 실패: {exc}") from exc


def enforce_timestamp_sort(df: pd.DataFrame) -> pd.DataFrame:
    if "@timestamp" not in df.columns:
        raise SqlExecutionError(detail="최종 결과에 '@timestamp' 컬럼이 없습니다.")
    parsed = pd.to_datetime(df["@timestamp"], errors="coerce")
    if parsed.isna().any():
        raise SqlExecutionError(detail="'@timestamp' 컬럼에 파싱 불가능한 값이 있습니다.")
    out = df.copy()
    out = out.assign(_sort_ts=parsed).sort_values(by="_sort_ts", ascending=True).reset_index(drop=True)
    return out.drop(columns=["_sort_ts"])


def export_final_csv(df: pd.DataFrame, output_file: str) -> Path:
    output_path = Path(output_file).resolve()
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    except OSError as exc:
        raise FileIOError(detail=f"최종 CSV 저장 실패: {output_path}") from exc
    return output_path
