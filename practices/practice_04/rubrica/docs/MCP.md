# Собственный MCP: rubrica_audit

Один tool, локальный stdio-сервер. Исходники: [`../mcp/rubrica_mcp/server.py`](../mcp/rubrica_mcp/server.py),
запуск: [`../scripts/mcp-server.sh`](../scripts/mcp-server.sh).

## Зачем он здесь

Ревьюверу и агенту нужен один вопрос: «что в папке сдачи ещё не соответствует
рубрике». Через CLI это отдельный терминал и отдельная команда. Через MCP это
один вызов из чата с ответом в виде структурированного JSON, который агент
может разобрать и на основании которого сразу править файлы.

Подключение в [`../opencode.json`](../opencode.json):

```json
"mcp": {
  "rubrica": {
    "type": "local",
    "command": ["sh", "scripts/mcp-server.sh"],
    "enabled": true,
    "environment": {}
  }
}
```

Скрипт-обёртка вычисляет корень проекта от своего расположения, поэтому
конфиг не зависит от того, из какой директории запущен opencode.

Проверка подключения:

```sh
opencode mcp list
#  ●  ✓ rubrica connected
#         sh scripts/mcp-server.sh
```

В чате инструмент называется `rubrica_rubrica_audit`: opencode добавляет к
имени инструмента имя MCP-сервера.

## Устройство

```
FastMCP/MCPServer "rubrica"          mcp/rubrica_mcp/server.py
  └── tool rubrica_audit(target, spec="")
        ├── validate_all(target, spec)        src/rubrica/validate.py   фича A
        ├── _resolve_spec(spec)               рубрика или умолчание
        ├── load_spec(spec_path)              src/rubrica/spec.py
        ├── audit(spec, target)               src/rubrica/core.py
        └── _hints(report)                    что чинить в первую очередь
```

Tool ничего не знает про правила, веса и секреты — всё это внутри `rubrica`.
MCP-слой отвечает только за формат ответа и за понятную ошибку.

## Контракт ответа

Успех:

| Поле | Значение |
|---|---|
| `ok` | `exit_code == 0` |
| `score` / `max_score` | баллы и максимум |
| `exit_code` | 0/1/2 — код аудита |
| `findings[]` | по правилу: `rule`, `kind`, `severity`, `ok`, `title`, `detail`, `weight` |
| `warnings[]` | предупреждения, в том числе о найденных токенах |
| `fix_hints[]` | что делать по порядку |
| `spec_path` | какая рубрика применена |
| `elapsed_ms` | время расчёта |

Ошибка входа имеет тот же набор полей: `ok: false`, `error` с текстом
причины, `findings: []`, `score: 0`, `fix_hints` с одной подсказкой.

## Ошибочный вход

Сначала tool бросал `ValueError`. Реальный вызов в opencode выглядел так:

```
TOOL rubrica_rubrica_audit status=error
out: "Error executing tool rubrica_audit"
```

Причина отказа не доходила до агента, и агент сделал неверный вывод, что
сервер не подключён. После перехода на структурированный ответ тот же вызов
даёт конкретный текст:

```json
{
  "ok": false,
  "error": "вход не прошёл валидацию: папка ../no-such-folder не существует",
  "target": "../no-such-folder",
  "fix_hints": ["исправь вход и повтори вызов"]
}
```

Фактические вызовы обоих сценариев — в
[`../evidence/E2-mcp-error-input.md`](../evidence/E2-mcp-error-input.md).

## Тесты

`tests/test_mcp_tool.py` — 9 тестов: успешный аудит, частичный аудит,
четыре вида ошибок входа, совпадение формы ответа при ошибке и успехе,
предупреждение о секрете, умолчание на `rubrics/practice_04.yaml`.

## Почему один tool

Количество подключений не добавляет баллов. Один инструмент, который
покрывает вопрос «готов ли я к сдаче», полезнее трёх, которые покрывают
половину шагов аудита. Второй tool (`rubrica_explain`) задумывался, но
разбирать отчёт по правилам умеет уже `rubrica_audit` через `findings` и
`fix_hints` — дублировать нечего.