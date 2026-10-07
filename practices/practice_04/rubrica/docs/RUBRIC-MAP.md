# Рубрика rubrica для практики 4

Одиннадцать правил, максимум 17 баллов. Шесть из них — блокеры: без них работу
не примут. Рубрика лежит в `rubrics/practice_04.yaml`, читается агентом через
skill `submission-audit`, применяется через CLI и через MCP-инструмент
`rubrica_audit`.

## Блокеры

| Правило | Что проверяет | Вес |
|---|---|---:|
| `agents_md_present` | есть `AGENTS.md` | 2 |
| `skill_defined` | есть `.opencode/skills/*/SKILL.md` | 2 |
| `hook_registered` | есть `.opencode/plugins/check-after-edit.js` | 2 |
| `mcp_server_declared` | в `opencode.json` есть `"rubrica"` | 2 |
| `mcp_source_present` | есть `mcp/rubrica_mcp/server.py` | 1 |
| `reflection_present` | есть `reflection.md` | 1 |

## Major

| Правило | Что проверяет | Вес |
|---|---|---:|
| `agents_md_names_check` | в `AGENTS.md` встречается `scripts/check.sh` | 2 |
| `runner_present` | есть `scripts/check.sh` | 1 |
| `evidence_transcripts` | минимум 3 файла `evidence/*.md` | 2 |

## Minor

| Правило | Что проверяет | Вес |
|---|---|---:|
| `skill_has_reference` | есть `.opencode/skills/*/references/*.md` | 1 |
| `no_stray_token` | в папке сдачи нет `.env` | 1 |

## Чего рубрика не проверяет

- Содержимое текстовых файлов, если это не выражено отдельным `file_contains`.
- Качество текста: рефлексия может быть пустой — `file_exists` скажет «есть».
- Токены внутри файлов — это делает предупреждение, а не правило.
- Поведение кода — этим занимается `scripts/check.sh`, а не аудит.

## Что сдаётся

```
rubrica/
├── AGENTS.md                      правила агента
├── docs/requirements.md           контракт
├── docs/style-guide.md            5 правил стиля для этого проекта
├── docs/HANDOFF.md                состояние для новой сессии
├── opencode.json                  модель, права skill, подключение MCP
├── Makefile                       install / check / audit
├── scripts/check.sh               runner, единственная точка проверки
├── scripts/mcp-server.sh          запуск MCP в stdio
├── src/rubrica/                   validate (A), spec, core, cli, narrative (B)
│   └── narrative.py добавлен фичей B
├── mcp/rubrica_mcp/server.py      собственный MCP-сервер
├── rubrics/practice_04.yaml       рубрика сдачи
├── tests/                         75 тестов
├── .opencode/skills/submission-audit/   skill + references + scripts
├── .opencode/plugins/check-after-edit.js  hook после правки
├── evidence/                      подтверждения применения
├── reflection.md                  рефлексия
└── submission.html                презентация с deeplink'ами
```