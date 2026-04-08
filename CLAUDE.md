# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development
make install       # Install Python (uv sync) + frontend (npm install) deps
make dev-api       # Run API with hot reload (uvicorn)
make dev-frontend  # Run frontend dev server (Vite)

# Code quality
make lint          # ruff check src/
make format        # ruff format src/
make test          # pytest (asyncio_mode="auto")

# Run a single test
uv run pytest tests/test_file.py::test_name -v
```

## Architecture

**Hexagonal architecture** (ports & adapters) with three layers:

- **Domain** (`src/<project>/domain/`) — Pure Python, zero framework dependencies
  - `entities.py` — Value objects and domain models
  - `ports/inbound.py` — Use case interfaces
  - `ports/outbound/` — Adapter interfaces (repositories, providers)
  - `use_cases/` — Application logic

- **Adapters** (`src/<project>/adapters/`)
  - `inbound/` — FastAPI route files + `schemas/` (Pydantic DTOs)
  - `outbound/` — Implementations: database repos, external API clients

- **Infrastructure** (`src/<project>/infrastructure/`)
  - `app.py` — FastAPI lifespan, dependency injection wiring
  - `config.py` — Environment-based config via Pydantic Settings

## Key Patterns

**Dependency Injection**: Adapters are wired to ports in the infrastructure layer (composition root). Domain and use cases never import concrete adapters.

**Prompts**: Markdown templates in `prompts/` directory. Loaded by a registry using directory/name pattern.

**Migrations**: Numbered SQL files in `migrations/`. Tracked in a `schema_migrations` table. All DDL uses `IF NOT EXISTS`.

## Configuration

See `.env.example` for all variables. Use UV for package management (`uv sync`, `uv run`).

## Code Style

- Python: ruff, line-length=100, target py314. Rules: E, F, I, N, W, UP.
- Enter plan mode for non-trivial tasks (3+ steps or architectural decisions).
- Verify changes work before marking complete — run tests, check logs.
- Fix bugs autonomously — don't ask for hand-holding when given a bug report.
