# Data Model: автономный HTML-отчёт

**Фича**: `001-html-report` · **Дата**: 2026-11-02
**Источник**: `spec.md`, `contracts/ui-logic.md`, `src/rubrica/core.py`

## Сущности

### FindingView

Одна находка аудита, пригодная для рендера. Не содержит объектов `Path` и
ссылок на `Report`.

| Поле | Тип | Источник | Правило |
|---|---|---|---|
| `rule` | `str` | `Finding.rule_id` | непустой id правила |
| `kind` | `str` | `Finding.kind` | один из `file_exists`, `file_missing`, `file_contains`, `dir_count` |
| `severity` | `str` | `Finding.severity` | `blocker`, `major`, `minor` |
| `ok` | `bool` | `Finding.ok` | PASS/FAIL |
| `title` | `str` | `Finding.title` | может быть пустым → показывается rule id |
| `detail` | `str` | `Finding.detail` | человекочитаемое объяснение |
| `weight` | `int` | `Finding.weight` | 1..10 |

### ReportView

Неизменяемая модель всего отчёта.

| Поле | Тип | Источник | Правило |
|---|---|---|---|
| `spec_id` | `str` | `Report.spec_id` | как есть |
| `spec_title` | `str` | `Report.spec_title` | как есть |
| `target` | `str` | `Report.target` | уже разрешённый путь |
| `score` | `int` | `Report.score` | сумма весов PASS |
| `max_score` | `int` | `Report.max_score` | сумма весов всех правил |
| `passed` | `int` | `len(Report.passed)` | количество |
| `failed` | `int` | `len(Report.failed)` | количество |
| `blockers` | `int` | `len(Report.blockers)` | количество |
| `exit_code` | `int` | `Report.exit_code` | только 0/1/2 |
| `findings` | `tuple[FindingView, ...]` | `Report.findings` | все, порядок рубрики |
| `warnings` | `tuple[str, ...]` | `Report.warnings` | исходный порядок |
| `narrative` | `str \| None` | аргумент CLI | как в JSON, без обрезки |
| `narrative_error` | `str \| None` | аргумент CLI | как в JSON, без обрезки |

### Экранные состояния

| Состояние | Условие | Отображение | Код процесса |
|---|---|---|---:|
| Успех | `exit_code == 0` | зелёный баннер «Все правила пройдены» | 0 |
| Провалы | `exit_code == 1` | жёлтый баннер «Есть провалы без блокеров» | 1 |
| Блокер | `exit_code == 2` | красный баннер «Есть блокирующие провалы» | 2 |
| Рецензия недоступна | `narrative_error is not None` | бейдж + текст ошибки + «Результат аудита не изменён» | 3 |
| Рецензия не запрашивалась | `narrative is None and narrative_error is None` | «Рецензия не запрашивалась» | как аудит |
| Нет совпадений | фильтры дали 0 | «Ничего не найдено…», `Показано 0 из M` | как аудит |
| Нет провалов при фильтре | «только провалы», `failed == 0` | «Провалов нет» | как аудит |
| Пустой отчёт | `findings == ()` | «Находок нет», `0/0` | 0 |

## Инварианты

1. `0 <= score <= max_score`.
2. `passed + failed == len(findings)` (HTML не режется лимитом).
3. `0 <= blockers <= failed`.
4. `exit_code == Report.exit_code`; 3 формируется только в CLI и не попадает
   в метрики отчёта.
5. `findings` сохраняет порядок `Report.findings`; сортировка — клиентская.
6. `build_view` не мутирует `Report`; повторный вызов даёт равные значения.
7. Нет `generated_at`, `hidden_findings`, случайных id.
8. `render_html(view)` — чистая функция: одинаковый view → одинаковая строка.
9. Все динамические строки экранированы; в атрибутах только контролируемые
   значения.
10. `narrative` и `narrative_error` побайтно совпадают с JSON-полями.

## Отображение `Report` → `ReportView`

```text
Report(spec_id, spec_title, target,
       findings: list[Finding], warnings: list[str])
        │
        ├── счётчики: len(passed), len(failed), len(blockers)
        ├── score / max_score / exit_code — как есть
        ├── findings → tuple(FindingView(...) для каждого)
        ├── warnings → tuple(...)
        └── narrative / narrative_error — из аргументов CLI
        ↓
ReportView → render_html() → строка → write_atomic() → Path
```

## Правила валидации пути

| Вход | Результат |
|---|---|
| `""` / пробелы | `ExportRejected("--html: путь не указан")` |
| `report.txt` / без расширения | `ExportRejected("нужен файл .html или .htm")` |
| существующий каталог | `ExportRejected("это каталог, нужен файл")` |
| родителя нет | `ExportRejected("родительская папка ... не существует")` |
| родитель — файл | `ExportRejected("родитель ... не каталог")` |
| цель — symlink | `ExportRejected("укажите реальный путь")` |
| родитель — symlink | разрешено, `resolve()` |
| существующий файл | перезапись атомарно |
| внутри `target` | разрешено |
| пробелы в PATH отчёта | разрешены |
| относительный путь | от текущего каталога, вернуть абсолютный |

## Что не входит в модель

- Время генерации, версия `rubrica`, хост, пользователь.
- Скрытые/отфильтрованные находки.
- Результаты будущих запусков и история.
- Настройки темы/фильтров между открытиями.
