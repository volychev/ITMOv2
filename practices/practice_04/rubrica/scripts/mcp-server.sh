#!/usr/bin/env sh
# Запуск MCP-сервера rubrica в stdio-режиме.
# Пути вычисляются от расположения скрипта, поэтому конфиг opencode.json
# не зависит от того, из какой директории запущен opencode.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY=$(command -v python3)
fi

cd "$ROOT"
PYTHONPATH="$ROOT/mcp${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec "$PY" -m rubrica_mcp.server