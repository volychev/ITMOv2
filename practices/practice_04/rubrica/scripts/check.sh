#!/usr/bin/env sh
# Runner проверок rubrica. Это единственная доверенная точка проверки:
# hook после правки, skill и агент в чате вызывают именно её.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY=$(command -v python3)
fi

echo "== rubrica: проверки =="
"$PY" -m compileall -q src >/dev/null
echo "compileall: ok"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

"$PY" -m unittest discover -s tests -t tests "$@"
STATUS=$?

echo "== rubrica: готово =="
exit "$STATUS"