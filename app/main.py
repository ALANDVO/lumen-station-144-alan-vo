from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.sandbox import ContextSandbox, SandboxConfig, ToolOutput, get_sandbox


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Lumen Station",
    description="Context window optimization for AI coding agents",
    version="0.1.0",
    lifespan=lifespan,
)


class SandboxRequest(BaseModel):
    tool_name: str
    raw_output: str
    session_id: str | None = None


class SessionCreateRequest(BaseModel):
    session_id: str
    metadata: dict | None = None


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "Lumen Station API", "version": "0.1.0"}


@app.post("/sandbox/process")
async def process_tool_output(request: SandboxRequest):
    sandbox = get_sandbox()
    session_id = request.session_id or "default"
    tool_output = sandbox.add_tool_output(session_id, request.tool_name, request.raw_output)
    return {
        "tool_name": tool_output.tool_name,
        "truncated_output": tool_output.truncated_output,
        "original_size": tool_output.original_size,
        "truncated_size": tool_output.truncated_size,
        "reduction_achieved": tool_output.reduction_achieved,
        "session_id": session_id,
    }


@app.post("/sandbox/session")
async def create_session(request: SessionCreateRequest):
    sandbox = get_sandbox()
    session = sandbox.create_session(request.session_id, request.metadata)
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "metadata": session.metadata,
    }


@app.get("/sandbox/session/{session_id}")
async def get_session(session_id: str):
    sandbox = get_sandbox()
    summary = sandbox.get_session_summary(session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary


@app.delete("/sandbox/session/{session_id}")
async def delete_session(session_id: str):
    sandbox = get_sandbox()
    session_file = sandbox.storage_path / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
    if session_id in sandbox._sessions:
        del sandbox._sessions[session_id]
    return {"deleted": True}


@app.post("/sandbox/cleanup")
async def cleanup_sessions():
    sandbox = get_sandbox()
    removed = sandbox.cleanup_expired_sessions()
    return {"removed": removed}

