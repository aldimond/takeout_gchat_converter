PY_SOURCES = *.py

.PHONY: lint
lint:
	pyflakes $(PY_SOURCES)
	mypy $(PY_SOURCES)

.PHONY: format
format:
	black --line-length 80 $(PY_SOURCES)
	isort $(PY_SOURCES)
