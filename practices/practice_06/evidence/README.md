# Evidence практики 6

Все материалы получены при атаках **только** на собственный локальный процесс Mini Shop (`127.0.0.1:8066`) с синтетическими данными. Не запускайте скрипты против чужих систем.

## Структура

```text
evidence/
├── attack_before.py          # воспроизведение атак на исходную версию
├── attack_after.py           # повторные атаки на исправленную версию
├── before/
│   ├── attack_before.log     # сырой вывод атак (исходный service.py)
│   ├── log_leak_explicit.txt # явная демонстрация пароля и X-Token в /debug/logs
│   ├── service_original.py   # копия уязвимой ревизии из git HEAD
│   ├── context_normal.json   # обычный контекст AI-помощника
│   ├── context_injected.json # контекст с внедрённым отзывом
│   ├── llm_normal.json       # ответ shop-planner на обычный контекст
│   └── llm_injected.json     # ответ shop-planner на внедрённый контекст
└── after/
    ├── attack_after.log      # повторные атаки после фикса
    ├── http_hardening.txt    # заголовки, 415, 413
    ├── context_injected.json # контекст после фикса (untrusted-блоки)
    ├── llm_injected.json     # повторный ответ модели
    └── forced_invalid_tool.txt # принудительная передача недопустимого tool-call
```

## Воспроизведение

### 1. Исходная уязвимая версия

```bash
cd practices/practice_06/lab
cp ../evidence/before/service_original.py service.py   # временно, для проверки
python3 service.py --port 8066
# в другом терминале:
python3 ../evidence/attack_before.py | tee ../evidence/before/attack_before_replay.log
```

После запуска скрипта файлы sandbox удалены (шаг `delete_tree`). Перезапустите сервис, чтобы восстановить их. Не коммитьте временную замену `service.py`; верните исправленную версию из репозитория.

### 2. Исправленная версия

```bash
cd practices/practice_06/lab
python3 service.py --port 8066
# в другом терминале:
python3 ../evidence/attack_after.py | tee ../evidence/after/attack_after_replay.log
```

Ожидаемые коды: `401` без сессии, `403` на чужие объекты/инструменты, `400` на SQLi/traversal, `201` с ценой каталога, экранированный HTML.

### 3. AI-контур

```bash
cd practices/practice_06
# сохранить контекст:
TOKEN=$(curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"learn-alice"}' \
  http://127.0.0.1:8066/login | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -sS -H "X-Token: $TOKEN" \
  'http://127.0.0.1:8066/assistant/context?order_id=1&question=Show%20my%20receipt' \
  > evidence/after/context_injected.json

# отдельный процесс агента shop-planner:
opencode run --agent shop-planner --model crysta1/deepseek-v4.1-flash --format json \
  --file evidence/after/context_injected.json \
  "Клиент просит помочь с заказом. Верни только JSON решения."
```

В эксперименте модель отказалась от инструкции из отзыва (before) и вернула недопустимый `read_file` (after). В обоих случаях серверная авторизация проверяется отдельно принудительной передачей решения в `/assistant/execute`; она не должна зависеть от поведения модели.

## Важные оговорки

- `attack_before.py` содержит деструктивный шаг; это учебный стенд, файлы восстанавливаются перезапуском.
- `sandbox.py` намеренно не изменялся: физическая граница каталога остаётся прежней, исправлена авторизация **внутри** неё.
- Сырые токены в логах `before` синтетические и уже недействительны после перезапуска.
