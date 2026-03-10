from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(str, Enum):
    INPUT = "INPUT"
    AWS = "AWS"
    SQL = "SQL"
    FILE_IO = "FILE_IO"


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    category: ErrorCategory
    user_message: str


ERROR_SPECS: dict[str, ErrorSpec] = {
    "LJ001": ErrorSpec(
        code="LJ001",
        category=ErrorCategory.INPUT,
        user_message="입력값이 유효하지 않습니다. 인자/설정 파일 형식을 확인하세요.",
    ),
    "LJ101": ErrorSpec(
        code="LJ101",
        category=ErrorCategory.AWS,
        user_message="CloudWatch 쿼리 실행 중 오류가 발생했습니다. 잠시 후 재시도하세요.",
    ),
    "LJ201": ErrorSpec(
        code="LJ201",
        category=ErrorCategory.SQL,
        user_message="최종 SQL 실행에 실패했습니다. SQL 문법 및 참조 테이블을 확인하세요.",
    ),
    "LJ301": ErrorSpec(
        code="LJ301",
        category=ErrorCategory.FILE_IO,
        user_message="파일 읽기/쓰기 중 오류가 발생했습니다. 경로와 권한을 확인하세요.",
    ),
}


class LogJoinerError(Exception):
    def __init__(self, spec: ErrorSpec, *, detail: str | None = None) -> None:
        self.spec = spec
        self.detail = detail
        suffix = f" (detail={detail})" if detail else ""
        super().__init__(f"[{spec.code}] {spec.user_message}{suffix}")


class InputValidationError(LogJoinerError):
    def __init__(self, *, detail: str | None = None) -> None:
        super().__init__(ERROR_SPECS["LJ001"], detail=detail)


class AwsQueryError(LogJoinerError):
    def __init__(self, *, detail: str | None = None) -> None:
        super().__init__(ERROR_SPECS["LJ101"], detail=detail)


class SqlExecutionError(LogJoinerError):
    def __init__(self, *, detail: str | None = None) -> None:
        super().__init__(ERROR_SPECS["LJ201"], detail=detail)


class FileIOError(LogJoinerError):
    def __init__(self, *, detail: str | None = None) -> None:
        super().__init__(ERROR_SPECS["LJ301"], detail=detail)
