from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="lumen-station-144-alan-vo", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="lumen-station-144-alan-vo",
        version="0.1.0"
    )


@app.get("/")
async def root() -> dict:
    return {"message": "Welcome to lumen-station-144-alan-vo", "docs": "/docs"}
