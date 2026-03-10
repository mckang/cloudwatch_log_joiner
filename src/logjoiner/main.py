from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from logjoiner.aws_logs import CloudWatchLogsClient
from logjoiner.cli import build_parser
from logjoiner.config import load_config, render_step_query
from logjoiner.env import load_aws_env
from logjoiner.errors import InputValidationError, LogJoinerError
from logjoiner.joiner import (
    export_final_csv,
    run_final_join_sqls,
)
from logjoiner.stage import StageWriter
from logjoiner.time_utils import parse_kst_datetime, to_utc_epoch_ms


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOGGER = logging.getLogger("logjoiner")


def _configure_logging(log_level: str) -> None:
    level = logging.DEBUG if log_level == "DEBUG" else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)


def _resolve_output_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "output":
        return path
    return Path("output") / path


def _rewrite_final_join_sql(final_join_sql: str, save_as_pairs: list[tuple[str, str]]) -> str:
    sql = final_join_sql
    for original, resolved in save_as_pairs:
        sql = sql.replace(f"'{original}'", f"'{resolved}'")
        sql = sql.replace(f'"{original}"', f'"{resolved}"')
    return sql


def _resolve_named_output_path(name: str) -> Path:
    path = _resolve_output_path(name)
    if path.suffix.lower() != ".csv":
        return path.with_suffix(".csv")
    return path


def _clear_output_directory(output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        for child in output_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    except OSError as exc:
        from logjoiner.errors import FileIOError

        raise FileIOError(detail=f"output 폴더 초기화 실패: {output_dir}") from exc


def main() -> int:
    started_at = time.monotonic()
    parser = build_parser()
    args = parser.parse_args()
    _configure_logging(args.log_level)

    start_ms: int | None = None
    end_ms: int | None = None
    try:
        if args.skip_extract:
            if args.start and args.end:
                start_kst = parse_kst_datetime(args.start)
                end_kst = parse_kst_datetime(args.end)
                if start_kst > end_kst:
                    raise InputValidationError(detail="--start 는 --end 보다 늦을 수 없습니다.")
                start_ms = to_utc_epoch_ms(start_kst)
                end_ms = to_utc_epoch_ms(end_kst)
            elif args.start or args.end:
                raise InputValidationError(
                    detail="--skip-extract 사용 시 --start/--end는 함께 지정해야 합니다."
                )
        else:
            if not args.start or not args.end:
                raise InputValidationError(detail="--skip-extract 미사용 시 --start와 --end는 필수입니다.")
            start_kst = parse_kst_datetime(args.start)
            end_kst = parse_kst_datetime(args.end)
            if start_kst > end_kst:
                raise InputValidationError(detail="--start 는 --end 보다 늦을 수 없습니다.")
            start_ms = to_utc_epoch_ms(start_kst)
            end_ms = to_utc_epoch_ms(end_kst)

        config = load_config(args.config)
        if args.poll_interval_seconds <= 0:
            raise InputValidationError(detail="--poll-interval-seconds 는 0보다 커야 합니다.")
        if args.poll_timeout_seconds <= 0:
            raise InputValidationError(detail="--poll-timeout-seconds 는 0보다 커야 합니다.")
        if args.retry_attempts <= 0:
            raise InputValidationError(detail="--retry-attempts 는 1 이상이어야 합니다.")
        if args.retry_backoff_seconds < 0:
            raise InputValidationError(detail="--retry-backoff-seconds 는 0 이상이어야 합니다.")
        if args.query_limit <= 0:
            raise InputValidationError(detail="--query-limit 은 1 이상이어야 합니다.")
        if args.min_split_seconds <= 0:
            raise InputValidationError(detail="--min-split-seconds 는 1 이상이어야 합니다.")
    except LogJoinerError as exc:
        LOGGER.error("%s", exc)
        return 2

    resolved_default_output_file = _resolve_output_path(
        config.output_file if config.output_file else "output/final_analysis_report.csv"
    )
    save_as_pairs: list[tuple[str, str]] = []
    source_tables: dict[str, str] = {}
    resolved_step_outputs: list[str] = []
    for step in config.analysis_steps:
        resolved = _resolve_output_path(step.save_as).as_posix()
        resolved_step_outputs.append(resolved)
        save_as_pairs.append((step.save_as, resolved))
        source_tables[step.name] = resolved
    effective_join_queries = [
        (
            query.name,
            query.save_as,
            [_rewrite_final_join_sql(sql, save_as_pairs) for sql in query.sqls],
        )
        for query in config.final_join_queries
    ]

    LOGGER.info("[LogJoiner] 설정 검증 완료")
    LOGGER.info("- config: %s", Path(args.config).resolve())
    LOGGER.info("- log_group_name: %s", config.log_group_name)
    if start_ms is not None and end_ms is not None:
        LOGGER.info("- query range (UTC ms): %s -> %s", start_ms, end_ms)
    else:
        LOGGER.info("- query range (UTC ms): N/A (--skip-extract)")
    LOGGER.info("- default_output_file: %s", resolved_default_output_file)
    LOGGER.info("- final_join_query_groups: %s", len(effective_join_queries))
    try:
        loaded = load_aws_env(args.env_file)
        LOGGER.info("- env_file: %s (loaded=%s)", Path(args.env_file).resolve(), loaded)
    except LogJoinerError as exc:
        LOGGER.error("%s", exc)
        return 2
    LOGGER.info("- analysis_steps:")
    for idx, step in enumerate(config.analysis_steps, start=1):
        rendered_query = render_step_query(step.query, config.extract_pattern)
        LOGGER.info("  %s. %s -> %s", idx, step.name, resolved_step_outputs[idx - 1])
        if args.dry_run:
            first_line = rendered_query.strip().splitlines()[0] if rendered_query.strip() else ""
            LOGGER.debug("     query preview: %s", first_line)

    if args.dry_run:
        LOGGER.info("[LogJoiner] dry-run 모드 종료 (외부 API 호출 없음)")
        return 0

    logs_client = CloudWatchLogsClient()
    stage_writer = StageWriter(overwrite=not args.no_overwrite_stage)

    start_seconds = start_ms // 1000 if start_ms is not None else None
    end_seconds = end_ms // 1000 if end_ms is not None else None
    try:
        total_rows = 0
        if args.skip_extract:
            LOGGER.info("[LogJoiner] --skip-extract: CloudWatch 추출을 건너뜁니다.")
        else:
            output_dir = Path("output").resolve()
            _clear_output_directory(output_dir)
            LOGGER.info("[LogJoiner] output 폴더 초기화 완료: %s", output_dir)
            LOGGER.info("[LogJoiner] CloudWatch 스텝 실행 시작")
            for idx, step in enumerate(config.analysis_steps, start=1):
                rendered_query = render_step_query(step.query, config.extract_pattern)
                resolved_save_as = resolved_step_outputs[idx - 1]
                LOGGER.info("  - step %s: %s (save_as=%s)", idx, step.name, resolved_save_as)
                result = logs_client.run_query_all(
                    log_group_name=config.log_group_name,
                    query_string=rendered_query,
                    start_time_seconds=start_seconds if start_seconds is not None else 0,
                    end_time_seconds=end_seconds if end_seconds is not None else 0,
                    poll_interval_seconds=args.poll_interval_seconds,
                    timeout_seconds=args.poll_timeout_seconds,
                    retry_attempts=args.retry_attempts,
                    retry_backoff_seconds=args.retry_backoff_seconds,
                    query_limit=args.query_limit,
                    min_split_seconds=args.min_split_seconds,
                )
                artifact = stage_writer.write_step_results(
                    step_name=step.name,
                    records=result.records,
                    save_as=resolved_save_as,
                )
                total_rows += artifact.row_count
                LOGGER.info(
                    "    완료: queryId=%s, rows=%s, csv=%s, json=%s",
                    result.query_id,
                    artifact.row_count,
                    artifact.csv_path.name,
                    artifact.json_path.name,
                )

        output_paths: list[Path] = []
        total_final_rows = 0
        for idx, (name, save_as, sqls) in enumerate(effective_join_queries, start=1):
            final_df = run_final_join_sqls(sqls, source_tables=source_tables)
            output_path = (
                _resolve_output_path(save_as)
                if save_as is not None
                else (_resolve_named_output_path(name) if name is not None else resolved_default_output_file)
            )
            output_path = export_final_csv(final_df, output_path.as_posix())
            output_paths.append(output_path)
            total_final_rows += len(final_df)
            LOGGER.info(
                "- join_result[%s]: name=%s, save_as=%s, rows=%s, file=%s",
                idx,
                name or "default",
                save_as or "default_output_file",
                len(final_df),
                output_path,
            )
    except LogJoinerError as exc:
        LOGGER.error("%s", exc)
        return 1

    elapsed = time.monotonic() - started_at
    LOGGER.info("[LogJoiner] 실행 완료")
    LOGGER.info("- staged_rows: %s", total_rows)
    LOGGER.info("- final_result_files: %s", len(output_paths))
    LOGGER.info("- final_rows_total: %s", total_final_rows)
    LOGGER.info("- elapsed_seconds: %.2f", elapsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
