# Quickstart: проверка HTML-отчёта

**Фича**: `001-html-report` · **Дата**: 2026-11-02
**Контракт**: [contracts/ui-logic.md](contracts/ui-logic.md) ·
**Данные**: [data-model.md](data-model.md)

## Подготовка

```sh
cd practices/practice_04/rubrica
make install            # venv + зависимости, если ещё не сделано
sh scripts/check.sh     # baseline: все существующие тесты
```

## 1. Сгенерировать отчёт на текущей папке

```sh
.venv/bin/python -m rubrica.cli . \
  --spec rubrics/practice_04.yaml \
  --html /tmp/rubrica-report.html
```

Ожидание:

- код 0, если рубрика проходит;
- stdout — обычный текстовый отчёт;
- stderr — `HTML-отчёт: /tmp/rubrica-report.html`;
- файл `/tmp/rubrica-report.html` существует и открывается в браузере.

## 2. Сверить HTML с JSON

```sh
.venv/bin/python -m rubrica.cli . \
  --spec rubrics/practice_04.yaml \
  --json --html /tmp/rubrica-report-json.html > /tmp/rubrica.json
```

Ожидание: `/tmp/rubrica.json` — валидный JSON прежней схемы; метрики и rule id
в HTML совпадают с JSON. `--max-findings` на HTML не влияет.

Проверка без браузера:

```sh
python3 - <<'PY'
import json, pathlib, re
payload = json.loads(pathlib.Path('/tmp/rubrica.json').read_text())
html = pathlib.Path('/tmp/rubrica-report-json.html').read_text()
assert f"Баллы: {payload['score']}/{payload['max_score']}" in html
for finding in payload['findings'][:5]:
    assert finding['rule'] in html
print('HTML и JSON согласованы')
PY
```

## 3. Проверить экран в браузере

Открыть `/tmp/rubrica-report-json.html` по `file://` и проверить:

1. Шапка: spec id/title, target, `Баллы: P/M`, `Пройдено`, `Провалено`,
   `Блокеров`, `Код аудита`, баннер вердикта.
2. Ввести `readme` в поиск → остаются совпадения по rule id/заголовку/деталям,
   счётчик `Показано N из M` меняется.
3. Выбрать `severity=blocker`, включить «Только провалы» → только проваленные
   blocker-находки.
4. Сменить сортировку на «провалы сначала», затем «вес: больше сначала».
5. Нажать «Сбросить» → поиск пуст, severity «все», чекбокс выключен,
   сортировка «порядок рубрики».
6. Ввести заведомо отсутствующий запрос → «Ничего не найдено…»,
   `Показано 0 из M`, метрики шапки не меняются.
7. Отключить JavaScript → все находки и секции читаются.

## 4. Проверить состояния вердикта

```sh
# всё проходит
.venv/bin/python -m rubrica.cli . --spec rubrics/practice_04.yaml --html /tmp/pass.html

# провал без блокера: временная рубрика
cat > /tmp/rubric-major.yaml <<'YAML'
id: major_demo
title: Провал без блокера
rules:
  - id: has_readme
    kind: file_exists
    path: README.md
    severity: major
  - id: has_missing
    kind: file_exists
    path: NOPE.md
    severity: major
YAML
.venv/bin/python -m rubrica.cli . --spec /tmp/rubric-major.yaml --html /tmp/fail.html

# блокер
cat > /tmp/rubric-blocker.yaml <<'YAML'
id: blocker_demo
title: Блокер
rules:
  - id: has_missing
    kind: file_exists
    path: NOPE.md
    severity: blocker
YAML
.venv/bin/python -m rubrica.cli . --spec /tmp/rubric-blocker.yaml --html /tmp/blocker.html
```

Ожидание: коды 0/1/2 и соответствующие баннеры; HTML пишется во всех случаях.

## 5. Проверить ошибки пути

```sh
# нет родительской папки → 2, файл не создан
.venv/bin/python -m rubrica.cli . --spec rubrics/practice_04.yaml \
  --html /tmp/no-such-dir/report.html

# неверное расширение → 2
.venv/bin/python -m rubrica.cli . --spec rubrics/practice_04.yaml \
  --html /tmp/report.txt

# каталог вместо файла → 2
.venv/bin/python -m rubrica.cli . --spec rubrics/practice_04.yaml \
  --html /tmp

# пустой путь → 2
.venv/bin/python -m rubrica.cli . --spec rubrics/practice_04.yaml --html ""
```

Ожидание: `ОТКАЗ: HTML-отчёт не записан — <причина>` в stderr, код 2, файл не
создан, аудит не запускался для ранних отказов.

## 6. Проверить рецензию без сети

```sh
env -u VSELLM_API_KEY .venv/bin/python -m rubrica.cli . \
  --spec rubrics/practice_04.yaml \
  --narrative --html /tmp/narrative-unavailable.html
```

Ожидание: код 3, HTML записан, в нём бейдж «Рецензия недоступна» и текст
ошибки, баллы не изменились.

## 7. Проверить тестами

```sh
sh scripts/check.sh
```

Ожидание: `compileall: ok`, все тесты (прежние + новые) проходят, exit 0.
Точечно:

```sh
.venv/bin/python -m unittest discover -s tests -t tests -k test_report_html
.venv/bin/python -m unittest discover -s tests -t tests -k test_cli_html
```

## 8. Проверить детерминизм и безопасность

```sh
.venv/bin/python -m rubrica.cli . --spec rubrics/practice_04.yaml --html /tmp/a.html
.venv/bin/python -m rubrica.cli . --spec rubrics/practice_04.yaml --html /tmp/b.html
cmp /tmp/a.html /tmp/b.html && echo "детерминизм: ok"
```

В тестах дополнительно проверяется, что `<script>` и `"><img onerror=...>` из
рубрики выводятся как текст, а не исполняются.
