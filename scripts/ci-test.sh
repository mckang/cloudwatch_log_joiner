#!/usr/bin/env bash
set -euo pipefail

echo "[ci] sync dependencies"
uv sync

echo "[ci] ruff"
uv run ruff check src tests

echo "[ci] mypy"
uv run mypy --ignore-missing-imports --disable-error-code=import-untyped src tests

echo "[ci] pytest"
uv run pytest
