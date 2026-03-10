from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from logjoiner.errors import FileIOError, InputValidationError


@dataclass(frozen=True)
class AnalysisStep:
    name: str
    query: str
    save_as: str


@dataclass(frozen=True)
class JoinQuerySpec:
    name: str | None
    save_as: str | None
    sqls: list[str]


@dataclass(frozen=True)
class AppConfig:
    log_group_name: str
    extract_pattern: str
    output_file: str | None
    analysis_steps: list[AnalysisStep]
    final_join_queries: list[JoinQuerySpec]


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(detail=f"설정 키 '{key}'는 비어있지 않은 문자열이어야 합니다.")
    return value


def _normalize_sql_list(value: Any, *, path: str) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
        return value
    raise InputValidationError(detail=f"{path}는 비어있지 않은 SQL 문자열 또는 문자열 리스트여야 합니다.")


def _parse_final_join_queries(data: dict[str, Any]) -> list[JoinQuerySpec]:
    sqls = data.get("final_join_sqls")
    if sqls is not None:
        if not isinstance(sqls, list) or not sqls:
            raise InputValidationError(detail="설정 키 'final_join_sqls'는 비어있지 않은 리스트여야 합니다.")

        # 형태 1) 기존 호환: ["sql1", "sql2"]
        if all(isinstance(item, str) and item.strip() for item in sqls):
            return [JoinQuerySpec(name=None, save_as=None, sqls=sqls)]

        # 형태 2) 권장: [{name: "...", query: "...|[...]", save_as: "..."}]
        if all(isinstance(item, dict) and {"name", "query", "save_as"}.issubset(item.keys()) for item in sqls):
            parsed: list[JoinQuerySpec] = []
            for idx, item in enumerate(sqls, start=1):
                name = item["name"]
                save_as = item["save_as"]
                if not isinstance(name, str) or not name.strip():
                    raise InputValidationError(
                        detail=f"final_join_sqls[{idx}].name은 비어있지 않은 문자열이어야 합니다."
                    )
                if not isinstance(save_as, str) or not save_as.strip():
                    raise InputValidationError(
                        detail=f"final_join_sqls[{idx}].save_as는 비어있지 않은 문자열이어야 합니다."
                    )
                parsed.append(
                    JoinQuerySpec(
                        name=name.strip(),
                        save_as=save_as.strip(),
                        sqls=_normalize_sql_list(item["query"], path=f"final_join_sqls[{idx}].query"),
                    )
                )
            return parsed

        # 형태 3) 기존 호환: [{a: ["sql1", "sql2"]}, {b: "sql"}]
        legacy_parsed: list[JoinQuerySpec] = []
        for idx, item in enumerate(sqls, start=1):
            if not isinstance(item, dict) or len(item) != 1:
                raise InputValidationError(
                    detail=(
                        "final_join_sqls 형식이 올바르지 않습니다. "
                        "권장 형식: - name: a, query: ..., save_as: output/a.csv"
                    )
                )
            name, value = next(iter(item.items()))
            if not isinstance(name, str) or not name.strip():
                raise InputValidationError(
                    detail=f"final_join_sqls[{idx}]의 키(name)는 비어있지 않은 문자열이어야 합니다."
                )
            legacy_parsed.append(
                JoinQuerySpec(
                    name=name.strip(),
                    save_as=f"{name.strip()}.csv",
                    sqls=_normalize_sql_list(value, path=f"final_join_sqls[{idx}].{name}"),
                )
            )
        return legacy_parsed

    # 하위 호환: 단일 final_join_sql
    single_sql = data.get("final_join_sql")
    if isinstance(single_sql, str) and single_sql.strip():
        return [JoinQuerySpec(name=None, save_as=None, sqls=[single_sql])]
    raise InputValidationError(
        detail="설정 키 'final_join_sqls' 또는 'final_join_sql' 중 하나는 필수입니다."
    )


def _parse_steps(data: dict[str, Any]) -> list[AnalysisStep]:
    steps = data.get("analysis_steps")
    if not isinstance(steps, list) or not steps:
        raise InputValidationError(detail="설정 키 'analysis_steps'는 1개 이상의 step 리스트여야 합니다.")

    parsed: list[AnalysisStep] = []
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise InputValidationError(detail=f"analysis_steps[{idx}]는 객체여야 합니다.")
        try:
            name = step["name"]
            query = step["query"]
            save_as = step["save_as"]
        except KeyError as exc:
            raise InputValidationError(detail=f"analysis_steps[{idx}]에 필수 키가 없습니다: {exc}") from exc
        if not all(isinstance(v, str) and v.strip() for v in (name, query, save_as)):
            raise InputValidationError(
                detail=f"analysis_steps[{idx}]의 name/query/save_as는 비어있지 않은 문자열이어야 합니다."
            )
        parsed.append(AnalysisStep(name=name, query=query, save_as=save_as))
    return parsed


def load_config(path: str) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileIOError(detail=f"설정 파일을 찾을 수 없습니다: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileIOError(detail=f"설정 파일 읽기 실패: {config_path}") from exc
    if not isinstance(raw, dict):
        raise InputValidationError(detail="설정 파일 루트는 YAML 객체여야 합니다.")

    missing_keys = [
        key
        for key in (
            "log_group_name",
            "extract_pattern",
            "analysis_steps",
        )
        if key not in raw
    ]
    if missing_keys:
        raise InputValidationError(detail=f"필수 설정 키 누락: {', '.join(missing_keys)}")

    steps = _parse_steps(raw)
    final_join_queries = _parse_final_join_queries(raw)
    output_file_value = raw.get("output_file")
    output_file: str | None
    if output_file_value is None:
        output_file = None
    else:
        if not isinstance(output_file_value, str) or not output_file_value.strip():
            raise InputValidationError(detail="설정 키 'output_file'는 비어있지 않은 문자열이어야 합니다.")
        output_file = output_file_value

    requires_output_file = any(query.save_as is None for query in final_join_queries)
    if requires_output_file and not output_file:
        raise InputValidationError(
            detail=(
                "이 설정 형식에서는 'output_file'이 필요합니다. "
                "(단일 final_join_sql 또는 문자열 리스트형 final_join_sqls 사용 시)"
            )
        )

    return AppConfig(
        log_group_name=_require_string(raw, "log_group_name"),
        extract_pattern=_require_string(raw, "extract_pattern"),
        output_file=output_file,
        analysis_steps=steps,
        final_join_queries=final_join_queries,
    )


def render_step_query(query: str, extract_pattern: str) -> str:
    if "%" in query and "%s" not in query:
        raise InputValidationError(
            detail="query 템플릿에 `%s` 외 포맷 문자열이 포함되어 있습니다. `%s`만 지원합니다."
        )
    if "%s" not in query:
        return query
    try:
        return query % extract_pattern
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            detail="query 템플릿 치환에 실패했습니다. `%s` 플레이스홀더 사용 여부를 확인하세요."
        ) from exc
