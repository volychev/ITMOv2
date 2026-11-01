"""Исполнение рубрики по папке сдачи и подсчёт баллов."""

from __future__ import annotations

import fnmatch
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .spec import Rule, Spec

_MAX_TEXT_BYTES = 2_000_000
_MAX_FILES_WALKED = 20_000


@dataclass(frozen=True)
class Finding:
    rule_id: str
    kind: str
    severity: str
    ok: bool
    title: str
    detail: str
    weight: int = 1

    def as_dict(self) -> dict:
        return {
            "rule": self.rule_id,
            "kind": self.kind,
            "severity": self.severity,
            "ok": self.ok,
            "title": self.title,
            "detail": self.detail,
            "weight": self.weight,
        }


@dataclass
class Report:
    spec_id: str
    spec_title: str
    target: str
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> list[Finding]:
        return [f for f in self.findings if f.ok]

    @property
    def failed(self) -> list[Finding]:
        return [f for f in self.findings if not f.ok]

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.failed if f.severity == "blocker"]

    @property
    def max_score(self) -> int:
        return sum(f.weight for f in self.findings)

    @property
    def score(self) -> int:
        return sum(f.weight for f in self.findings if f.ok)

    @property
    def exit_code(self) -> int:
        if self.blockers:
            return 2
        return 1 if self.failed else 0

    def as_dict(self) -> dict:
        return {
            "spec": self.spec_id,
            "spec_title": self.spec_title,
            "target": self.target,
            "score": self.score,
            "max_score": self.max_score,
            "passed": len(self.passed),
            "failed": len(self.failed),
            "blockers": len(self.blockers),
            "exit_code": self.exit_code,
            "findings": [f.as_dict() for f in self.findings],
            "warnings": list(self.warnings),
        }


def _is_within(target: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(target.resolve())
    except (ValueError, OSError):
        return False
    return True


def _read_text(path: Path) -> tuple[str | None, str | None]:
    """Читает файл как текст. Возвращает (текст, ошибка)."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"недоступен для чтения ({exc.strerror})"
    if len(raw) > _MAX_TEXT_BYTES:
        return None, f"больше {_MAX_TEXT_BYTES} байт, пропущен"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, "не текст UTF-8, пропущен"


def _check_file_exists(target: Path, rule: Rule) -> tuple[bool, str]:
    candidate = target / (rule.path or "")
    if not _is_within(target, candidate.parent if candidate.parent.exists() else candidate):
        return False, f"путь {rule.path!r} выходит за пределы папки сдачи"
    if candidate.is_file():
        return True, f"файл {rule.path} на месте"
    return False, f"файл {rule.path} не найден"


def _check_file_missing(target: Path, rule: Rule) -> tuple[bool, str]:
    candidate = target / (rule.path or "")
    if candidate.exists():
        return False, f"{rule.path} не должен существовать в сдаче"
    return True, f"{rule.path} отсутствует, как и требуется"


def _check_file_contains(target: Path, rule: Rule) -> tuple[bool, str]:
    candidate = target / (rule.path or "")
    if not candidate.is_file():
        return False, f"файл {rule.path} не найден, проверить содержимое нельзя"
    text, error = _read_text(candidate)
    if text is None:
        return False, f"{rule.path}: {error}"
    pattern = re.compile(rule.pattern or "")
    match = pattern.search(text)
    if match:
        line = text[: match.start()].count("\n") + 1
        return True, f"{rule.path}: совпадение {rule.pattern!r} в строке {line}"
    return False, f"{rule.path}: нет совпадения с {rule.pattern!r}"


def _check_dir_count(target: Path, rule: Rule) -> tuple[bool, str]:
    pattern = rule.glob or "*"
    found: list[str] = []
    walked = 0
    for entry in sorted(target.rglob("*")):
        if entry.is_symlink() or not entry.is_file():
            continue
        if not _is_within(target, entry):
            continue
        walked += 1
        if walked > _MAX_FILES_WALKED:
            break
        rel = entry.relative_to(target).as_posix()
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, f"*/{pattern.lstrip('/')}"):
            found.append(rel)
    ok = len(found) >= rule.min_count
    if ok:
        sample = ", ".join(found[:3])
        return True, f"{len(found)} файлов по {pattern} (например: {sample})"
    return False, f"нужно минимум {rule.min_count} файлов по {pattern}, найдено {len(found)}"


_HANDLERS = {
    "file_exists": _check_file_exists,
    "file_missing": _check_file_missing,
    "file_contains": _check_file_contains,
    "dir_count": _check_dir_count,
}


def audit(spec: Spec, target: Path) -> Report:
    """Прогоняет рубрику по папке сдачи и возвращает отчёт."""
    target = Path(target)
    report = Report(spec_id=spec.id, spec_title=spec.title, target=str(target))

    for rule in spec.rules:
        handler = _HANDLERS[rule.kind]
        try:
            ok, detail = handler(target, rule)
        except Exception as exc:  # noqa: BLE001 — одно правило не должно ронять аудит
            ok, detail = False, f"правило упало с ошибкой: {type(exc).__name__}: {exc}"
        report.findings.append(
            Finding(
                rule_id=rule.id,
                kind=rule.kind,
                severity=rule.severity,
                ok=ok,
                title=rule.describe(),
                detail=detail,
                weight=rule.weight,
            )
        )

    if not spec.source:
        report.warnings.append("рубрика загружена из памяти, путь к источнику неизвестен")

    extra = sorted(_detect_secrets(target))
    if extra:
        report.warnings.append(f"возможные секреты в {len(extra)} файлах: {', '.join(extra[:5])}")

    return report


_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)


def _detect_secrets(target: Path) -> Counter:
    hits: Counter = Counter()
    for entry in target.rglob("*"):
        if entry.is_symlink() or not entry.is_file():
            continue
        if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in entry.parts):
            continue
        text, error = _read_text(entry)
        if text is None:
            continue
        if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
            rel = entry.relative_to(target).as_posix()
            hits[rel] += 1
    return hits
