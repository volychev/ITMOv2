# E2 — собственный MCP: успешный вызов и ошибочный вход

Сервер: [`mcp/rubrica_mcp/server.py`](../mcp/rubrica_mcp/server.py), один tool
`rubrica_audit`. Устройство и контракт — в [`docs/MCP.md`](../docs/MCP.md).

**Подключение:**

```sh
opencode mcp list
#  ●  ✓ rubrica connected
#         sh scripts/mcp-server.sh
```

## Сценарий 1. Корректный вход

Вызов из сессии агента (см. [E1](E1-agents-skill-mcp.md)):

```
TOOL rubrica_rubrica_audit status=completed
args={"target": ".", "spec": "rubrics/practice_04.yaml"}
```

Ответ — JSON-вердикт: 14/17, `exit_code: 2`, 11 правил с пометкой `ok`,
`fix_hints` с приоритетом. Полный ответ приведён в E1.

## Сценарий 2. Ошибочный вход — несуществующая папка

**Команда:**

```sh
opencode run --format json --model vsellm/openai/gpt-5 \
  --title "P4-E2 ошибочный вход в MCP" \
  "Вызови MCP tool rubrica_audit дважды с ошибочным входом:
   (1) target='../no-such-folder', (2) spec='rubrics/missing.yaml' при target='.'
   Покажи дословно поле error из ответа инструмента."
```

Сырой поток: [`raw/E2-mcp-error-input.jsonl`](raw/E2-mcp-error-input.jsonl).

**Фактический ответ инструмента, вызов 1:**

```
TOOL rubrica_rubrica_audit status=completed
args={"target": "../no-such-folder"}
{
  "ok": false,
  "error": "вход не прошёл валидацию: папка ../no-such-folder не существует",
  "target": "../no-such-folder",
  "spec": null,
  "findings": [],
  "score": 0,
  "max_score": 0,
  "fix_hints": ["исправь вход и повтори вызов"],
  "elapsed_ms": 0
}
```

**Фактический ответ инструмента, вызов 2:**

```
TOOL rubrica_rubrica_audit status=completed
args={"spec": "rubrics/missing.yaml", "target": "."}
{
  "ok": false,
  "error": "файл рубрики rubrics/missing.yaml не найден",
  "target": ".",
  "spec": "rubrics/missing.yaml",
  "findings": [],
  "score": 0,
  "max_score": 0,
  "fix_hints": ["исправь вход и повтори вызов"],
  "elapsed_ms": 83
}
```

Ответ агента:

> 1) target='../no-such-folder':
> вход не прошёл валидацию: папка ../no-such-folder не существует
>
> 2) spec='rubrics/missing.yaml', target='.':
> файл рубрики rubrics/missing.yaml не найден

Характер ошибки различается: первая — про папку сдачи, вторая — про рубрику.
Агент получает разные тексты и может реагировать по-разному.

## Важная деталь: почему ошибка возвращается данными, а не бросается

Первый вариант сервера бросал `ValueError`. Реальный вызов выглядел так:

```
TOOL rubrica_rubrica_audit status=error
args={"target": "../no-such-folder"}
out: "Error executing tool rubrica_audit"
```

Причина отказа не доходила до агента вообще, и он сделал неверный вывод:
«сервер не подключился, ответа нет». После перехода на структурированный
ответ с полем `error` тот же вызов даёт конкретный текст проблемы.
Подробности — в [`docs/MCP.md`](../docs/MCP.md) и в
[`reflection.md`](../reflection.md).

## Проверка контракта ошибки тестом

```sh
.venv/bin/python -m unittest discover -s tests -t tests -k test_mcp_tool
```

Тесты `test_missing_target_returns_structured_error`,
`test_bad_spec_path_returns_structured_error`,
`test_invalid_rubric_content_returns_structured_error`,
`test_empty_target_returns_structured_error` и
`test_error_payload_has_same_shape_as_success` фиксируют это поведение.