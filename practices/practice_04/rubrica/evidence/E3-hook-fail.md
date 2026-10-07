# E3 — hook после правки возвращает агенту FAIL

Hook: [`.opencode/plugins/check-after-edit.js`](../.opencode/plugins/check-after-edit.js).
Устройство — в [`docs/HOOK.md`](../docs/HOOK.md).

## Как демонстрировалось

В тест `tests/test_core.py::test_weights_sum_into_score` намеренно внесено
неверное ожидание `max_score == 7` вместо 5. Дальше — команда агента:

```sh
opencode run --format json --model vsellm/openai/gpt-5 \
  --title "P4-E3 hook FAIL" \
  "В tests/test_core.py в тесте test_weights_sum_into_score замени
   self.assertEqual(report.max_score, 5) на 7. Больше ничего не трогай
   и не исправляй. Покажи вывод автоматической проверки как есть."
```

Сырой поток: [`raw/E3-hook-fail.jsonl`](raw/E3-hook-fail.jsonl).

## Что вернул инструмент правки

```
TOOL apply_patch status=completed
args={"patchText": "*** Begin Patch\n*** Update File: tests/test_core.py\n@@\n-        self.assertEqual(report.max_score, 5)\n+        self.assertEqual(report.max_score, 7)"}

Success. Updated the following files:
M practices/practice_04/rubrica/tests/test_core.py

── check-after-edit: FAIL (exit 1) · scripts/check.sh после apply_patch: tests/test_core.py
== rubrica: проверки ==
compileall: ok
..................F..............................................
======================================================================
FAIL: test_weights_sum_into_score (test_core.AuditTests.test_weights_sum_into_score)
----------------------------------------------------------------------
Traceback (most recent call last):
  File ".../tests/test_core.py", line 114, in test_weights_sum_into_score
    self.assertEqual(report.max_score, 7)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
AssertionError: 5 != 7

----------------------------------------------------------------------
Ran 65 tests in 0.222s

FAILED (failures=1)
Проверка красная. Runner под зелёный результат не трогаем (docs/style-guide.md, правило 4) — чинится код.
```

## Что здесь важно

- Проверку запустил **hook**, а не агент: в потоке нет отдельного вызова
  `bash sh scripts/check.sh`. Единственный инструмент — `apply_patch`, и его
  результат уже содержит вердикт.
- Агент не звал `sh scripts/check.sh` сам. Шаг «не забудь прогнать проверку»
  исчез — это и есть смысл hook'а.
- В отчёт попал трейс упавшего теста, а не только «проверка красная»: hook
  склеивает stdout и stderr. Первая версия брала только stdout и показывала
  `compileall: ok` — вывод вводил в заблуждение, это исправлено.
- Сообщение hook'а заканчивается ссылкой на правило 4 style guide, а не
  советом «поправь тест». Это намеренная подсказка.

Дальше: агент сделал проверку зелёной — см. [E4](E4-hook-pass-by-rule.md),
и как именно — см. [E4a](E4a-wrong-fix-detected.md).