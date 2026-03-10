from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from logjoiner.errors import FileIOError, InputValidationError


def load_aws_env(env_file: str) -> bool:
    env_path = Path(env_file)
    if not env_path.exists():
        raise FileIOError(detail=f"dotenv 파일을 찾을 수 없습니다: {env_path}")
    loaded = load_dotenv(dotenv_path=env_path, override=False)

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    # 둘 중 하나만 존재하면 잘못된 설정으로 간주한다.
    if (access_key and not secret_key) or (secret_key and not access_key):
        raise InputValidationError(
            detail="AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY는 함께 설정되어야 합니다."
        )

    return bool(loaded)
