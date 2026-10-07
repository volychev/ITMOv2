"""Фича A: валидация входа перед любыми чтениями и любым обращением к зависимости.

Порядок важен: сначала дёшево и локально, потом дорого. Если вход плохой,
аудит не начинается вообще.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_TARGET_BYTES = 64 * 1024 * 1024
MAX_FILES = 5_000
MAX_TARGET_NAME = 120
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}

_WS_RE = re.compile(r"[ \t]+")


class InputRejected(Exception):
    """Вход не прошёл валидацию. Дальше ничего не выполняется."""


@dataclass(frozen=True)
class ValidatedInput:
    target: Path
    spec_path: Path | None = None
    notes: list[str] = field(default_factory=list)


def _reject(problems: list[str], reason: str) -> None:
    problems.append(reason)


def validate_target(raw: str | Path) -> tuple[Path, list[str]]:
    """Проверяет путь к папке сдачи: существование, тип, глубину, безопасность."""
    problems: list[str] = []
    notes: list[str] = []

    if raw is None or str(raw).strip() == "":
        raise InputRejected("путь к папке сдачи не указан")

    target = Path(raw).expanduser()
    name = target.name

    if len(name) > MAX_TARGET_NAME:
        _reject(problems, f"имя папки длиннее {MAX_TARGET_NAME} символов")
    if str(raw).strip() == "..":
        _reject(problems, "путь '..' указывает на родительскую папку; укажите папку сдачи явно")
    if any(ch.isspace() for ch in str(raw).strip()):
        _reject(problems, "путь содержит пробелы; передайте его кавычками в shell")

    if not target.exists():
        _reject(problems, f"папка {target} не существует")
    elif not target.is_dir():
        _reject(problems, f"{target} — не папка")
    else:
        if not target.is_dir() or target.resolve() == Path(target.anchor or "/").resolve():
            _reject(problems, "нельзя аудировать корень файловой системы")

        files = 0
        total = 0
        for entry in target.rglob("*"):
            if any(part in SKIP_DIRS for part in entry.parts):
                continue
            if entry.is_symlink():
                notes.append(f"пропущена символическая ссылка {entry.relative_to(target).as_posix()}")
                continue
            if not entry.is_file():
                continue
            files += 1
            try:
                total += entry.stat().st_size
            except OSError:
                notes.append(f"не удалось узнать размер {entry.relative_to(target).as_posix()}")
            if files > MAX_FILES:
                _reject(problems, f"больше {MAX_FILES} файлов: похоже, аудитируется не папка сдачи")
                break
            if total > MAX_TARGET_BYTES:
                _reject(problems, f"больше {MAX_TARGET_BYTES // (1024 * 1024)} МБ: это не папка сдачи")
                break

    if problems:
        raise InputRejected("вход не прошёл валидацию: " + "; ".join(problems))

    return target.resolve(), notes


def validate_flags(*, json_output: bool, max_findings: int) -> None:
    """Проверяет комбинацию флагов CLI."""
    problems: list[str] = []
    if max_findings < 1 or max_findings > 500:
        _reject(problems, "--max-findings должен быть в диапазоне 1..500")
    if problems:
        raise InputRejected("флаги некорректны: " + "; ".join(problems))


def validate_all(
    raw_target: str | Path,
    *,
    spec_path: str | Path | None = None,
    json_output: bool = False,
    max_findings: int = 200,
) -> ValidatedInput:
    """Единая точка входа: валидирует всё до начала работы."""
    validate_flags(json_output=json_output, max_findings=max_findings)
    target, notes = validate_target(raw_target)

    resolved_spec: Path | None = None
    if spec_path is not None:
        candidate = Path(spec_path).expanduser()
        if not candidate.exists():
            raise InputRejected(f"файл рубрики {candidate} не найден")
        if not candidate.is_file():
            raise InputRejected(f"{candidate} — не файл")
        if candidate.suffix not in {".yaml", ".yml"}:
            raise InputRejected(f"рубрика должна быть YAML (.yaml/.yml), получено {candidate.suffix!r}")
        resolved_spec = candidate.resolve()

    return ValidatedInput(target=target, spec_path=resolved_spec, notes=notes)