from __future__ import annotations

from pathlib import Path

from logjoiner.stage import StageWriter


def test_stage_writer_collision_policy(tmp_path: Path) -> None:
    writer = StageWriter(base_dir=tmp_path, overwrite=False)
    first = writer.write_step_results(step_name="s1", records=[{"a": "1"}], save_as="temp.csv")
    second = writer.write_step_results(step_name="s1", records=[{"a": "2"}], save_as="temp.csv")
    assert first.csv_path.name == "temp.csv"
    assert second.csv_path.name == "temp.1.csv"
    assert first.csv_path.exists()
    assert second.csv_path.exists()
