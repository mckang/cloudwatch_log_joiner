from __future__ import annotations

from typing import Any

import pytest

from logjoiner.aws_logs import CloudWatchLogsClient
from logjoiner.errors import AwsQueryError


class FakeLogsClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls = 0

    def start_query(self, **_: Any) -> dict[str, str]:
        return {"queryId": "q-123"}

    def get_query_results(self, **_: Any) -> dict[str, Any]:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def test_run_query_complete_status() -> None:
    fake = FakeLogsClient(
        [
            {"status": "Running"},
            {
                "status": "Complete",
                "results": [
                    [
                        {"field": "@timestamp", "value": "2026-03-10T00:00:00Z"},
                        {"field": "traceId", "value": "abc"},
                    ]
                ],
            },
        ]
    )
    client = CloudWatchLogsClient(client=fake)  # type: ignore[arg-type]
    result = client.run_query(
        log_group_name="/aws/lambda/x",
        query_string="fields traceId",
        start_time_seconds=0,
        end_time_seconds=1,
        poll_interval_seconds=0,
        timeout_seconds=3,
    )
    assert result.status == "Complete"
    assert result.records[0]["traceId"] == "abc"


def test_run_query_failed_status() -> None:
    fake = FakeLogsClient([{"status": "Failed"}])
    client = CloudWatchLogsClient(client=fake)  # type: ignore[arg-type]
    with pytest.raises(AwsQueryError) as exc_info:
        client.run_query(
            log_group_name="/aws/lambda/x",
            query_string="fields traceId",
            start_time_seconds=0,
            end_time_seconds=1,
            poll_interval_seconds=0,
            timeout_seconds=3,
        )
    assert "[LJ101]" in str(exc_info.value)


class FlakyLogsClient:
    def __init__(self) -> None:
        self.start_calls = 0

    def start_query(self, **_: Any) -> dict[str, str]:
        self.start_calls += 1
        if self.start_calls == 1:
            raise AwsQueryError(detail="temporary error")
        return {"queryId": "q-123"}

    def get_query_results(self, **_: Any) -> dict[str, Any]:
        return {"status": "Complete", "results": []}


def test_run_query_retries_then_success() -> None:
    flaky = FlakyLogsClient()
    client = CloudWatchLogsClient(client=flaky)  # type: ignore[arg-type]
    result = client.run_query(
        log_group_name="/aws/lambda/x",
        query_string="fields traceId",
        start_time_seconds=0,
        end_time_seconds=1,
        poll_interval_seconds=0,
        timeout_seconds=3,
        retry_attempts=2,
        retry_backoff_seconds=0,
    )
    assert result.status == "Complete"


def test_run_query_all_splits_time_range(monkeypatch: pytest.MonkeyPatch) -> None:
    client = CloudWatchLogsClient(client=FakeLogsClient([{"status": "Complete", "results": []}]))  # type: ignore[arg-type]
    calls: list[tuple[int, int]] = []

    def fake_run_query(**kwargs: Any) -> Any:
        start = int(kwargs["start_time_seconds"])
        end = int(kwargs["end_time_seconds"])
        query_limit = int(kwargs["query_limit"])
        calls.append((start, end))
        if (end - start) > 1:
            records = [{"traceId": f"{start}"}, {"traceId": f"{end}"}]
        else:
            records = [{"traceId": f"{start}-{end}"}]
        # query_limit에 정확히 도달하면 분할 유도
        if len(records) > query_limit:
            records = records[:query_limit]
        return type(
            "Result",
            (),
            {
                "query_id": f"{start}-{end}",
                "status": "Complete",
                "records": records,
                "statistics": {},
            },
        )()

    monkeypatch.setattr(client, "run_query", fake_run_query)
    result = client.run_query_all(
        log_group_name="/aws/lambda/x",
        query_string="fields traceId",
        start_time_seconds=0,
        end_time_seconds=3,
        poll_interval_seconds=0,
        timeout_seconds=3,
        retry_attempts=1,
        retry_backoff_seconds=0,
        query_limit=2,
        min_split_seconds=1,
    )
    assert len(calls) >= 3
    assert len(result.records) >= 2
