# Журнал запросов и проверок

Не сохраняйте скрытую Chain of Thought и полный чат. Нужны запрос, краткий результат, ссылка на изменённый артефакт и ваша проверка.

| ID | Артефакт и цель | Инструмент / модель | Тип промпта | Запрос или ссылка на него | Результат или ссылка | Что приняли | Что отклонили или исправили | Как проверили |
|---|---|---|---|---|---|---|---|---|
| P1-01 | Baseline-ревью `TRAINING_PR.diff` | OpenCode 1.18.30 / openai/gpt-5 (VseLLM) | zero-shot | «Ниже diff учебного PR. Посмотри PR и найди проблемы. @practices/practice_01/TRAINING_PR.diff» | [P1-01 ответ](#p1-01-ответ-модели) | Все проблемы категории High и Medium, которые явно видны в diff: отсутствие Pydantic-валидации, синхронный эндпоинт, неограниченный промпт, отсутствие обработки ошибок, prompt injection | Thread-safety (не видна из diff), аутентификация и rate limiting (выходят за рамки задачи), Open Questions — не подтверждены артефактами | Сверил каждый finding с конкретными строками diff: `api.py:35-37`, `review_service.py:19-22` — все High/Medium ссылаются на реальные строки |
| P1-02 | Ревью `TRAINING_PR.diff` с master prompt и Context Pack | OpenCode / openai/gpt-5 (VseLLM) | master prompt | [Master Prompt v1](#master-prompt-v1) | [P1-02 ответ](#p1-02-ответ-модели) | SEC-1, OUT-1, REL-1 — все три риска подтверждены цитатами из diff и явно ссылаются на правило; Checks покрывают API-1 | «Input validation» в Checks выходит за рамки данных правил — полезно, но не является нарушением из Rules | Сверил каждый risk с правилом из Context Pack и строкой diff: `review_service.py:19-22` и `api.py:35-37` — все три подтверждены |
| P1-03 |  |  |  |  |  |  |  |  |

## P1-01 Ответ модели

```
Findings (ordered by severity)

High
- app/api.py:35-37 create_review: No input validation. Accepting a bare dict and indexing
  payload["diff"] will raise KeyError on missing field, returning a 500 instead of a 422
  with a clear message. Use a Pydantic model for the request body and response.
- app/api.py:35-37 create_review: Synchronous endpoint calling a likely blocking LLM
  backend will block the event loop worker. Prefer async with an async LLM client or run
  the blocking call in a threadpool.
- app/review_service.py:19-22 ReviewService.review: Unbounded prompt size. Passing the
  full diff without size checks can blow up latency, cost, or exceed LLM context limits.
- app/review_service.py:19-22 and app/api.py:36,37: Type hints use dict[str, str] which
  require Python 3.9+. If the project targets 3.8, imports will fail at runtime.
- app/review_service.py:21-22 ReviewService.review: No error handling or timeouts around
  LLM.generate. Any exception will bubble up to the API and become a 500.

Medium
- app/api.py:35-37 API schema quality: Using plain dict yields a poor OpenAPI schema.
  Define Pydantic models for request (diff: str) and response (comment: str).
- app/review_service.py:19-22 Prompt construction: The diff is concatenated directly into
  the prompt without clear delimiting — vulnerable to prompt confusion/injection.
- app/review_service.py:22 Response shape: Returning a single "comment" string may not
  meet review needs (multiple findings, severity, file/line references).
- app/api.py:35-37 Lack of authentication/rate limiting — open endpoint can be abused.
- app/review_service.py:16-18 Thread safety of shared llm instance is unknown.
- app/review_service.py:19-22 Observability: No logging/metrics for request size, latency.

Low
- app/review_service.py:10-13 LLM Protocol formatting change is stylistic only.
- app/api.py:35-37 HTTP semantics: consider versioning (/api/v1/reviews).
- app/review_service.py:19-22 No docstrings.

Open Questions
- What Python version is the project targeting?
- Is the LLM client synchronous or async?
- What is the expected maximum diff size?
- What response structure is desired by consumers?
- Are there authentication, rate limiting, or quota requirements?
```

## Master Prompt v1

Контракт второго запуска. Ссылки на источники: Context Pack — `context.md`, правила — `CASE.md`, вход — `TRAINING_PR.diff`.

### 1. Цель и роль

- Цель: автоматически выполнить первичный разбор учебного diff и вернуть краткое описание, максимум три риска с доказательствами и список проверок.
- Роль AI: помощник ревьюера PR. Решения не принимает, код не изменяет (`SCOPE-1`).

### 2. Входы и источники

- Обязательный вход: `TRAINING_PR.diff` (git patch), до 20 000 символов (`API-1`).
- Разрешённые файлы и источники: только прикреплённый diff; репозиторий и сеть не читать.
- Context Pack — факты, правила, примеры и ограничения: см. `context.md` (включает `SEC-1`, `API-1`, `REL-1`, `OUT-1`, `SCOPE-1`, `QA-1`, `OBS-1`).

### 3. Задача и артефакты

- Что сделать: разобрать diff, выделить нарушенные правила и потенциальные ошибки, сформировать risks с доказательствами по строкам.
- Что вернуть: JSON по `OUT-1`: `summary`, массив `risks` (до 3: `{file, line, evidence, risk, rule}`), массив `checks`.

### 4. Формат результата

- Структура ответа: `{ summary: string, risks: Array<{file:string,line:number,evidence:string,risk:string,rule:string}>, checks: string[] }`.
- Ограничения объёма: summary ≤ 300 символов; evidence — точная цитата строки из diff; максимум 3 риска.

### 5. Полномочия и запреты

- Разрешено: анализировать diff, ссылаться на строки и правила, предлагать проверки.
- Запрещено: approve/merge, изменять код, ссылаться на несуществующие правила, записывать diff/ответ в логи (`OBS-1`).

### 6. Рабочий процесс и остановка

- Шаги:
  1) Извлечь файлы и строки из diff.
  2) Сопоставить находки с правилами из `CASE.md`.
  3) Для каждого риска зафиксировать точный путь и строку, приложить цитату evidence.
  4) Сформировать `checks` с воспроизводимыми шагами.
- Когда остановиться и запросить человека: если нет подтверждаемого evidence по `QA-1` или вход превышает лимит (`API-1`).

### 7. Проверки и evidence

- Как проверять утверждения: каждый риск подтверждать точной цитатой из diff и указанием нарушенного правила. Если подтверждения нет — риск не включать (`QA-1`).
- Какое evidence сохранить: путь к файлу с номером строки и цитатой; шаги для ручной/автоматической проверки.

### 8. Definition of Done

- Задача закончена, когда: выдано краткое summary, до 3 подтверждённых рисков с evidence и rule, и список проверок; границы соблюдены; формат соответствует `OUT-1`.

## Риски (макс 3) — подтверждены diff и правилами

1. Нарушение `SEC-1` — передача diff во внешний LLM без удаления секретов
   - Файл и строка: `app/review_service.py:19-22`
   - Доказательство:
     ```text
     19:     def review(self, diff: str) -> dict[str, str]:
     20:         prompt = f"Review this pull request and find problems:\n{diff}"
     21:         answer = self.llm.generate(prompt)
     22:         return {"comment": answer}
     ```
   - Правило: `SEC-1`
   - Проверка: передать diff, содержащий тестовый токен (`TOKEN_123`). Ожидание по правилу — токен должен быть редактирован до `[REDACTED]` перед LLM-вызовом; фактическое поведение — токен попадает в `prompt`. Unit-проверка: замокать `LLM.generate` и зафиксировать вход.

2. Нарушение `API-1` — нет отклонения длинного diff с HTTP 413
   - Файл и строка: `app/api.py:35-37`
   - Доказательство:
     ```text
     35: @app.post("/api/reviews")
     36: def create_review(payload: dict) -> dict[str, str]:
     37:     return review_service.review(payload["diff"]) 
     ```
   - Правило: `API-1`
   - Проверка: отправить POST `/api/reviews` с `diff` длиной > 20 000 символов. Ожидается 413 по правилу; фактически — нет проверки длины, эндпоинт принимает запрос.

3. Нарушение `OUT-1` — неверная структура ответа
   - Файл и строка: `app/review_service.py:22`
   - Доказательство:
     ```text
     22:         return {"comment": answer}
     ```
   - Правило: `OUT-1` (требуются `summary`, `risks`, `checks`)
   - Проверка: вызвать `/api/reviews` с любым валидным diff и проверить JSON-ключи ответа. Ожидается наличие `summary`, `risks`, `checks`; фактически — только `comment`.

## P1-02 Ответ модели

```
Summary
- Added POST endpoint at /api/reviews that forwards a provided diff to the LLM via ReviewService.
- Implemented ReviewService.review that embeds the raw diff into a prompt and returns {"comment": answer}.
- Minor formatting change to the LLM Protocol signature.

Risks
1. SEC-1 violation (tokens/keys not removed before LLM call)
   Path: app/review_service.py:20
   Evidence: prompt = f"Review this pull request and find problems:\n{diff}"
   Why: The raw diff is sent to the external LLM without any redaction of tokens or private keys. Violates SEC-1.

2. OUT-1 violation (wrong API response structure)
   Path: app/review_service.py:22
   Evidence: return {"comment": answer}
   Why: The API returns a dict with "comment" instead of the required structure containing "summary", "risks" (up to 3), and "checks". Violates OUT-1.

3. REL-1 violation (no 10s timeout or error interception on LLM call)
   Path: app/review_service.py:21
   Evidence: answer = self.llm.generate(prompt)
   Why: The LLM call lacks a 10-second timeout and try/except handling. Violates REL-1.

Checks
- API-1: Send a diff > 20,000 characters to POST /api/reviews and verify the request is rejected with HTTP 413.
- OUT-1: Verify the response structure includes "summary", "risks" (max 3), and "checks" for normal and error paths.
- REL-1: Simulate slow or failing LLM; confirm a 10s timeout and that errors are caught and handled.
- SEC-1: Provide a diff containing placeholder secrets/tokens; ensure they are redacted before any LLM invocation.
- Input validation: POST /api/reviews with missing or malformed "diff" key returns a clear client error.
```

## Сравнение двух запусков

| Проверка | Zero-shot (P1-01) | С master prompt (P1-02) | Вывод |
|---|---|---|---|
| Есть ссылка на файл или строку | ✅ Да — `api.py:35-37`, `review_service.py:19-22` | ✅ Да — `review_service.py:20`, `review_service.py:22`, `review_service.py:21` | Оба запуска дают точные ссылки, но P1-02 точнее (отдельная строка для каждого риска) |
| Вывод подтверждён diff или правилом | ⚠️ Частично — High/Medium технически корректны, но без ссылки на правила проекта | ✅ Да — каждый риск явно ссылается на правило (`SEC-1`, `OUT-1`, `REL-1`) и приводит цитату из кода | Master prompt принципиально улучшил: модель теперь проверяет по конкретным правилам, а не по «лучшим практикам» |
| Соблюдены границы AI | ⚠️ Частично — модель сама решала что важно, вышла за рамки (auth, thread-safety) | ✅ Да — ровно 3 риска, нет домыслов, код не правит | Context Pack и Forbidden явно ограничили зону ответственности |
| Есть воспроизводимая проверка | ❌ Нет — рекомендации общие («добавьте обработку») | ✅ Да — для каждого check конкретный шаг и ожидаемый результат | Master prompt потребовал `checks`, и модель добавила их для всех правил |

## Peer review

| Где другой команде пришлось догадываться | Что исправили | Если не исправили — почему |
|---|---|---|
| 1 |  |  |
| 2 |  |  |
| 3 |  |  |
