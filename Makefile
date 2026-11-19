.PHONY: setup proto seed test benchmark charts

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e '.[dev]'
	PATH="$(CURDIR)/.venv/bin:$$PATH" bash scripts/compile_proto.sh

proto:
	PATH="$(CURDIR)/.venv/bin:$$PATH" bash scripts/compile_proto.sh

seed:
	PYTHONPATH=src .venv/bin/python -m music_service.seed

test:
	PYTHONPATH=src .venv/bin/python -m pytest

benchmark:
	PYTHONPATH=src .venv/bin/python -m music_service.benchmarks.run

charts:
	.venv/bin/python scripts/generate_charts.py

