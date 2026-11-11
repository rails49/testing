#!/bin/bash
# The gate: what CI runs and a change must pass.
set -e

cd "$(dirname "$0")/.."

uv sync --locked --quiet
uv run ruff check .
uv run black --check .
uv run pyright
uv run pytest -q
