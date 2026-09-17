# Unit-проверки

| Требование или правило | Что проверяем изолированно | Вход | Ожидаемый результат | Evidence |
|---|---|---|---|---|
| `QA-1` — риск только при наличии доказательства в diff | `ReviewService.review` не включает риск без ссылки на строку diff | Заглушка LLM возвращает риск без поля `evidence` | Риск отфильтрован из ответа; `risks == []` | Проверяется через мок `LLM` в unit-тесте |
| `REL-1` — timeout 10 секунд | `ReviewService.review` перехватывает `TimeoutError` от LLM | Заглушка LLM бросает `TimeoutError` через 0 мс | `review()` возвращает контролируемый объект ошибки, а не пробрасывает исключение | Мок `LLM.generate` с `side_effect=TimeoutError` |
| `API-1` — отклонение diff > 20 000 символов | `ReviewService.review` возвращает ошибку до вызова LLM | `diff` длиной 20 001 символ | Возбуждается `ValueError` или кастомный `DiffTooLargeError`; `LLM.generate` не вызывался | Проверить через `unittest.mock.MagicMock` — `assert not llm.generate.called` |
| `SEC-1` — очистка секретов | Функция очистки заменяет секреты на `[REDACTED]` | `diff` содержит `API_KEY=secret123` | В строке промпта `API_KEY=secret123` заменена на `API_KEY=[REDACTED]` | Сравнение строк промпта до и после очистки |
| `OUT-1` — структура ответа | `ReviewService.review` возвращает словарь с ключами `summary`, `risks`, `checks` | Валидный diff, LLM возвращает корректный ответ | `result.keys() == {"summary", "risks", "checks"}`; `len(result["risks"]) <= 3` | Проверить тип и длину `risks` в assert |

## Как использовали AI

- Строка в [`prompts.md`](prompts.md): P1-01 — findings из zero-shot стали основой для выбора покрываемых правил.
- Что проверили и исправили сами: каждый тест-кейс сопоставлен с конкретным правилом из `CASE.md`; добавлена проверка `QA-1`, которую AI не упомянул явно в zero-shot.
