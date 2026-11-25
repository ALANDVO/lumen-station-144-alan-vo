from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.sandbox import ContextSandbox, SandboxConfig, ToolOutput, get_sandbox
from app.router import route_request, register_platform, add_routing_hook, _PLATFORM_REGISTRY


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: register default platforms
    register_platform("github", priority=1, metadata={"handler": "github_handler"})
    register_platform("gitlab", priority=2, metadata={"handler": "gitlab_handler"})
    register_platform("jira", priority=3, metadata={"handler": "jira_handler"})
    register_platform("gitlab-ci", priority=4, metadata={"handler": "ci_handler"})
    register_platform("azure-devops", priority=5, metadata={"handler": "ado_handler"})
    register_platform("bitbucket", priority=6, metadata={"handler": "bitbucket_handler"})
    register_platform("circleci", priority=7, metadata={"handler": "circleci_handler"})
    register_platform("travis-ci", priority=8, metadata={"handler": "travis_handler"})
    register_platform("codeship", priority=9, metadata={"handler": "codeship_handler"})
    register_platform("drone", priority=10, metadata={"handler": "drone_handler"})
    register_platform("appveyor", priority=11, metadata={"handler": "appveyor_handler"})
    register_platform("codesandbox", priority=12, metadata={"handler": "codesandbox_handler"})
    register_platform("replit", priority=13, metadata={"handler": "replit_handler"})
    register_platform("codeship-ng", priority=14, metadata={"handler": "codeship_ng_handler"})
    register_platform("netlify", priority=15, metadata={"handler": "netlify_handler"})
    register_platform("vercel", priority=16, metadata={"handler": "vercel_handler"})
    register_platform("railway", priority=17, metadata={"handler": "railway_handler"})
    # Setup default routing hooks
    add_routing_hook("github", lambda r: {**r, "validated": True})
    add_routing_hook("gitlab", lambda r: {**r, "validated": True})
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


# MCP Routing Models
class RouteRequest(BaseModel):
    platform: str
    request: dict[str, Any]


class RouteResponse(BaseModel):
    platform: str
    handler: str
    routed_request: dict[str, Any]
    status: str


class HealthResponse(BaseModel):
    status: str


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


# MCP Routing Endpoints


@app.post("/mcp/route", response_model=RouteResponse)
async def mcp_route(request: RouteRequest):
    """Route a request to the appropriate MCP platform handler."""
    try:
        result = route_request(request.platform, request.request)
        return RouteResponse(
            platform=result["platform"],
            handler=result["handler"],
            routed_request=result["routed_request"],
            status=result["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mcp/platforms")
async def list_platforms():
    """List all registered MCP platforms."""
    platforms = []
    for pid, pconf in sorted(
        _PLATFORM_REGISTRY.items(), key=lambda x: x[1]["priority"]
    ):
        platforms.append(
            {
                "platform": pid,
                "enabled": pconf["enabled"],
                "priority": pconf["priority"],
                "handler": pconf["metadata"].get("handler", "default"),
            }
        )
    return {"platforms": platforms}


@app.get("/mcp/platform/{platform_id}")
async def get_platform(platform_id: str):
    """Get details for a specific platform."""
    if platform_id not in _PLATFORM_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform_id}")
    pconf = _PLATFORM_REGISTRY[platform_id]
    return {
        "platform": platform_id,
        "enabled": pconf["enabled"],
        "priority": pconf["priority"],
        "metadata": pconf["metadata"],
    }
