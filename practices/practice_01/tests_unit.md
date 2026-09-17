# Unit-проверки

| Требование или правило | Что проверяем изолированно | Вход | Ожидаемый результат | Evidence |
|---|---|---|---|---|
| `QA-1` — риск только при наличии доказательства в diff | `ReviewService.review` не включает риск без ссылки на строку diff | Заглушка LLM возвращает риск без поля `evidence` | Риск отфильтрован из ответа; `risks == []` | Проверяется через мок `LLM` в unit-тесте |
| `REL-1` — timeout 10 секунд | `ReviewService.review` перехватывает `TimeoutError` от LLM | Заглушка LLM бросает `TimeoutError` через 0 мс | `review()` возвращает контролируемый объект ошибки, а не пробрасывает исключение | Мок `LLM.generate` с `side_effect=TimeoutError` |
| `API-1` — отклонение diff > 20 000 символов | `ReviewService.review` возвращает ошибку до вызова LLM | `diff` длиной 20 001 символ | Возбуждается `ValueError` или кастомный `DiffTooLargeError`; `LLM.generate` не вызывался | Проверить через `unittest.mock.MagicMock` — `assert not llm.generate.called` |
| `SEC-1` — очистка секретов | Функция очистки заменяет секреты на `[REDACTED]` | `diff` содержит `API_KEY=secret123` | В строке промпта `API_KEY=secret123` заменена на `API_KEY=[REDACTED]` | Сравнение строк промпта до и после очистки |
| `OUT-1` — структура ответа | `ReviewService.review` возвращает словарь с ключами `summary`, `risks`, `checks` | Валидный diff, LLM возвращает корректный ответ | `result.keys() == {"summary", "risks", "checks"}`; `len(result["risks"]) <= 3` | Проверить тип и длину `risks` в assert |

## Реализация тестов

Исполняемые pytest-тесты находятся в [`tests/test_review_service.py`](../../tests/test_review_service.py).

Покрытые правила:
- `API-1` → `test_api1_rejects_too_long_diff` — diff > 20 000 символов, LLM не вызывается, бросается `ValueError`
- `REL-1` → `test_rel1_timeout_is_caught_and_uses_10s_timeout` — `TimeoutError` перехватывается, `timeout=10` передаётся в `generate`
- `OUT-1` → `test_out1_response_structure_and_risks_cap` — ответ содержит `summary`, `risks` (≤3), `checks`
- `QA-1` → `test_qa1_risk_requires_evidence_present` — риск без поля `evidence` отфильтровывается

Что исправили вручную после few-shot (P2-01): модель использовала `pytest.raises((ValueError, Exception))` — слишком широко; в финальном коде оставили только `ValueError` согласно `API-1`.

## Как использовали AI

- Строка в [`prompts.md`](prompts.md): P1-01 (zero-shot, baseline), P2-01 (few-shot, реализация тестов).
- Что проверили и исправили сами: каждый тест-кейс сопоставлен с конкретным правилом из `CASE.md`; тип исключения в `API-1` уточнён с `Exception` до `ValueError`.
