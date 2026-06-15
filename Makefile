run:
	uv run payments

before_pr:
	ruff format
	ruff check --fix --unsafe-fixes
	mypy .
	lint imports;
