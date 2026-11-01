# E1 — применение AGENTS.md, skill и MCP в одной сессии

**Команда** (из корня `rubrica/`):

```sh
export VSELLM_API_KEY=...   # ключ из .env репозитория, в сдачу не попадает
opencode run --format json --model vsellm/openai/gpt-5 \
  --title "P4-E1 правила+skill+MCP" \
  "Прочитай AGENTS.md. Загрузи skill submission-audit и прочитай reference
   references/rubric-rules.md. Вызови MCP tool rubrica_audit с target='.' и
   spec='rubrics/practice_04.yaml'. Ничего не меняй."
```

Сырой поток событий: [`raw/E1-agents-skill-mcp.jsonl`](raw/E1-agents-skill-mcp.jsonl).
Ниже — только фактические вызовы инструментов из этого потока.

## Что реально вызвал агент

| Шаг | Инструмент | Аргументы | Статус |
|---|---|---|---|
| 1 | `read` | `AGENTS.md` | completed |
| 2 | `skill` | `{"name": "submission-audit"}` | completed |
| 3 | `read` | `.opencode/skills/submission-audit/references/rubric-rules.md` | completed |
| 4 | `rubrica_rubrica_audit` | `{"target": ".", "spec": "rubrics/practice_04.yaml"}` | completed |

Извлечено из потока:

```
TOOL read        status=completed  args={"filePath": ".../rubrica/AGENTS.md"}
TOOL skill       status=completed  args={"name": "submission-audit"}
TOOL glob        status=completed  args={"pattern": "**/references/rubric-rules.md"}  → No files found
TOOL read        status=completed  args={"filePath": ".../references/rubric-rules.md"}
TOOL rubrica_rubrica_audit status=completed args={"target": ".", "spec": "rubrics/practice_04.yaml"}
```

Имя инструмента в чате — `rubrica_rubrica_audit`: opencode добавляет к имени
инструмента имя MCP-сервера, поэтому сервер назван `rubrica`.

## Что агент извлёк из AGENTS.md

Цитата из ответа агента:

> 1) Путь к контракту и команда проверки из AGENTS.md
> - Контракт: docs/requirements.md
> - Команда проверки: sh scripts/check.sh

Оба значения совпадают с реальным содержимым файлов: контракт действительно
`docs/requirements.md`, и `sh scripts/check.sh` действительно проходит
(`Ran 74 tests … OK`). Агент не выдумал команду — он её прочитал в правилах
и затем ей пользовался в других сессиях (см. [E4](E4-hook-pass-by-rule.md)).

## Что агент извлёк из reference

> 2) Правила рубрики из reference references/rubric-rules.md
> - Блокеры: agents_md_present (2), skill_defined (2), hook_registered (2),
>   mcp_server_declared (2), mcp_source_present (1), reflection_present (1)
> - Major: agents_md_names_check (2), runner_present (1), evidence_transcripts (2)
> - Minor: skill_has_reference (1), no_stray_token (1)

Это в точности содержимое `.opencode/skills/submission-audit/references/rubric-rules.md`:
11 правил, сумма весов 17. Агент перечислил 11, с теми же severity и весами.

## Что вернул MCP tool

Ответ `rubrica_audit` (усечён по findings):

```json
{
  "spec": "practice_04",
  "spec_title": "Практика 4 — среда агента, skill и собственный MCP",
  "target": ".../practices/practice_04/rubrica",
  "score": 14, "max_score": 17, "passed": 9, "failed": 2, "blockers": 1,
  "exit_code": 2,
  "findings": [
    {"rule": "agents_md_present", "ok": true, "detail": "файл AGENTS.md на месте"},
    {"rule": "agents_md_names_check", "ok": true, "detail": "AGENTS.md: совпадение 'scripts/check\\.sh' в строке 17"},
    {"rule": "evidence_transcripts", "ok": false, "detail": "нужно минимум 3 файлов по evidence/*.md, найдено 0"},
    {"rule": "reflection_present", "ok": false, "detail": "файл reflection.md не найден"}
  ],
  "fix_hints": [
    "сначала закрой 1 blocker'ов, остальное потом",
    "добавь файлы: приложены подтверждения применения инструментов",
    "создай рефлексия написана — файл отсутствует"
  ],
  "ok": false, "elapsed_ms": 12527
}
```

## Что это доказывает

В одной сессии агент применил все три подключения по отдельности: правила
(прочитал и назвал контракт и runner), skill (загрузил через инструмент `skill`
и прочитал связанный reference), MCP (вызвал tool и получил структурированный
вердикт). Ни одно из подключений не присутствует «просто файлом на диске» —
каждое использовано инструментом и дало результат, который агент процитировал.

Провалы в отчёте — не дефект среды: на момент прогона ещё не существовали
`reflection.md` и `evidence/`. Финальный прогон даёт 17/17, см. [E7](E7-final-audit.md).