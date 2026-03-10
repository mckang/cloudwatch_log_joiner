from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from logjoiner.errors import FileIOError


@dataclass(frozen=True)
class StepStageArtifact:
    step_name: str
    csv_path: Path
    json_path: Path
    row_count: int


class StageWriter:
    def __init__(self, base_dir: Path | None = None, *, overwrite: bool = True) -> None:
        self.base_dir = base_dir or Path.cwd()
        self.overwrite = overwrite

    def _resolve_output_path(self, path: Path) -> Path:
        if self.overwrite or not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        idx = 1
        while True:
            candidate = path.with_name(f"{stem}.{idx}{suffix}")
            if not candidate.exists():
                return candidate
            idx += 1

    def write_step_results(
        self,
        *,
        step_name: str,
        records: list[dict[str, str]],
        save_as: str,
    ) -> StepStageArtifact:
        csv_path = self._resolve_output_path((self.base_dir / save_as).resolve())
        json_path = csv_path.with_suffix(".json")
        try:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(records).to_csv(csv_path, index=False, encoding="utf-8")
            json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            raise FileIOError(detail=f"스테이징 파일 저장 실패: {csv_path}") from exc
        return StepStageArtifact(
            step_name=step_name,
            csv_path=csv_path,
            json_path=json_path,
            row_count=len(records),
        )
