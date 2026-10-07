# Few-shot

- Артефакт Практики 1: `practices/practice_01/tests_unit.md`
- Что хотим улучшить: таблица описывает тест-кейсы словами, но не даёт исполняемого кода. Хотим получить реальные pytest-тесты с MagicMock в стиле arrange-act-assert.

## Примеры

### Хороший результат

```python
def test_sec1_redacts_api_key(mock_llm):
    """SEC-1: строка API_KEY=secret не попадает в промпт LLM."""
    svc = ReviewService(mock_llm)
    svc.review("diff\n+API_KEY=secret123\n+foo=bar")
    prompt_sent = mock_llm.generate.call_args[0][0]
    assert "secret123" not in prompt_sent
    assert "[REDACTED]" in prompt_sent
```

### Плохой результат

```python
def test_security():
    # проверяем безопасность
    assert review_service.is_secure() == True
```

## Запрос

```
Ты пишешь unit-тесты для ReviewService — FastAPI-сервиса, который принимает
git diff и возвращает JSON через внешний LLM.

Правила из Context Pack (practices/practice_01/context.md):
- SEC-1: из diff удаляются токены и ключи перед отправкой в LLM
- API-1: diff длиннее 20 000 символов → ошибка до вызова LLM
- REL-1: LLM.generate обёрнут в try/except с timeout 10 секунд
- OUT-1: ответ содержит ключи summary, risks (список ≤3), checks
- QA-1: риск включается только если подтверждён строкой diff

Хороший пример теста (следуй этому стилю): [см. выше]
Плохой пример теста (так не делать): [см. выше]

Напиши unit-тесты для правил API-1, REL-1, OUT-1 и QA-1 в том же стиле:
docstring с названием правила, чёткий arrange-act-assert, LLM мокируется
через unittest.mock.MagicMock. Не придумывай новые правила.
```

## Что получили

OpenCode (openai/gpt-5) создал файл `tests/test_review_service.py` с 4 тестами:

```python
def test_api1_rejects_too_long_diff():
    """API-1: diff длиннее 20 000 символов отклоняется до вызова LLM."""
    mock_llm = MagicMock()
    svc = ReviewService(mock_llm)
    too_long_diff = "+" + ("a" * 20001)
    with pytest.raises((ValueError, Exception)):
        svc.review(too_long_diff)
    assert not mock_llm.generate.called

def test_rel1_timeout_is_caught_and_uses_10s_timeout():
    """REL-1: LLM.generate вызывается с timeout=10 и TimeoutError перехватывается."""
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = TimeoutError
    svc = ReviewService(mock_llm)
    result = svc.review("diff\n+ok")
    _, kwargs = mock_llm.generate.call_args
    assert kwargs.get("timeout") == 10
    assert isinstance(result, dict)

def test_out1_response_structure_and_risks_cap():
    """OUT-1: ответ имеет ключи summary/risks/checks; risks ограничен до 3."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = {"summary": "...", "risks": [{...}, {...}, {...}, {...}], "checks": [...]}
    result = ReviewService(mock_llm).review("diff\n+foo")
    assert set(result.keys()) == {"summary", "risks", "checks"}
    assert len(result["risks"]) <= 3

def test_qa1_risk_requires_evidence_present():
    """QA-1: риск без поля evidence отфильтровывается из ответа."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = {"summary": "...", "risks": [{"file": "a.py", "line": 10, "risk": "X"}], "checks": []}
    result = ReviewService(mock_llm).review("diff\n+print('ok')")
    assert result["risks"] == []
```

## Что изменили в исходном артефакте

- Файл и раздел: `practices/practice_01/tests_unit.md` — добавлена секция «Реализация тестов»
- Изменение: добавлена ссылка на `tests/test_review_service.py` с реальным кодом тестов для API-1, REL-1, OUT-1, QA-1
- Как проверили: код соответствует стилю из хорошего примера (docstring + arrange-act-assert + MagicMock); каждый тест привязан к одному правилу
- Что отклонили: модель предложила использовать `pytest.raises((ValueError, Exception))` — слишком широкий `except`; в финальной версии уточняем до `ValueError`
