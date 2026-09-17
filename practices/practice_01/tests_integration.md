# Integration-проверки

| Связь компонентов | Что может сломаться | Как воспроизводим | Ожидаемый результат | Evidence |
|---|---|---|---|---|
| `FastAPI (create_review)` → `ReviewService.review` | `KeyError` на отсутствующем поле `diff` в payload → HTTP 500 вместо 422 | Отправить `POST /api/reviews` с `{}` (пустой body) | HTTP 422 Unprocessable Entity с описанием поля `diff` | `curl -X POST /api/reviews -d '{}'` → `{"detail": [...]}`, status 422 |
| `ReviewService.review` → `LLM.generate` | Непойманное исключение LLM всплывает в API → HTTP 500 | Заменить LLM на тестовый стаб, бросающий `ConnectionError` | HTTP 503 с полем `error` (правило `REL-1`) | Интеграционный тест с фейковым LLM-клиентом через `app.dependency_overrides` |
| `create_review` → валидация размера diff | Diff > 20 000 символов проходит в LLM без проверки | Отправить `POST /api/reviews` с `diff` длиной 20 001 символ | HTTP 413 Request Entity Too Large (`API-1`) | `curl` с большим payload → статус 413 |
| `ReviewService` → очистка секретов → LLM | Секрет из diff попадает в промпт к внешнему LLM | Отправить diff с `SECRET=abc` и логировать промпт в тесте | В промпте `SECRET=abc` заменён на `SECRET=[REDACTED]` | Перехватить аргумент `LLM.generate` в тесте, проверить отсутствие оригинального секрета |

## Как использовали AI

- Строка в [`prompts.md`](prompts.md): P1-01 — High-findings послужили основой для выбора связей.
- Что проверили и исправили сами: добавлен тест на `SEC-1` (AI его не упомянул в контексте интеграции); указаны конкретные HTTP-коды ответа согласно правилам `CASE.md`.
