# E8 — HTML-отчёт (фича C)

Подтверждение работы фичи `--html`: тесты, ручные сценарии, браузер, OpenSpec
baseline. Контракт — [`docs/requirements.md`](../docs/requirements.md), спека —
[`specs/001-html-report/spec.md`](../specs/001-html-report/spec.md).

## 1. Baseline и итог

```sh
# до фичи
sh scripts/check.sh     # 74 теста, OK
make audit              # 17/17, exit 0

# после фичи
sh scripts/check.sh     # 113 тестов, OK
make audit              # 17/17, exit 0
```

Новые тесты: `tests/test_report_html.py` (23) и `tests/test_cli_html.py` (16).
Прежние 74 не менялись.

## 2. Генерация и сверка с JSON

```sh
.venv/bin/rubrica . --spec rubrics/practice_04.yaml \
  --json --html /tmp/opencode/rubrica-report-json.html > /tmp/opencode/rubrica.json
```

- exit 0;
- stdout — валидный JSON прежней схемы (17/17, 11 правил), поля `html` нет;
- stderr — `HTML-отчёт: /tmp/opencode/rubrica-report-json.html`;
- проверка согласованности: `HTML и JSON согласованы: 17 / 17; правил: 11`.

## 3. Браузер

Отчёт с шестью находками (3 PASS, 3 FAIL, 1 blocker) открыт по HTTP,
`console` — ошибок нет. Сценарии из `quickstart.md` §3:

| Действие | Ожидание | Факт |
|---|---|---|
| поиск `readme` | 1 находка | `Показано 1 из 6`, `has_readme` |
| `severity=blocker` + «только провалы» | только проваленный blocker | `Показано 1 из 6`, `has_tests` |
| сортировка «провалы сначала» | FAIL выше PASS | `has_changelog`, `has_tests`, `has_docs`, затем PASS |
| сортировка «вес» | больший вес выше | `has_tests` (3), далее вес 2, затем 1 |
| «Сбросить» | исходный порядок рубрики | 6 из 6 в порядке рубрики |
| запрос `zzz-none` | пустое состояние | `Показано 0 из 6`, «Ничего не найдено…»; метрики шапки не изменились |

Скриншот: [`artifacts/html-report-demo.jpeg`](artifacts/html-report-demo.jpeg).
Сам отчёт: [`artifacts/html-report-demo.html`](artifacts/html-report-demo.html).
Без JS панель фильтров скрыта через `.controls { display: none }` и класс `js`,
который добавляет скрипт; список находок и остальные секции остаются в HTML.

## 4. Вердикты и коды

| Сценарий | Код | Проверка |
|---|---:|---|
| всё проходит | 0 | баннер «Все правила пройдены» |
| провал без блокера | 1 | баннер «Есть провалы без блокеров» |
| блокер | 2 | баннер «Есть блокирующие провалы», HTML записан |
| рецензия недоступна | 3 | бейдж «Рецензия недоступна», баллы не изменились |
| ошибка записи | 2 | stdout уже напечатан, stderr — причина |

## 5. Ошибки пути (до аудита)

```text
no-parent code=2
ОТКАЗ: HTML-отчёт не записан — --html: родительская папка /tmp/opencode/no-such-dir не существует

ext code=2
ОТКАЗ: HTML-отчёт не записан — --html: нужен файл .html или .htm, получено '.txt'

dir code=2
ОТКАЗ: HTML-отчёт не записан — --html: /tmp — это каталог, нужен путь к файлу

empty code=2
ОТКАЗ: HTML-отчёт не записан — --html: путь не указан
```

`audit` при этих отказах не вызывается — это закреплено тестами с `mock.patch`.

## 6. Детерминизм

```sh
.venv/bin/rubrica . --spec rubrics/practice_04.yaml --html /tmp/opencode/a.html
.venv/bin/rubrica . --spec rubrics/practice_04.yaml --html /tmp/opencode/b.html
cmp /tmp/opencode/a.html /tmp/opencode/b.html && echo "детерминизм: ok"
# детерминизм: ok
```

## 7. Безопасность и запись

- Все динамические строки проходят через `html.escape`; тесты подставляют
  `<script>` и `"><img onerror=...>` в title/detail/warnings/narrative.
- CSP: `default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';
  img-src data:`; внешних `<link>`, `<script src>`, `<img src>`, `@import`,
  `url(` и `http(s)://` в файле нет.
- Запись: `mkstemp` в целевой папке → UTF-8 → `flush` → `fsync` → `chmod 0600`
  → `os.replace`; при `OSError` временный файл удаляется, прежний не трогается.
- На рабочем NTFS-монтировании POSIX-права не сохраняются (файл виден как 755);
  тест прав `0600` выполняется в `/tmp`, где режим поддерживается. Это
  ограничение среды, а не кода.

## 8. OpenSpec baseline

OpenSpec 1.14.1 прогнан в отдельном worktree baseline-коммита `c7c60a5`:
`openspec init` → `openspec new change html-report` → четыре артефакта →
`openspec validate --strict` → `Change 'html-report' is valid`.

- [Транскрипт](openspec-baseline/transcript.txt)
- [proposal](openspec-baseline/artifacts/proposal.md),
  [delta-spec](openspec-baseline/artifacts/specs/html-report/spec.md),
  [design](openspec-baseline/artifacts/design.md),
  [tasks](openspec-baseline/artifacts/tasks.md)

Сравнение процессов — [`docs/sdd-comparison.md`](../docs/sdd-comparison.md),
рефлексия — [`specs/001-html-report/reflection.md`](../specs/001-html-report/reflection.md).
