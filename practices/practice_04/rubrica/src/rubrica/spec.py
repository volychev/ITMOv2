"""Модель рубрики: загрузка YAML и валидация самой рубрики.

Это слой фичи A. Он отвечает за вход: рубрика должна быть понятной машине,
иначе аудит бессмысленен. Никаких файлов сдачи он не трогает.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RULE_KINDS = ("file_exists", "file_contains", "file_missing", "dir_count")

_RULE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_SEVERITIES = ("blocker", "major", "minor")
_MAX_RULES = 200


class SpecError(Exception):
    """Рубрика нечитаема или невалидна.

    Сообщение всегда называет конкретное поле, чтобы его можно было
    показать агенту без дополнительных запросов.
    """

    def __init__(self, message: str, *, path: str | None = None, problems: list[str] | None = None):
        self.path = path
        self.problems = problems or []
        if problems:
            joined = "; ".join(problems)
            message = f"{message}: {joined}"
        super().__init__(message)


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    severity: str
    title: str
    path: str | None = None
    pattern: str | None = None
    needle: str | None = None
    glob: str | None = None
    min_count: int = 1
    weight: int = 1

    def describe(self) -> str:
        return self.title or self.id


@dataclass(frozen=True)
class Spec:
    id: str
    title: str
    rules: tuple[Rule, ...] = field(default_factory=tuple)
    source: Path | None = None

    def rule(self, rule_id: str) -> Rule:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        raise KeyError(rule_id)


def _require(problems: list[str], cond: bool, message: str) -> bool:
    if not cond:
        problems.append(message)
    return cond


def _parse_rule(raw: Any, index: int, problems: list[str]) -> Rule | None:
    where = f"rules[{index}]"
    if not isinstance(raw, dict):
        problems.append(f"{where}: правило должно быть отображением")
        return None

    rule_id = raw.get("id")
    if not isinstance(rule_id, str) or not _RULE_ID_RE.match(rule_id):
        problems.append(f"{where}.id: ожидается ^[a-z][a-z0-9_]{{2,63}}$, получено {rule_id!r}")
        rule_id = None

    kind = raw.get("kind")
    if kind not in RULE_KINDS:
        problems.append(f"{where}.kind: допустимые значения {RULE_KINDS}, получено {kind!r}")
        kind = None

    severity = raw.get("severity", "major")
    if severity not in _SEVERITIES:
        problems.append(f"{where}.severity: допустимые значения {_SEVERITIES}, получено {severity!r}")
        severity = None

    title = raw.get("title", "")
    if not isinstance(title, str):
        problems.append(f"{where}.title: ожидается строка")
        title = ""

    weight = raw.get("weight", 1)
    if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= 10:
        problems.append(f"{where}.weight: ожидается целое 1..10, получено {weight!r}")
        weight = 1

    min_count = raw.get("min_count", 1)
    if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 0:
        problems.append(f"{where}.min_count: ожидается целое >= 0, получено {min_count!r}")
        min_count = 1

    for key in ("path", "glob", "pattern", "needle"):
        if key in raw and raw[key] is not None and not isinstance(raw[key], str):
            problems.append(f"{where}.{key}: ожидается строка")
            raw[key] = None

    # Проверяем, что у правила есть ровно те аргументы, которые нужны его виду.
    needed = {
        "file_exists": ("path",),
        "file_missing": ("path",),
        "file_contains": ("path", "pattern"),
        "dir_count": ("glob",),
    }.get(kind or "", ())
    for key in needed:
        if not raw.get(key):
            problems.append(f"{where}.{key}: обязателен для kind={kind}")

    if kind == "dir_count" and min_count == 0:
        problems.append(f"{where}.min_count: для kind=dir_count ожидается >= 1")

    if raw.get("pattern"):
        try:
            re.compile(raw["pattern"])
        except re.error as exc:
            problems.append(f"{where}.pattern: не компилируется ({exc})")

    if rule_id is None or kind is None or severity is None:
        return None

    return Rule(
        id=rule_id,
        kind=kind,
        severity=severity,
        title=title or rule_id,
        path=raw.get("path"),
        pattern=raw.get("pattern"),
        needle=raw.get("needle"),
        glob=raw.get("glob"),
        min_count=min_count,
        weight=weight,
    )


def parse_spec(data: Any, *, source: Path | None = None) -> Spec:
    """Проверяет структуру рубрики и превращает её в :class:`Spec`."""
    problems: list[str] = []

    if not isinstance(data, dict):
        raise SpecError("Рубрика должна быть отображением YAML", path=str(source) if source else None)

    spec_id = data.get("id")
    if not isinstance(spec_id, str) or not spec_id.strip():
        problems.append("id: обязательное непустое поле")

    title = data.get("title", "")
    if not isinstance(title, str):
        problems.append("title: ожидается строка")
        title = ""

    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        problems.append("rules: обязательный список правил")
        raw_rules = []
    elif not raw_rules:
        problems.append("rules: список пуст, аудиту нечего проверять")
    elif len(raw_rules) > _MAX_RULES:
        problems.append(f"rules: не больше {_MAX_RULES} правил, получено {len(raw_rules)}")

    rules: list[Rule] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_rules):
        rule = _parse_rule(raw, index, problems)
        if rule is None:
            continue
        if rule.id in seen:
            problems.append(f"rules[{index}].id: дубликат {rule.id!r}")
            continue
        seen.add(rule.id)
        rules.append(rule)

    if problems:
        raise SpecError("Рубрика не прошла валидацию", path=str(source) if source else None, problems=problems)

    return Spec(id=str(spec_id), title=title, rules=tuple(rules), source=source)


def load_spec(path: Path) -> Spec:
    """Читает рубрику с диска и валидирует её."""
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SpecError("Файл рубрики не найден", path=str(path)) from exc
    except OSError as exc:
        raise SpecError(f"Файл рубрики недоступен: {exc.strerror}", path=str(path)) from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise SpecError(f"Рубрика не является корректным YAML: {exc}", path=str(path)) from exc

    if data is None:
        raise SpecError("Рубрика пуста", path=str(path))

    return parse_spec(data, source=path)