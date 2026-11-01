"""Narrative enrichment via OpenAI-compatible endpoint.

This module is an optional dependency. Any failure to obtain a narrative
must not affect audit results; callers should handle NarrativeUnavailable.

HTTP implemented with standard library only (urllib) per style-guide.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class NarrativeUnavailable(RuntimeError):
    """Any dependency failure while fetching a narrative.

    Message is human-friendly and explains the concrete problem.
    """


# Проект работает с учебным VseLLM из корневого opencode.json, а не с api.openai.com.
# Адрес и модель переопределяются переменными, но по умолчанию совпадают с настройкой репозитория.
DEFAULT_BASE_URL = "https://litellm.data-light.ru/v1"
DEFAULT_MODEL = "openai/gpt-5"
DEFAULT_ENDPOINT = f"{DEFAULT_BASE_URL}/chat/completions"


@dataclass
class NarrativeOptions:
    endpoint: str = os.environ.get("VSELLM_API_BASE", DEFAULT_ENDPOINT)
    model: str = os.environ.get("VSELLM_DEFAULT_MODEL", DEFAULT_MODEL)
    timeout: float = 10.0


def _build_request(payload: dict[str, Any], api_key: str, endpoint: str) -> urllib.request.Request:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    # Only use the key from environment, never embed in code
    req.add_header("Authorization", f"Bearer {api_key}")
    return req


def request_narrative(report: dict[str, Any] | Any, *, model: str | None = None, timeout: float | None = None,
                      endpoint: str | None = None) -> str:
    """Requests a narrative text for the given report.

    Raises NarrativeUnavailable on any dependency failure or malformed response.
    """
    api_key = os.environ.get("VSELLM_API_KEY")
    if not api_key:
        raise NarrativeUnavailable("VSELLM_API_KEY не установлен — рецензия недоступна")

    opts = NarrativeOptions()
    if model:
        opts.model = model
    if timeout is not None:
        opts.timeout = float(timeout)
    if endpoint:
        opts.endpoint = endpoint

    # Prepare a concise prompt. Keep it simple; external endpoint decides formatting.
    # report can be a Report.as_dict() payload or any mapping; we only serialize it.
    try:
        report_payload = report if isinstance(report, dict) else getattr(report, "as_dict", lambda: report)()
    except Exception:
        # Fallback: best-effort JSON serialisation
        report_payload = report

    messages = [
        {"role": "system", "content": "You are a code auditor writing short, actionable narrative reviews."},
        {"role": "user", "content": "Summarize this audit report for a student; highlight what to fix first."},
        {"role": "user", "content": json.dumps(report_payload, ensure_ascii=False)},
    ]
    payload = {"model": opts.model, "messages": messages}

    req = _build_request(payload, api_key, opts.endpoint)
    try:
        with urllib.request.urlopen(req, timeout=opts.timeout) as resp:
            raw = resp.read()
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                raise NarrativeUnavailable(f"не-JSON ответ от зависимости: {exc}")
    except urllib.error.HTTPError as exc:
        raise NarrativeUnavailable(f"HTTP {exc.code} от зависимости: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        # Includes timeouts and DNS issues
        if isinstance(exc.reason, socket.timeout):
            raise NarrativeUnavailable("таймаут при обращении к зависимости") from exc
        raise NarrativeUnavailable(f"недоступна зависимость: {exc.reason}") from exc
    except (socket.timeout, TimeoutError) as exc:
        raise NarrativeUnavailable("таймаут при обращении к зависимости") from exc
    except (ssl.SSLError, ConnectionError, OSError) as exc:
        raise NarrativeUnavailable(f"ошибка соединения с зависимостью: {type(exc).__name__}: {exc}") from exc

    # Validate response shape
    if not isinstance(data, dict) or not data:
        raise NarrativeUnavailable("пустой или некорректный ответ зависимости")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise NarrativeUnavailable("ответ не содержит choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise NarrativeUnavailable("ответ имеет неожиданный формат choices[0]")
    message = first.get("message")
    if not isinstance(message, dict):
        raise NarrativeUnavailable("ответ не содержит message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise NarrativeUnavailable("ответ не содержит содержимого рецензии")
    return content.strip()
