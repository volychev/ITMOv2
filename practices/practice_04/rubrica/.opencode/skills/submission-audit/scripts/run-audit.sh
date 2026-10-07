#!/usr/bin/env bash
# Обёртка skill submission-audit: аудит + разбор результата.
# Вызывается из SKILL.md, шаг 1 и шаг 3. Коды возврата те же, что у rubrica.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY=$(command -v python3)

TARGET=${1:-..}
SPEC=${2:-rubrics/practice_04.yaml}

"$PY" -m rubrica.cli "$TARGET" --spec "$SPEC"
STATUS=$?

case "$STATUS" in
  0) echo "ИТОГ: все правила пройдены, можно сдавать." ;;
  1) echo "ИТОГ: есть провалы без блокеров — закрой их и повтори." ;;
  2) echo "ИТОГ: блокер или отказ входа — читай сообщение ОТКАЗ или fix_hints[0]." ;;
  3) echo "ИТОГ: аудит прошёл, рецензия недоступна. Сдавать можно." ;;
  *) echo "ИТОГ: неожиданный код возврата $STATUS." ;;
esac

exit "$STATUS"