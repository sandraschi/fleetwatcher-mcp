set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

serve:
    uv run python -m fleetwatcher_mcp.server

lint:
    uv run ruff check src/

fmt:
    uv run ruff format src/

test:
    uv run pytest tests/ -v

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green