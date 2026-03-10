from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from logjoiner.aws_logs import CloudWatchLogsClient
from logjoiner.errors import AwsQueryError
from logjoiner.main import main


def _write_config(path: Path) -> None:
    path.write_text(
        """
log_group_name: "/aws/lambda/test"
extract_pattern: "ERROR"
output_file: "output/final.csv"
analysis_steps:
  - name: "s1"
    query: |
      fields traceId, @timestamp
      | filter @message like /%s/
    save_as: "output/s1.csv"
final_join_sqls:
  - name: "result"
    query: |
      SELECT *
      FROM s1
    save_as: "output/result.csv"
""".strip(),
        encoding="utf-8",
    )


def test_main_success_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    env = tmp_path / ".env"
    _write_config(cfg)
    env.write_text("AWS_ACCESS_KEY_ID=a\nAWS_SECRET_ACCESS_KEY=b\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class FakeCloudWatch:
        def run_query_all(self, **_: Any) -> Any:
            return type(
                "Result",
                (),
                {
                    "query_id": "q-1",
                    "records": [
                        {"@timestamp": "2026-03-10T00:00:00Z", "traceId": "t1"},
                        {"@timestamp": "2026-03-10T00:00:01Z", "traceId": "t2"},
                    ],
                },
            )()

    monkeypatch.setattr("logjoiner.main.CloudWatchLogsClient", lambda: FakeCloudWatch())
    monkeypatch.setattr(
        "sys.argv",
        [
            "logjoiner",
            "--start",
            "2026-03-10 00:00:00",
            "--end",
            "2026-03-10 00:01:00",
            "--config",
            str(cfg),
            "--env-file",
            str(env),
        ],
    )

    code = main()
    assert code == 0
    assert (tmp_path / "output" / "s1.csv").exists()
    assert (tmp_path / "output" / "result.csv").exists()


def test_main_failure_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    env = tmp_path / ".env"
    _write_config(cfg)
    env.write_text("AWS_ACCESS_KEY_ID=a\nAWS_SECRET_ACCESS_KEY=b\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class FakeCloudWatch:
        def run_query_all(self, **_: Any) -> Any:
            raise AwsQueryError(detail="simulated failure")

    monkeypatch.setattr("logjoiner.main.CloudWatchLogsClient", lambda: FakeCloudWatch())
    monkeypatch.setattr(
        "sys.argv",
        [
            "logjoiner",
            "--start",
            "2026-03-10 00:00:00",
            "--end",
            "2026-03-10 00:01:00",
            "--config",
            str(cfg),
            "--env-file",
            str(env),
        ],
    )

    code = main()
    assert code == 1


def test_main_skip_extract_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    env = tmp_path / ".env"
    _write_config(cfg)
    env.write_text("AWS_ACCESS_KEY_ID=a\nAWS_SECRET_ACCESS_KEY=b\n", encoding="utf-8")
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)
    (tmp_path / "output" / "s1.csv").write_text(
        "@timestamp,traceId\n2026-03-10T00:00:00Z,t1\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    class ShouldNotCallCloudWatch:
        def run_query_all(self, **_: Any) -> Any:
            raise AssertionError("skip-extract 경로에서 CloudWatch 호출이 발생하면 안 됩니다.")

    monkeypatch.setattr("logjoiner.main.CloudWatchLogsClient", lambda: ShouldNotCallCloudWatch())
    monkeypatch.setattr(
        "sys.argv",
        [
            "logjoiner",
            "--skip-extract",
            "--config",
            str(cfg),
            "--env-file",
            str(env),
        ],
    )

    code = main()
    assert code == 0
    assert (tmp_path / "output" / "result.csv").exists()


def test_aws_retry_path() -> None:
    class FlakyClient:
        def __init__(self) -> None:
            self.start_calls = 0

        def start_query(self, **_: Any) -> dict[str, str]:
            self.start_calls += 1
            if self.start_calls < 2:
                raise AwsQueryError(detail="temporary failure")
            return {"queryId": "q-123"}

        def get_query_results(self, **_: Any) -> dict[str, Any]:
            return {"status": "Complete", "results": []}

    client = CloudWatchLogsClient(client=FlakyClient())  # type: ignore[arg-type]
    result = client.run_query(
        log_group_name="/aws/lambda/x",
        query_string="fields traceId",
        start_time_seconds=0,
        end_time_seconds=1,
        poll_interval_seconds=0,
        timeout_seconds=1,
        retry_attempts=2,
        retry_backoff_seconds=0,
    )
    assert result.status == "Complete"
