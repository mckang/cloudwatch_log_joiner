from __future__ import annotations

from pathlib import Path

import pytest

from logjoiner.errors import InputValidationError
from logjoiner.config import load_config, render_step_query


def test_load_config_sample_file() -> None:
    config = load_config("config.sample.yaml")
    assert config.log_group_name == "/aws/lambda/my-service-logs"
    assert config.extract_pattern == "ERROR"
    assert config.output_file == "output/final_analysis_report.csv"
    assert len(config.analysis_steps) == 2
    assert len(config.final_join_queries) == 2
    assert config.final_join_queries[0].name == "a"
    assert config.final_join_queries[0].save_as == "output/a.csv"
    assert "\n" in config.analysis_steps[0].query


def test_load_config_missing_required_key(tmp_path: Path) -> None:
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(
        """
log_group_name: "/aws/lambda/x"
output_file: "x.csv"
analysis_steps:
  - name: "s1"
    query: "fields @message"
    save_as: "s1.csv"
final_join_sqls: ["select 1"]
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(InputValidationError):
        load_config(str(bad_config))


def test_render_step_query_with_extract_pattern() -> None:
    rendered = render_step_query("filter @message like /%s/", "ERROR")
    assert "ERROR" in rendered


def test_render_step_query_invalid_template() -> None:
    with pytest.raises(InputValidationError) as exc_info:
        render_step_query("filter @message like /%d/", "ERROR")
    assert "[LJ001]" in str(exc_info.value)


def test_load_config_single_final_join_sql_backward_compatible(tmp_path: Path) -> None:
    cfg = tmp_path / "single.yaml"
    cfg.write_text(
        """
log_group_name: "/aws/lambda/x"
extract_pattern: "ERROR"
output_file: "x.csv"
analysis_steps:
  - name: "s1"
    query: "fields @message"
    save_as: "s1.csv"
final_join_sql: "select 1 as ok"
""".strip(),
        encoding="utf-8",
    )
    config = load_config(str(cfg))
    assert len(config.final_join_queries) == 1
    assert config.final_join_queries[0].name is None
    assert config.final_join_queries[0].save_as is None
    assert config.final_join_queries[0].sqls == ["select 1 as ok"]


def test_load_config_named_final_join_sqls(tmp_path: Path) -> None:
    cfg = tmp_path / "named.yaml"
    cfg.write_text(
        """
log_group_name: "/aws/lambda/x"
extract_pattern: "ERROR"
analysis_steps:
  - name: "s1"
    query: "fields @message"
    save_as: "s1.csv"
final_join_sqls:
  - name: "a"
    query:
      - "select 1 as v"
      - "select * from __input__"
    save_as: "output/a.csv"
  - name: "b"
    query: "select 2 as v"
    save_as: "output/b.csv"
""".strip(),
        encoding="utf-8",
    )
    config = load_config(str(cfg))
    assert config.output_file is None
    assert len(config.final_join_queries) == 2
    assert config.final_join_queries[0].name == "a"
    assert config.final_join_queries[0].save_as == "output/a.csv"
    assert len(config.final_join_queries[0].sqls) == 2
