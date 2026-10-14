UV ?= uv

.PHONY: format lint typecheck test security check lock

format:
	$(UV) run ruff format .

lint:
	$(UV) run ruff format --check .
	$(UV) run ruff check .

typecheck:
	$(UV) run mypy src

test:
	$(UV) run pytest

security:
	@requirements=$$(mktemp); trap 'rm -f "$$requirements"' EXIT; \
		$(UV) export --all-groups --no-emit-project --no-hashes --output-file "$$requirements" > /dev/null; \
		$(UV) run pip-audit --strict --disable-pip --no-deps --requirement "$$requirements"
	$(UV) run bandit -c pyproject.toml -r src

lock:
	$(UV) lock --check

check: lock lint typecheck test security
