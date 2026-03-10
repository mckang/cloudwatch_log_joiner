from __future__ import annotations

import time
from json import dumps
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.client import BaseClient

from logjoiner.errors import AwsQueryError

TERMINAL_SUCCESS = "Complete"
TERMINAL_FAILURES = {"Failed", "Cancelled", "Timeout", "Unknown"}


@dataclass(frozen=True)
class QueryExecutionResult:
    query_id: str
    status: str
    records: list[dict[str, str]]
    statistics: dict[str, Any]


def _row_to_dict(row: list[dict[str, str]]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in row:
        field = item.get("field")
        if not field or field == "@ptr":
            continue
        parsed[field] = item.get("value", "")
    return parsed


class CloudWatchLogsClient:
    def __init__(self, client: BaseClient | None = None) -> None:
        self._client = client or boto3.client("logs")

    def start_query(
        self,
        *,
        log_group_name: str,
        query_string: str,
        start_time_seconds: int,
        end_time_seconds: int,
        limit: int | None = None,
    ) -> str:
        response = self._client.start_query(
            logGroupName=log_group_name,
            startTime=start_time_seconds,
            endTime=end_time_seconds,
            queryString=query_string,
            **({"limit": limit} if limit is not None else {}),
        )
        query_id = response.get("queryId")
        if not query_id:
            raise AwsQueryError(detail="CloudWatch start_query 응답에 queryId가 없습니다.")
        return query_id

    def wait_for_query(
        self,
        query_id: str,
        *,
        poll_interval_seconds: float,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        started = time.monotonic()
        while True:
            response = self._client.get_query_results(queryId=query_id)
            status = response.get("status", "Unknown")
            if status == TERMINAL_SUCCESS:
                return response
            if status in TERMINAL_FAILURES:
                raise AwsQueryError(
                    detail=f"CloudWatch 쿼리 실패(status={status}, queryId={query_id})"
                )
            if time.monotonic() - started > timeout_seconds:
                raise AwsQueryError(
                    detail=f"CloudWatch 쿼리 타임아웃({timeout_seconds}s, queryId={query_id})"
                )
            time.sleep(poll_interval_seconds)

    def run_query(
        self,
        *,
        log_group_name: str,
        query_string: str,
        start_time_seconds: int,
        end_time_seconds: int,
        poll_interval_seconds: float,
        timeout_seconds: int,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 1.0,
        query_limit: int = 10000,
    ) -> QueryExecutionResult:
        if retry_attempts <= 0:
            raise ValueError("retry_attempts 는 1 이상이어야 합니다.")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds 는 0 이상이어야 합니다.")

        last_error: Exception | None = None
        for attempt in range(1, retry_attempts + 1):
            try:
                query_id = self.start_query(
                    log_group_name=log_group_name,
                    query_string=query_string,
                    start_time_seconds=start_time_seconds,
                    end_time_seconds=end_time_seconds,
                    limit=query_limit,
                )
                response = self.wait_for_query(
                    query_id,
                    poll_interval_seconds=poll_interval_seconds,
                    timeout_seconds=timeout_seconds,
                )
                rows = response.get("results", [])
                records = [_row_to_dict(row) for row in rows]
                return QueryExecutionResult(
                    query_id=query_id,
                    status=response.get("status", "Unknown"),
                    records=records,
                    statistics=response.get("statistics", {}),
                )
            except AwsQueryError as exc:
                last_error = exc
                if attempt < retry_attempts:
                    sleep_for = retry_backoff_seconds * attempt
                    time.sleep(sleep_for)
                else:
                    break

        raise AwsQueryError(detail=f"CloudWatch 쿼리 재시도 소진({retry_attempts}회): {last_error}")

    def run_query_all(
        self,
        *,
        log_group_name: str,
        query_string: str,
        start_time_seconds: int,
        end_time_seconds: int,
        poll_interval_seconds: float,
        timeout_seconds: int,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 1.0,
        query_limit: int = 10000,
        min_split_seconds: int = 1,
    ) -> QueryExecutionResult:
        if query_limit <= 0:
            raise ValueError("query_limit은 1 이상이어야 합니다.")
        if min_split_seconds <= 0:
            raise ValueError("min_split_seconds는 1 이상이어야 합니다.")

        result = self.run_query(
            log_group_name=log_group_name,
            query_string=query_string,
            start_time_seconds=start_time_seconds,
            end_time_seconds=end_time_seconds,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            query_limit=query_limit,
        )

        # limit 미만이면 해당 구간 결과가 모두 반환된 것으로 간주
        if len(result.records) < query_limit:
            return result

        # 더 이상 쪼갤 수 없는 최소 구간이면 반환
        if (end_time_seconds - start_time_seconds) <= min_split_seconds:
            return result

        mid = (start_time_seconds + end_time_seconds) // 2
        if mid <= start_time_seconds:
            return result

        left = self.run_query_all(
            log_group_name=log_group_name,
            query_string=query_string,
            start_time_seconds=start_time_seconds,
            end_time_seconds=mid,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            query_limit=query_limit,
            min_split_seconds=min_split_seconds,
        )
        if mid + 1 > end_time_seconds:
            right_records: list[dict[str, str]] = []
            right_query_id = ""
        else:
            right = self.run_query_all(
                log_group_name=log_group_name,
                query_string=query_string,
                start_time_seconds=mid + 1,
                end_time_seconds=end_time_seconds,
                poll_interval_seconds=poll_interval_seconds,
                timeout_seconds=timeout_seconds,
                retry_attempts=retry_attempts,
                retry_backoff_seconds=retry_backoff_seconds,
                query_limit=query_limit,
                min_split_seconds=min_split_seconds,
            )
            right_records = right.records
            right_query_id = right.query_id

        merged = left.records + right_records
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in merged:
            key = dumps(row, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)

        return QueryExecutionResult(
            query_id=",".join([p for p in [left.query_id, right_query_id] if p]),
            status="Complete",
            records=deduped,
            statistics={"split": True, "segments": 2},
        )
