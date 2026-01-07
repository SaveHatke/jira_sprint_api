#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# --- load .env (optional) ---
if [ -f ".env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^\s*#' .env | xargs -d '\n' 2>/dev/null || true)
fi

# --- create venv if missing ---
if [ ! -d "$VENV_DIR" ]; then
  echo "[run] Creating virtualenv at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# --- activate venv ---
# shellcheck disable=SC1091
#linux source "$VENV_DIR/bin/activate"

source "$VENV_DIR/Scripts/activate"

python -m pip install -U pip >/dev/null

# --- dependency check/install ---
DEPS_HASH_FILE="$VENV_DIR/.deps_hash"
NEW_HASH="$(python - <<'PY'
import hashlib, pathlib
p = pathlib.Path("pyproject.toml")
data = p.read_bytes() if p.exists() else b""
print(hashlib.sha256(data).hexdigest())
PY
)"

OLD_HASH=""
if [ -f "$DEPS_HASH_FILE" ]; then
  OLD_HASH="$(cat "$DEPS_HASH_FILE" || true)"
fi

if [ "$NEW_HASH" != "$OLD_HASH" ]; then
  echo "[run] Installing dependencies (pyproject.toml changed or first run)"
  # editable install is best for local dev; change to `pip install .` if you prefer
  pip install -e ".[dev]"
  echo "$NEW_HASH" > "$DEPS_HASH_FILE"
else
  echo "[run] Dependencies look up-to-date"
fi

# --- run server ---
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "[run] Starting server on ${HOST}:${PORT}"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
