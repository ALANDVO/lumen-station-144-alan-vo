# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

core-api

## Roadmap

### core-api — Core FastAPI Application Skeleton

Status: done

Acceptance:
- FastAPI app starts on port 8000
- Health endpoint returns 200 OK
- Basic project structure with pyproject.toml

Implementation: `app/main.py`, `pyproject.toml`

Tests: `tests/test_main.py`

### context-sandbox — Context Sandbox Tool Output Reduction

Status: planned

Acceptance:
- Tool output sandboxed and truncated to 98% reduction
- Session memory persisted across requests

### mcp-routing — MCP Platform Routing

Status: planned

Acceptance:
- Routes requests across 17 platforms via MCP
- Hooks enforce routing rules

