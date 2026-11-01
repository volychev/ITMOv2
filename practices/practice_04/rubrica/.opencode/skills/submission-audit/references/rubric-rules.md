name: rubric-rules
description: Правила рубрики practice_04 — что именно проверяет каждое правило, какой у него severity и вес. Нужен, когда агент или человек хочет понять, почему аудит не даёт полный балл.
license: MIT
compatibility: opencode
metadata:
  audience: student
  audience_note: тот же список лежит в rubrics/practice_04.yaml, этот файл — читаемая копия

# Правила рубрики practice_04

Рубрика: `rubrics/practice_04.yaml`, 11 правил, максимум 17 баллов.

## Блокеры (без них сдача не принимается)

| Правило | Что проверяет | Вес |
|---|---|---:|
| `agents_md_present` | есть `AGENTS.md` | 2 |
| `skill_defined` | есть `.opencode/skills/*/SKILL.md` | 2 |
| `hook_registered` | есть `.opencode/plugins/check-after-edit.js` | 2 |
| `mcp_server_declared` | в `opencode.json` есть секция `"rubrica"` | 2 |
| `mcp_source_present` | есть `mcp/rubrica_mcp/server.py` | 1 |
| `reflection_present` | есть `reflection.md` | 1 |

## Major (потеря баллов, но работа принимается)

| Правило | Что проверяет | Вес |
|---|---|---:|
| `agents_md_names_check` | в `AGENTS.md` встречается `scripts/check.sh` | 2 |
| `runner_present` | есть `scripts/check.sh` | 1 |
| `evidence_transcripts` | минимум 3 файла `evidence/*.md` | 2 |

## Minor (аккуратность)

| Правило | Что проверяет | Вес |
|---|---|---:|
| `skill_has_reference` | есть `.opencode/skills/*/references/*.md` | 1 |
| `no_stray_token` | в папке сдачи нет файла `.env` | 1 |

## Как это читать

Блокеров 6, и они закрываются наличием файлов, а не содержанием. Проверка
`file_exists` не смотрит внутрь файла — если нужно, чтобы в файле было
осмысленное содержимое, добавь отдельное правило `file_contains`.

Именно поэтому `agents_md_present` и `agents_md_names_check` — два разных
правила: первое требует файл, второе требует, чтобы в нём была названа
настоящая команда проверки.

Рубрика лежит в репозитории и проверяется тестом
`test_shipped_rubric_is_valid`. Правка рубрики без правки этого документа
приведёт к расхождению, поэтому меняй оба.