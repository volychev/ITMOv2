.PHONY: install check test audit audit-json

PY := $(CURDIR)/.venv/bin/python

install:
	@test -x $(PY) || (command -v uv >/dev/null && uv venv .venv)
	@command -v uv >/dev/null && uv pip install --python $(PY) -e . || $(PY) -m pip install -e .

check:
	@sh scripts/check.sh

test: check

audit:
	@$(PY) -m rubrica.cli .. --spec rubrics/practice_04.yaml

audit-json:
	@$(PY) -m rubrica.cli .. --spec rubrics/practice_04.yaml --json

