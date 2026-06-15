run:
	uv run auth

before_pr:
	ruff format
	ruff check --fix --unsafe-fixes
	mypy .
	lint imports;
