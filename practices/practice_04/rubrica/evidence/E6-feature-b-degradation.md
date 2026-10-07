# E6 — фича B: деградация при отказе зависимости

Фича B сделана в отдельном worktree на ветке `practice-04-b`, затем слита
`git merge --ff-only`. Реализацию выполнил агент OpenCode в новой сессии с
чистым контекстом; ниже — приёмка и живая проверка.

## Требования, которые ставились агенту

1. Модуль `src/rubrica/narrative.py`, одна функция `request_narrative(report, ...)`.
2. Любой отказ зависимости (нет ключа, недоступный endpoint, HTTP-ошибка,
   таймаут, не-JSON, пустой ответ, нет `choices`) → один тип исключения
   `NarrativeUnavailable` с понятным текстом.
3. Ключ только из `VSELLM_API_KEY`, в коде ключей нет.
4. CLI: `--narrative`, `--model`, `--timeout`; без `--narrative` зависимость
   не трогается вообще.
5. Код 3 = «аудит прошёл, рецензия недоступна». Код аудита 0/1/2 не меняется.
6. `src/rubrica/core.py` не меняется: аудит не ходит в сеть.
7. Тесты на успех и на все отказы + обновление `docs/requirements.md`
   и `docs/style-guide.md`.

Сырой поток сессии агента: `../raw-B-session.md`.

## Что вмешательство человека исправило

Агент сделал всё по списку, но при приёмке нашлись три дефекта:

1. **Тест зависел от окружения и ходил в сеть.** `test_json_contains_narrative_fields_when_requested`
   рассчитывал на отсутствие `VSELLM_API_KEY` у разработчика. С ключом в
   переменных тест уходил в сеть: `sh scripts/check.sh` замедлился с 0.2 с
   до 10.7 с. Исправлено: окружение изолировано, `request_narrative`
   подменён mock'ом, добавлена проверка `narrative.assert_not_called()` для
   запуска без флага.
2. **Умолчания указывали на чужой сервис.** `endpoint` по умолчанию был
   `https://api.openai.com/v1/chat/completions`, модель — `gpt-3.5-turbo`,
   тогда как проект работает с учебным VseLLM. Приведено к настройке
   репозитория: `https://litellm.data-light.ru/v1`, `openai/gpt-5`.
   Переменные `VSELLM_API_BASE` и `VSELLM_DEFAULT_MODEL` оставлены как
   переопределение.
3. **`make audit` звал запрещённый путь.** Цель аудита была `..`, а
   `validate_target` это отклоняет (родительская папка — не папка сдачи).
   Заменено на `.`, добавлена цель `audit-narrative`.

После правок `sh scripts/check.sh` снова 0.25 с и остаётся таким же
при установленном `VSELLM_API_KEY`.

## Живая проверка: четыре сценария

```sh
PY=.venv/bin/python
R="--spec rubrics/practice_04.yaml"
```

Сырой вывод: [`raw/E6-feature-b-degradation.txt`](raw/E6-feature-b-degradation.txt).

### 1. Ключа нет

```sh
env -u VSELLM_API_KEY $PY -m rubrica.cli . $R --narrative --json
```

```
audit exit_code: 2 | narrative: None
narrative_error: VSELLM_API_KEY не установлен — рецензия недоступна
код возврата: 3
```

### 2. Ключ есть, зависимость недоступна

```sh
VSELLM_API_BASE="https://127.0.0.1:9/v1/chat/completions" \
  $PY -m rubrica.cli . $R --narrative --json
```

```
audit: 14 / 17 exit 2
narrative_error: недоступна зависимость: [Errno 111] Connection refused
код возврата: 3
```

Вердикт аудита **не изменился**: те же 14/17 и тот же `exit_code: 2`.
Отличается только код возврата программы (3 вместо 2) и текст в stderr.

### 3. Без `--narrative` зависимость не трогается

```sh
$PY -m rubrica.cli . $R --json
```

```
narrative: None | narrative_error: None
код возврата: 2
```

### 4. Живой endpoint

```sh
$PY -m rubrica.cli . $R --narrative --timeout 120 --json
```

```
audit exit_code: 2 | narrative_error: None
narrative: Короткий итог и приоритеты
- Итог: 14/17, 1 блокер, 2 провала, exit_code=2. Базовые артефакты на месте:
  AGENTS.md, skill с референсами, хук, runner, собственный MCP подключён…
```

## Что доказывает этот файл

- Фича B не ломает фичу A: сценарии валидации входа (коды 2) работают
  без изменений, аудит по-прежнему не ходит в сеть.
- Отказ внешней зависимости не подменяет вердикт: `score`, `max_score`,
  `exit_code` в JSON остаются достоверными, ошибка уходит в отдельное поле.
- Код 3 отделён от кода аудита и читается как «всё прошло, но необязательное
  enrichment не получилось».
- Таймаут у реального endpoint по умолчанию 10 с; учебный VseLLM при холодном
  старте в него не укладывается. Это не дефект деградации (сообщение
  корректное), но повод поднять умолчание — отмечено в `reflection.md`.