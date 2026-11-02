# Tasks: Автономный HTML-отчёт аудита

**Input**: Design documents from `specs/001-html-report/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/ui-logic.md](contracts/ui-logic.md)

**Tests**: включены, потому что спека и style guide требуют проверок через
публичный интерфейс. Тесты пишутся до реализации и должны падать.

**Organization**: задачи сгруппированы по пользовательским историям; P1 — MVP.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: зафиксировать базу и границы до правок.

- [x] T001 Проверить baseline: `sh scripts/check.sh` (74 теста) и `make audit` зелёные; записать результат в `evidence/E8-html-report.md`
- [x] T002 [P] Зафиксировать границы: `core.py`, `validate.py`, `spec.py`, `narrative.py`, `scripts/check.sh`, `rubrics/practice_04.yaml` не меняются
- [x] T003 [P] Проверить, что новых зависимостей нет: `pyproject.toml` не меняется, HTML/CSS/JS — stdlib и inline

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: модель, путь и атомарная запись, без которых не работает ни одна
история.

**⚠️ CRITICAL**: до завершения этой фазы UI-истории не реализуются.

### Tests first

- [x] T004 [P] Тесты модели в `tests/test_report_html.py`: `build_view` сохраняет счётчики, порядок, все находки, `warnings`, `narrative`/`narrative_error`; не мутирует `Report`; нет `generated_at`/`hidden_findings`
- [x] T005 [P] Тесты пути и записи в `tests/test_report_html.py`: пустой путь, `.txt`, каталог, отсутствующий/некаталоговый родитель, symlink-цель, успешная запись, перезапись, права `0600`, атомарность при mock `os.replace`

### Implementation

- [x] T006 [US1] Создать `src/rubrica/report_html.py`: `ExportRejected`, `FindingView`, `ReportView`, `build_view`
- [x] T007 [US1] Реализовать `resolve_output_path` по таблице контракта
- [x] T008 [US1] Реализовать `write_atomic` (mkstemp → UTF-8 → flush → fsync → os.replace, cleanup, `0600`)

**Checkpoint**: модель и запись готовы; можно рендерить и подключать CLI.

---

## Phase 3: User Story 1 — Сгенерировать и открыть отчёт (Priority: P1) 🎯 MVP

**Goal**: `rubrica <target> --html PATH` создаёт автономный HTML-файл, метрики
и находки совпадают с JSON.

**Independent Test**: запустить CLI на текущей папке, открыть файл, сверить
score/max и rule id с `--json`.

### Tests for User Story 1

- [x] T009 [P] [US1] Тест `render_html` в `tests/test_report_html.py`: `<!DOCTYPE html>`, `lang="ru"`, charset, шапка, метрики, все находки, PASS/FAIL, severity, вес
- [x] T010 [P] [US1] CLI e2e в `tests/test_cli_html.py`: `--html` создаёт файл, stdout прежний, stderr содержит путь, код 0
- [x] T011 [P] [US1] CLI e2e в `tests/test_cli_html.py`: `--json --html` — stdout валидный JSON прежней схемы, файл есть; `--max-findings 1` не режет HTML

### Implementation for User Story 1

- [x] T012 [US1] Реализовать `render_html`: HTML5-каркас, inline CSS, шапка, баннер, список находок, предупреждения, подвал
- [x] T013 [US1] Реализовать `export_html`: `resolve_output_path` → `build_view` → `render_html` → `write_atomic`
- [x] T014 [US1] Подключить `--html` в `src/rubrica/cli.py`: argparse, ранняя валидация после `validate_all`, вызов после аудита, stderr-подтверждение, маппинг ошибок в код 2
- [x] T015 [US1] Обновить `docs/requirements.md`: вход, `--html`, совместимость с `--json`/`--max-findings`, коды, формат HTML
- [x] T016 [P] [US1] Обновить `README.md`: раздел «HTML-отчёт» с примером и ограничениями

**Checkpoint**: MVP работает; можно показывать HTML и сверять с JSON.

---

## Phase 4: User Story 2 — Найти нужную находку (Priority: P2)

**Goal**: поиск, фильтр severity, «только провалы», сортировка и сброс
работают в браузере; без JS страница остаётся полной.

**Independent Test**: открыть отчёт с ≥ 5 находками и пройти сценарии из
`quickstart.md` §3.

### Tests for User Story 2

- [x] T017 [P] [US2] Тест разметки в `tests/test_report_html.py`: есть `type="search"`, селект severity, чекбокс, селект сортировки, кнопка сброса, счётчик с `aria-live`, `data-severity`/`data-ok`/`data-weight`/`data-search` у находок
- [x] T018 [P] [US2] Тест доступности/офлайна: у контролов есть `<label for>`, `lang="ru"`, нет `<link>`, `<script src>`, `<img src>`, `@import`, `url(`, `http://`, `https://`

### Implementation for User Story 2

- [x] T019 [US2] Добавить панель действий и data-атрибуты в `render_html`
- [x] T020 [US2] Реализовать vanilla-JS: casefold-поиск, AND-фильтры, устойчивая сортировка, сброс, счётчик, пустые состояния
- [x] T021 [US2] Добавить CSS: читаемая типографика, контраст, видимый фокус, адаптивность, `prefers-reduced-motion`, print
- [x] T022 [US2] Проверить в браузере по `quickstart.md` §3 и сохранить скриншот в `evidence/`

**Checkpoint**: отчёт удобен для 200 правил; без JS не ломается.

---

## Phase 5: User Story 3 — Понять вердикт и деградацию (Priority: P3)

**Goal**: баннеры 0/1/2, бейдж недоступной рецензии, три состояния рецензии,
коды возврата.

**Independent Test**: сгенерировать четыре отчёта (pass/fail/blocker/narrative
unavailable) и сверить баннеры и коды.

### Tests for User Story 3

- [x] T023 [P] [US3] Тест вердиктов в `tests/test_report_html.py`: тексты и классы баннеров для 0/1/2, выделение blocker
- [x] T024 [P] [US3] CLI e2e в `tests/test_cli_html.py`: pass → 0, major fail → 1, blocker → 2, `--narrative` с mock `NarrativeUnavailable` → 3 и HTML записан
- [x] T025 [P] [US3] Тест трёх состояний рецензии: не запрашивалась / получена / недоступна; ошибка не меняет метрики

### Implementation for User Story 3

- [x] T026 [US3] Реализовать баннеры, бейдж деградации и блок рецензии в `render_html`
- [x] T027 [US3] Связать `narrative`/`narrative_error` с `build_view`/`export_html` в `cli.py`
- [x] T028 [US3] Проверить приоритет кодов: ошибка экспорта → 2 даже при `narrative_error`; без `--html` — прежние коды

**Checkpoint**: вердикт читается за секунду, деградация не выглядит провалом.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: безопасность, детерминизм, документация, доказательства, сравнение
с OpenSpec.

- [x] T029 [P] Тесты безопасности в `tests/test_report_html.py`: `<script>`, `"><img onerror=...>`, кавычки в title/detail/warnings/narrative выводятся как текст; CSP присутствует
- [x] T030 [P] Тест детерминизма: два `render_html` и два CLI-запуска дают идентичные байты
- [x] T031 [P] Тест ошибочного входа и границ: все отказы пути → `ExportRejected`, файл не создан, temp удалён; ошибка записи не портит старый файл
- [x] T032 Обновить `docs/HANDOFF.md`, `AGENTS.md` (границы фичи C), `docs/RUBRIC-MAP.md` при необходимости
- [x] T033 Прогнать `quickstart.md` целиком; записать фактические коды и выводы в `evidence/E8-html-report.md`
- [x] T034 Запустить `sh scripts/check.sh` и `make audit`; зафиксировать числа тестов и баллов
- [x] T035 [P] Сделать реальный baseline OpenSpec 1.14.1 в отдельном временном worktree; сохранить артефакты и транскрипт в `evidence/openspec-baseline/`
- [x] T036 [P] Написать `docs/sdd-comparison.md`: Spec Kit vs OpenSpec, что совпало/разошлось, что дал каждый
- [x] T037 [P] Написать `specs/001-html-report/reflection.md`: что согласовали, где вмешался человек, чему научились
- [x] T038 Проверить, что `git diff` не содержит секретов, `.env`, `.venv`, `node_modules`; сделать коммит

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: без зависимостей.
- **Foundational (Phase 2)**: после Setup; блокирует все истории.
- **US1 (Phase 3)**: после Foundational.
- **US2 (Phase 4)**: после US1 (нужен готовый HTML-каркас), но проверяется отдельно.
- **US3 (Phase 5)**: после US1; может идти параллельно US2, если не конфликтует по `render_html`.
- **Polish (Phase 6)**: после US1–US3.

### Within Each Story

- Тесты → падение → реализация → зелёный прогон.
- Модель → рендер → запись → CLI.
- После каждой истории — `sh scripts/check.sh`.
- Не менять runner, рубрику и чужие фичи.

### Parallel Opportunities

- T004/T005 — разные аспекты одного файла тестов; писать последовательно, но
  можно разделить по классам.
- T009/T010/T011 — разные файлы тестов.
- T017/T018 — разные проверки разметки.
- T023/T024/T025 — разные уровни.
- T029/T030/T031 — разные классы тестов.
- T035/T036/T037 — после реализации, разные файлы.

## Implementation Strategy

### MVP First

1. Phase 1 → Phase 2 → US1.
2. **STOP and VALIDATE**: сгенерировать HTML, сверить с JSON, показать человеку.
3. Только потом US2/US3.

### Incremental Delivery

1. Модель + запись + CLI + базовый HTML (US1).
2. Интерактивность (US2).
3. Вердикты и деградация (US3).
4. Безопасность, детерминизм, документация, сравнение (Polish).

## Notes

- `[P]` — задачи, которые не конфликтуют по файлам.
- `[US*]` — трассировка к историям из `spec.md`.
- Тесты проверяют публичные интерфейсы, а не внутренние helper'ы.
- `sh scripts/check.sh` — единственная доверенная проверка.
- Реализация не начинается до приёмки `spec.md` и `contracts/ui-logic.md`
  человеком.
