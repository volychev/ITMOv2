# Implementation Plan: Автономный HTML-отчёт аудита

**Branch**: `001-html-report` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-html-report/spec.md`

## Summary

Добавить в CLI `rubrica` необязательный флаг `--html PATH`, который пишет один
самодостаточный HTML-файл из того же `Report`, что текст и JSON. Отчёт содержит
шапку с вердиктом, все находки, предупреждения и рецензию; поиск, фильтр по
severity, «только провалы», сортировка и сброс работают на встроенном vanilla
JS. Реализация — новый модуль `src/rubrica/report_html.py` на стандартной
библиотеке, минимальная правка `cli.py`, новые тесты через публичные
интерфейсы. Существующие `core.py`, `validate.py`, `spec.py`, `narrative.py`
не меняются; поведение без `--html` и коды возврата сохраняются.

## Technical Context

**Language/Version**: Python >= 3.11 (в репозитории `.venv` — 3.14.8)

**Primary Dependencies**: стандартная библиотека (`argparse`, `dataclasses`,
`html`, `os`, `tempfile`, `pathlib`); существующий `pyyaml`. Новых зависимостей
нет.

**Storage**: локальная файловая система; вход — папка сдачи и YAML-рубрика,
выход — один HTML-файл.

**Testing**: `unittest`, запуск только через `sh scripts/check.sh`
(`compileall` + весь набор тестов). Точечно:
`.venv/bin/python -m unittest discover -s tests -t tests -k test_report_html`.

**Target Platform**: CLI в Linux/macOS/Windows; HTML открывается в актуальных
Chrome/Firefox/Safari/Edge по `file://`.

**Project Type**: single project, CLI-утилита.

**Performance Goals**: фильтрация/сортировка 200 находок — < 100 мс в браузере;
рендер и запись — доли секунды; размер файла — единицы МБ в худшем случае.

**Constraints**: офлайн, без внешних CSS/JS/шрифтов; детерминированный
байт-идентичный HTML; `0600` на файл; атомарная запись; без сети без
`--narrative`; существующие коды 0/1/2/3 не переписываются.

**Scale/Scope**: до 200 правил рубрики, до 500 в `--max-findings` (только
текстовый stdout), один пользователь, один отчёт за запуск.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Проверка | Статус |
|---|---|---|
| I. Контракт важнее кода | спека и `contracts/ui-logic.md` приняты до кода; `docs/requirements.md` обновляется в том же изменении | PASS |
| II. Проверка через публичный интерфейс | тесты через `build_view`, `render_html`, `export_html`, `main`; runner не меняется | PASS |
| III. Ошибка зависимости не меняет вердикт | `report_html` не знает о сети; `core.py` не меняется; `narrative_error` только отображается | PASS |
| IV. Минимум зависимостей и детерминизм | только stdlib; нет времени/случайности; байтовая воспроизводимость | PASS |
| V. Безопасность и честные сообщения | `html.escape`, проверка пути, запрет симлинка-цели, сообщения с путём и причиной | PASS |

Нарушений нет; Complexity Tracking не заполняется.

## Project Structure

### Documentation (this feature)

```text
specs/001-html-report/
├── spec.md                  # консолидированная спека (Spec Kit)
├── plan.md                  # этот файл
├── research.md              # решения и альтернативы
├── data-model.md            # ReportView / FindingView / состояния
├── quickstart.md            # сценарии проверки
├── tasks.md                 # задачи реализации
├── checklists/requirements.md
├── contracts/ui-logic.md    # общий контракт двух команд
└── teams/
    ├── ui/spec-before.md
    ├── ui/spec-after.md
    ├── logic/spec-before.md
    └── logic/spec-after.md
```

### Source Code (repository root)

```text
src/rubrica/
├── __init__.py
├── cli.py                   # + --html, ранняя валидация пути, вызов export_html
├── core.py                  # без изменений
├── narrative.py             # без изменений
├── report_html.py           # НОВЫЙ: view model, render, resolve, atomic write
├── spec.py                  # без изменений
└── validate.py              # без изменений

tests/
├── test_report_html.py      # НОВЫЙ: модель, рендер, путь, запись, детерминизм
├── test_cli_html.py         # НОВЫЙ: CLI e2e, коды 0/1/2/3, JSON+HTML
└── test_*.py                # существующие 74 теста без изменений

docs/
├── requirements.md          # + контракт --html
├── HANDOFF.md               # + состояние фичи C
└── sdd-comparison.md        # НОВЫЙ: Spec Kit vs OpenSpec

README.md                    # + раздел про HTML-отчёт
evidence/                    # + подтверждения запуска и скриншот
```

**Structure Decision**: single project. Новый слой `report_html.py` отделён от
`core.py` (аудит) и `narrative.py` (сеть); CLI только связывает их. Тесты
публичных интерфейсов лежат рядом с существующими, без новых фреймворков.

## Phase 0: Research

См. [research.md](research.md). Все неизвестные закрыты: способ рендера,
модель представления, атомарная запись, валидация пути, детерминизм, границы
с `--max-findings`, `--json` и `--narrative`.

## Phase 1: Design & Contracts

- [data-model.md](data-model.md) — `ReportView`, `FindingView`, состояния
  экрана, инварианты и отображение `Report` → view.
- [contracts/ui-logic.md](contracts/ui-logic.md) — CLI, путь, данные, Python-
  контракт, HTML, коды возврата и сквозная приёмка.
- [quickstart.md](quickstart.md) — runnable-сценарии проверки.

## Phase 2: Tasks

См. [tasks.md](tasks.md). Порядок: тесты → модуль → CLI → документация →
сквозная проверка. Реализация начинается только после приёмки спеки и
контракта человеком.

## Post-Design Constitution Check

После проектирования повторно проверено:

- `ReportView` не мутирует `Report`, рендер чистый, запись атомарная — принцип I
  и IV соблюдены.
- Все проверки идут через публичные функции и `main` — принцип II.
- `report_html` не импортирует сетевые модули, `narrative` остаётся
  единственной точкой сети — принцип III.
- Динамические строки экранируются, путь проверяется, symlink-цель
  отклоняется — принцип V.
- Новых зависимостей и изменений в `core.py`/`validate.py`/`spec.py`/
  `narrative.py` нет.

## Complexity Tracking

Нарушений конституции нет. Дополнительные слои не вводятся: один новый модуль
и два тестовых файла.
