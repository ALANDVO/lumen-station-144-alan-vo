# Lumen Station — Alan Vo

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


Context window optimization for AI coding agents. Sandboxes tool output (98% reduction), persists session memory, and enforces routing across 17 platforms via MCP + hooks.

## Quick Start

```bash
# Create virtual environment
python3 -m venv .venv

# Install dependencies
.venv/bin/pip install -e ".[dev]"

# Run server
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /health` - Health check (returns `{"status": "ok"}`)
- `GET /` - Root endpoint (returns version info)

## Project Structure

```
lumen-station-144-alan-vo/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI application
├── pyproject.toml       # Project configuration
├── feature-plan.json    # Feature tracking
├── PLAN.md              # Implementation plan
└── README.md            # This file
```

## Development

```bash
# Run tests (when available)
.venv/bin/pytest

# Lint
.venv/bin/ruff check .
```

## Status

See [PLAN.md](PLAN.md) for current implementation status and roadmap.

Maintainer: Alan Vo <alanvo@gmail.com>
