"""Tests for Context Sandbox feature."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.sandbox import ContextSandbox, SandboxConfig, ToolOutput, SessionMemory


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Lumen Station API"
        assert data["version"] == "0.1.0"


class TestSandboxCore:
    """Tests for core sandbox functionality."""

    def test_sandbox_config_defaults(self):
        config = SandboxConfig()
        assert config.reduction_ratio == 0.98
        assert config.max_output_chars == 10000
        assert config.session_ttl_seconds == 3600

    def test_sandbox_config_custom(self):
        config = SandboxConfig(reduction_ratio=0.95, max_output_chars=5000, session_ttl_seconds=1800)
        assert config.reduction_ratio == 0.95
        assert config.max_output_chars == 5000
        assert config.session_ttl_seconds == 1800

    def test_truncate_output_large(self):
        sandbox = ContextSandbox(SandboxConfig(reduction_ratio=0.98, max_output_chars=100))
        large_output = "x" * 10000
        tool_output = sandbox.sandbox_tool_output("test_tool", large_output)

        assert tool_output.tool_name == "test_tool"
        assert tool_output.raw_output == large_output
        assert tool_output.original_size == 10000
        assert tool_output.truncated_size <= 100
        assert tool_output.reduction_achieved >= 0.98

    def test_truncate_output_small(self):
        sandbox = ContextSandbox(SandboxConfig(reduction_ratio=0.98, max_output_chars=100))
        small_output = "hello world"
        tool_output = sandbox.sandbox_tool_output("test_tool", small_output)

        assert tool_output.original_size == 11
        assert tool_output.truncated_size == 11
        assert tool_output.reduction_achieved == 0.0
        assert tool_output.truncated_output == small_output

    def test_session_create_and_get(self):
        sandbox = ContextSandbox()
        session = sandbox.create_session("test-session", {"user": "test"})

        assert session.session_id == "test-session"
        assert session.metadata == {"user": "test"}

        retrieved = sandbox.get_session("test-session")
        assert retrieved is not None
        assert retrieved.session_id == "test-session"
        assert retrieved.metadata == {"user": "test"}

    def test_session_persistence(self, tmp_path):
        sandbox = ContextSandbox(storage_path=tmp_path)
        session = sandbox.create_session("persist-test", {"key": "value"})

        # Create new sandbox instance with same storage
        sandbox2 = ContextSandbox(storage_path=tmp_path)
        retrieved = sandbox2.get_session("persist-test")

        assert retrieved is not None
        assert retrieved.session_id == "persist-test"
        assert retrieved.metadata == {"key": "value"}

    def test_add_tool_output_to_session(self):
        sandbox = ContextSandbox()
        tool_output = sandbox.add_tool_output("session-1", "read_file", "file content here")

        assert tool_output.tool_name == "read_file"
        assert tool_output.raw_output == "file content here"

        session = sandbox.get_session("session-1")
        assert session is not None
        assert len(session.tool_outputs) == 1
        assert session.tool_outputs[0].tool_name == "read_file"

    def test_session_summary(self, tmp_path):
        sandbox = ContextSandbox(SandboxConfig(reduction_ratio=0.5), storage_path=tmp_path)
        sandbox.add_tool_output("session-summary", "tool1", "a" * 100)
        sandbox.add_tool_output("session-summary", "tool2", "b" * 200)

        summary = sandbox.get_session_summary("session-summary")

        assert summary is not None
        assert summary["session_id"] == "session-summary"
        assert summary["tool_count"] == 2
        assert summary["total_original_chars"] == 300
        assert summary["total_truncated_chars"] == 150  # 50% reduction
        assert summary["overall_reduction"] == 0.5

    def test_session_not_found(self):
        sandbox = ContextSandbox()
        summary = sandbox.get_session_summary("nonexistent")
        assert summary is None

    def test_cleanup_expired_sessions(self, tmp_path):
        import time
        import json
        sandbox = ContextSandbox(SandboxConfig(session_ttl_seconds=1), storage_path=tmp_path)
        sandbox.create_session("old-session")
        # Manually write old timestamp to disk
        session_file = tmp_path / "old-session.json"
        data = json.loads(session_file.read_text())
        data["updated_at"] = time.time() - 2
        session_file.write_text(json.dumps(data, indent=2))
        sandbox.create_session("new-session")

        time.sleep(0.1)
        removed = sandbox.cleanup_expired_sessions()

        assert removed == 1
        assert sandbox.get_session("old-session") is None
        assert sandbox.get_session("new-session") is not None


class TestSandboxAPI:
    """Tests for sandbox API endpoints."""

    @pytest.mark.asyncio
    async def test_process_tool_output(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/sandbox/process",
                json={
                    "tool_name": "bash",
                    "raw_output": "x" * 10000,
                    "session_id": "api-test-1",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["tool_name"] == "bash"
            assert data["session_id"] == "api-test-1"
            assert data["original_size"] == 10000
            assert data["truncated_size"] <= 10000
            assert data["reduction_achieved"] >= 0.98

    @pytest.mark.asyncio
    async def test_process_tool_output_default_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/sandbox/process",
                json={
                    "tool_name": "bash",
                    "raw_output": "test output",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "default"

    @pytest.mark.asyncio
    async def test_create_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/sandbox/session",
                json={
                    "session_id": "api-session-1",
                    "metadata": {"project": "test"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "api-session-1"
            assert data["metadata"] == {"project": "test"}

    @pytest.mark.asyncio
    async def test_get_session_summary(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First add some tool output
            await client.post(
                "/sandbox/process",
                json={
                    "tool_name": "tool1",
                    "raw_output": "x" * 1000,
                    "session_id": "summary-test",
                },
            )

            response = await client.get("/sandbox/session/summary-test")
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "summary-test"
            assert data["tool_count"] == 1
            assert data["total_original_chars"] == 1000

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sandbox/session/nonexistent")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create session first
            await client.post(
                "/sandbox/session",
                json={"session_id": "delete-test"},
            )

            response = await client.delete("/sandbox/session/delete-test")
            assert response.status_code == 200
            assert response.json() == {"deleted": True}

            # Verify deleted
            response = await client.get("/sandbox/session/delete-test")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cleanup_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/sandbox/cleanup")
            assert response.status_code == 200
            data = response.json()
            assert "removed" in data
            assert isinstance(data["removed"], int)
