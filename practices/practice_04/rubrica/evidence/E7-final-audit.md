# E7 — финальный прогон: handoff, skill, MCP и runner в одной сессии

Проверка на зрелом состоянии работы: новая сессия агента восстанавливает
контекст из `AGENTS.md` и `docs/HANDOFF.md`, применяет skill, вызывает MCP и
запускает runner.

**Команда:**

```sh
opencode run --format json --model vsellm/openai/gpt-5 \
  --title "P4-E7 финальный аудит и handoff" \
  "Прочитай AGENTS.md и docs/HANDOFF.md. Затем: (1) загрузи skill
   submission-audit, (2) вызови MCP tool rubrica_audit с target='.' и
   spec='rubrics/practice_04.yaml', (3) запусти sh scripts/check.sh.
   Ничего не меняй. Ответь: что уже сделано, что осталось, какой балл у
   аудита и какой код вернул sh scripts/check.sh."
```

Сырой поток: [`raw/E7-final-audit-and-handoff.jsonl`](raw/E7-final-audit-and-handoff.jsonl).

## Фактические вызовы

| Шаг | Инструмент | Аргументы | Статус |
|---|---|---|---|
| 1 | `read` | `AGENTS.md` | completed |
| 2 | `read` | `docs/HANDOFF.md` | completed |
| 3 | `skill` | `{"name": "submission-audit"}` | completed |
| 4 | `rubrica_rubrica_audit` | `{"target": ".", "spec": "rubrics/practice_04.yaml"}` | completed |
| 5 | `bash` | `sh scripts/check.sh` | completed |

## Ответ агента

> **Что уже сделано:**
> - По HANDOFF: фича A (валидация), ядро, фича B (деградация зависимости),
>   среда агента (AGENTS.md, skill, MCP, hook, runner) готовы. В HANDOFF
>   отмечено: `sh scripts/check.sh` — 74 теста, OK; `make audit` — 17/17,
>   exit 0.
> - По фактическому запуску сейчас: `rubrica_audit` показал 17/17,
>   blockers 0, exit_code 0. `scripts/check.sh` выполнился успешно,
>   74 теста прошли.
>
> **Что осталось:**
> - Обязательных задач не осталось (по HANDOFF: «Ничего обязательного.
>   Работа закрыта»).
> - В «Куда идти дальше» есть необязательные улучшения (таймаут 30–60 с,
>   добавить `file_contains` для `reflection.md`, отдельная проверка
>   зависимости через MCP, переписать hook под opencode 2.x), но это не
>   blockers.
>
> **Баллы аудита:** 17 из 17, `exit_code` 0.
> **Код возврата `sh scripts/check.sh`:** успех; тесты: 74, статус OK.

## Вывод

Агент верно восстановил состояние: разделил «сделано» и «осталось», назвал
необязательные улучшения улучшениями, а не блокерами, и сверил HANDOFF с
фактическим прогоном. Цифры в HANDOFF (74 теста, 17/17) совпали с реальными
результатами проверок.

Первый прогон E7 делался на устаревшем `docs/HANDOFF.md`, где ещё стояло
«доделать фичу B в worktree». Агент тогда не заметил расхождения. HANDOFF
обновлён, прогон повторён — теперь состояние совпадает с фактическим.
Это видно по двум версиям одного и того же ответа.

## Итоговая проверка для сдачи

```
$ sh scripts/check.sh
== rubrica: проверки ==
compileall: ok
..........................................................................
----------------------------------------------------------------------
Ran 74 tests in 0.227s

OK
== rubrica: готено ==

$ make audit
баллы:  17/17   провалено: 0   blocker'ов: 0
EXIT=0
```

Дополнительно:

```sh
opencode debug skill   # submission-audit найден
opencode mcp list      # rubrica connected
```