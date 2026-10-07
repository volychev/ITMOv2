# Skill: submission-audit

Файлы: [`../.opencode/skills/submission-audit/`](../.opencode/skills/submission-audit/).

```
.opencode/skills/submission-audit/
├── SKILL.md                       процедура: 5 шагов
├── references/
│   ├── exit-codes.md              что означает каждый код возврата
│   ├── rubric-rules.md            11 правил рубрики с весами
│   └── writing-rules.md           как писать и проверять новые правила
└── scripts/
    └── run-audit.sh               обёртка: аудит + разбор результата
```

## Устройство

**Frontmatter** задаёт, когда skill применяется:

```yaml
---
name: submission-audit
description: Use when checking whether a practice folder is ready to submit,
  before a commit, or when asked "что ещё не сдано", "проверь сдачу",
  "готов ли я к сдаче", "не хватает ли файлов". Runs the rubrica rubric
  over the folder, explains exit codes, and blocks submission on blockers.
license: MIT
compatibility: opencode
metadata:
  audience: student
  workflow: pre-submission
---
```

`name` обязан совпадать с именем каталога, `description` — 1..1024 символов.
Подробности в [`../.opencode/skills/submission-audit/SKILL.md`](../.opencode/skills/submission-audit/SKILL.md).

**Тело** — процедура в пять шагов, а не эссе о зачем это нужно:

1. прогнать рубрику;
2. закрыть блокеры первыми;
3. проверить предупреждения (в том числе о секретах);
4. подтвердить применение среды;
5. показать факты, а не обещания.

**References** вынесены отдельно, потому что это справочные данные, а не
процедура. Агент читает их по требованию, а не всегда. Плюс к тому имена
триггеров в `description` — «проверь сдачу», «готов ли я к сдаче» — именно
по ним skill выбирается.

**Script** `run-audit.sh` делает рутину: зовёт CLI, ловит код возврата и
печатает человекочитаемый итог одной строкой.

```sh
sh .opencode/skills/submission-audit/scripts/run-audit.sh .. rubrics/practice_04.yaml
```

## Запуск и проверенный результат

Skill был загружен агентом через инструмент `skill` в реальной сессии:

```
TOOL skill status=completed args={"name": "submission-audit"}
```

Агент затем прочитал связанный reference и перечислил 11 правил с теми же
severity и весами, что в рубрике. Полный разбор — в
[`../evidence/E1-agents-skill-mcp.md`](../evidence/E1-agents-skill-mcp.md).

Проверка, что skill виден opencode:

```sh
opencode debug skill
# [{ "name": "submission-audit",
#    "location": ".../rubrica/.opencode/skills/submission-audit/SKILL.md", … }]
```

Результат работы skill виден по тому, что агент после его загрузки назвал
блокеры и веса без обращения к рубрике на диске.

## Что skill улучшил в задаче

Шаг «что ещё не сдано» без skill — это ручной проход по чек-листу из README.
Skill превращает его в одну команду с интерпретацией кода возврата и приоритетом
«блокеры первыми». На финальном прогоне рубрика дала 17/17, то есть
пропущенных обязательных артефактов не осталось.

## Границы применимости

- Skill про сдачу. Качество кода он не проверяет — это `sh scripts/check.sh`.
- Skill не заменяет чтение `fix_hints`: он говорит, что проверить, а решение
  принимает человек.
- Если рубрика изменилась, `references/rubric-rules.md` надо править вместе
  с `rubrics/practice_04.yaml`, иначе агент получит устаревшие цифры.