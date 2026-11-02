# Tasks

## 1. Модель и запись

- [ ] 1.1 Добавить тесты `build_view` в `tests/test_report_html.py`: счётчики,
  порядок, все находки, `warnings`, `narrative`/`narrative_error`; запуск
  `unittest -k test_report_html` зелёный.
- [ ] 1.2 Реализовать `ExportRejected`, `FindingView`, `ReportView`,
  `build_view` в `src/rubrica/report_html.py`; тесты 1.1 проходят.
- [ ] 1.3 Добавить тесты пути и записи: пустой путь, `.txt`, каталог,
  отсутствующий родитель, symlink, права `0600`, ошибка `os.replace`.
- [ ] 1.4 Реализовать `resolve_output_path` и `write_atomic`; тесты 1.3
  проходят, временный файл при ошибке удалён.

## 2. Рендер и CLI

- [ ] 2.1 Добавить тесты `render_html`: каркас, шапка, метрики, находки,
  PASS/FAIL, severity, вес; `unittest -k test_report_html` зелёный.
- [ ] 2.2 Реализовать `render_html` с inline CSS/JS, баннерами 0/1/2 и блоком
  рецензии; тесты 2.1 проходят.
- [ ] 2.3 Добавить CLI e2e в `tests/test_cli_html.py`: `--html`, `--json
  --html`, `--max-findings`, коды 0/1/2/3, ранение отказы пути; тесты падают до
  реализации.
- [ ] 2.4 Подключить `--html` в `src/rubrica/cli.py`: argparse, проверка пути
  после `validate_all`, экспорт после печати, stderr-подтверждение, код 2 при
  ошибке; все тесты 2.3 проходят.

## 3. Интерактивность и безопасность

- [ ] 3.1 Добавить тесты разметки фильтров и data-атрибутов, доступности и
  отсутствия внешних ресурсов; `unittest -k test_report_html` зелёный.
- [ ] 3.2 Реализовать поиск, severity, «только провалы», пять сортировок,
  сброс, счётчик и пустые состояния; тесты 3.1 проходят.
- [ ] 3.3 Добавить тесты экранирования (`<script>`, `"><img onerror=...>`),
  CSP и детерминизма; тесты проходят.
- [ ] 3.4 Проверить отчёт в браузере по `quickstart.md` §3 и сохранить
  скриншот в `evidence/artifacts/`; фильтры и сброс работают без ошибок
  консоли.

## 4. Документация и приёмка

- [ ] 4.1 Обновить `docs/requirements.md`: вход, `--html`, совместимость,
  коды, формат HTML; `make audit` остаётся 17/17.
- [ ] 4.2 Обновить `README.md`, `AGENTS.md`, `docs/HANDOFF.md`,
  `docs/RUBRIC-MAP.md`, `docs/style-guide.md`; ссылки и числа тестов совпадают
  с фактическими.
- [ ] 4.3 Прогнать `sh scripts/check.sh` и `make audit`; зафиксировать 113
  тестов и 17/17 в evidence.
- [ ] 4.4 Выполнить `quickstart.md` целиком, записать фактические коды,
  ошибки пути и детерминизм в `evidence/E8-html-report.md`.
- [ ] 4.5 Проверить `git diff` на секреты и лишние файлы, сделать коммит;
  `git status` чистый.

## Workflow follow-up

- Сравнить процесс с OpenSpec 1.14.1 и записать выводы в
  `docs/sdd-comparison.md`.
