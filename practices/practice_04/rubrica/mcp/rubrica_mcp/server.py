"""MCP-сервер rubrica: один полезный tool `rubrica_audit`.

Запуск (stdio-транспорт, как ждёт opencode):

    .venv/bin/python -m rubrica_mcp.server

Инструмент сознательно узкий. Ревьюеру и агенту нужен один вопрос:
«что в папке сдачи ещё не соответствует рубрике и какой код вернёт аудит».
Всё остальное — правила, веса, поиск секретов — считается внутри `rubrica`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = PROJECT_ROOT / "rubrics" / "practice_04.yaml"

if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rubrica.core import audit  # noqa: E402
from rubrica.spec import SpecError, load_spec  # noqa: E402
from rubrica.validate import InputRejected, validate_all  # noqa: E402

server = MCPServer(
    name="rubrica",
    version="0.2.0",
    instructions=(
        "Аудит папки сдачи практики по рубрике. "
        "Вызывай rubrica_audit перед сдачей или перед коммитом, "
        "чтобы узнать баллы, проваленные правила и код возврата."
    ),
)


class AuditInputRejected(InputRejected):
    """Вход отклонён. Текст годится для показа пользователю."""


def _resolve_spec(spec: str | None) -> Path:
    if spec is None or not spec.strip():
        return DEFAULT_SPEC
    candidate = Path(spec).expanduser()
    if candidate.is_dir():
        candidate = candidate / "rubrics" / "practice_04.yaml"
    if not candidate.exists():
        raise AuditInputRejected(
            f"рубрика {candidate} не найдена. Оставьте spec пустым, чтобы взять "
            f"{DEFAULT_SPEC}, или передайте путь к существующему .yaml."
        )
    return candidate


def _hints(report) -> list[str]:
    hints: list[str] = []
    for finding in report.failed:
        if finding.kind == "file_exists":
            hints.append(f"создай {finding.title.lower()} — файл отсутствует")
        elif finding.kind == "file_contains":
            hints.append(f"добавь в {finding.title.lower()} требуемое содержимое")
        elif finding.kind == "dir_count":
            hints.append(f"добавь файлы: {finding.title.lower()}")
        elif finding.kind == "file_missing":
            hints.append(f"убери из сдачи: {finding.title.lower()}")
    if report.blockers:
        hints.insert(0, f"сначала закрой {len(report.blockers)} blocker'ов, остальное потом")
    return hints


def _run(target: str, spec: str | None) -> dict:
    validated = validate_all(target, spec_path=spec if spec and spec.strip() else None)
    spec_path = _resolve_spec(spec)
    try:
        loaded = load_spec(spec_path)
    except SpecError as exc:
        raise AuditInputRejected(f"рубрика непригодна: {exc}") from exc

    report = audit(loaded, validated.target)
    report.warnings.extend(validated.notes)
    payload = report.as_dict()
    payload["spec_path"] = str(spec_path)
    payload["fix_hints"] = _hints(report)
    return payload


def _error(message: str, *, target: str, spec: str, started: float) -> str:
    """Ошибка входа возвращается как данные, а не как исключение.

    MCP-клиент показывает `Error executing tool` без деталей, поэтому
    бросать исключение здесь бессмысленно: агент не увидит причину.
    """
    return json.dumps(
        {
            "ok": False,
            "error": message,
            "target": target,
            "spec": spec or None,
            "findings": [],
            "score": 0,
            "max_score": 0,
            "fix_hints": ["исправь вход и повтори вызов"],
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        },
        ensure_ascii=False,
        indent=2,
    )


@server.tool(
    name="rubrica_audit",
    title="Аудит папки сдачи по рубрике",
    description=(
        "Проверяет папку сдачи практики по рубрике YAML и возвращает вердикт: баллы, "
        "проваленные правила с пояснением, код возврата, предупреждения о секретах и "
        "подсказки, что чинить. Вызывай перед сдачей или перед коммитом. "
        "При негодном входе (нет папки, битая рубрика) возвращает JSON с ok=false и "
        "полем error, где написано, что именно не так, — вместо пустого успешного отчёта."
    ),
)
def rubrica_audit(
    target: str,
    spec: str = "",
) -> str:
    """Аудит папки сдачи.

    Args:
        target: Путь к папке сдачи, например "." для текущей.
        spec: Путь к рубрике .yaml. Пустая строка — взять rubrics/practice_04.yaml проекта.
    """
    started = time.monotonic()
    try:
        payload = _run(target, spec)
    except InputRejected as exc:
        return _error(str(exc), target=target, spec=spec, started=started)
    except SpecError as exc:
        return _error(f"рубрика непригодна: {exc}", target=target, spec=spec, started=started)

    payload["ok"] = payload["exit_code"] == 0
    payload["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()