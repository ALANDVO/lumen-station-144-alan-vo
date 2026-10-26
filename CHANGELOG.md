# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-10-25

### Added
- Core FastAPI application skeleton
- Health check endpoint (`/health`)
- Root endpoint (`/`)
- Project structure with pyproject.toml
- Virtual environment setup
- Basic documentation (README.md, PLAN.md)
- Feature tracking (feature-plan.json)

### Implementation
- `app/main.py`: FastAPI app with lifespan management
- `pyproject.toml`: Dependencies (fastapi, uvicorn, pydantic, pydantic-settings)
- `app/__init__.py`: Package marker

### Verified
- Server starts on port 8000
- Health endpoint returns 200 OK with `{"status": "ok"}`
- Root endpoint returns version info
