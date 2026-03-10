from __future__ import annotations

from pathlib import Path

import pytest

from logjoiner.errors import FileIOError, InputValidationError
from logjoiner.env import load_aws_env


def test_load_aws_env_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AWS_ACCESS_KEY_ID=abc\nAWS_SECRET_ACCESS_KEY=def\nAWS_DEFAULT_REGION=ap-northeast-2\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    loaded = load_aws_env(str(env_file))
    assert loaded is True


def test_load_aws_env_invalid_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("AWS_ACCESS_KEY_ID=abc\n", encoding="utf-8")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    with pytest.raises(InputValidationError):
        load_aws_env(str(env_file))


def test_load_aws_env_missing_file_exposes_file_io_code() -> None:
    with pytest.raises(FileIOError) as exc_info:
        load_aws_env("/tmp/not-exists-logjoiner.env")
    assert "[LJ301]" in str(exc_info.value)
