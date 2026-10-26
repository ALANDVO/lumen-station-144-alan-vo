"""Context Sandbox: Tool output reduction and session memory persistence."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SandboxConfig(BaseModel):
    """Configuration for sandbox behavior."""

    reduction_ratio: float = Field(default=0.98, ge=0.0, le=1.0)
    max_output_chars: int = Field(default=10000, ge=100)
    session_ttl_seconds: int = Field(default=3600, ge=1)


class ToolOutput(BaseModel):
    """Tool output with metadata."""

    tool_name: str
    raw_output: str
    truncated_output: str
    original_size: int
    truncated_size: int
    reduction_achieved: float
    timestamp: float = Field(default_factory=time.time)


class SessionMemory(BaseModel):
    """Persisted session memory."""

    session_id: str
    tool_outputs: list[ToolOutput] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ContextSandbox:
    """Manages tool output sandboxing and session persistence."""

    def __init__(
        self,
        config: SandboxConfig | None = None,
        storage_path: Path | None = None,
    ):
        self.config = config or SandboxConfig()
        self.storage_path = storage_path or Path(".sandbox_sessions")
        self.storage_path.mkdir(exist_ok=True)
        self._sessions: dict[str, SessionMemory] = {}

    def _truncate_output(self, output: str) -> tuple[str, int, int, float]:
        """Truncate output to achieve target reduction ratio."""
        original_size = len(output)

        # Don't truncate very small outputs
        if original_size < 100:
            truncated = output
        else:
            target_size = int(original_size * (1 - self.config.reduction_ratio))
            target_size = min(target_size, self.config.max_output_chars)

            if original_size <= target_size:
                truncated = output
            else:
                # Reserve space for truncation message
                msg = f"\n... [truncated {original_size - target_size} chars]"
                msg_len = len(msg)
                content_size = max(0, target_size - msg_len)
                truncated = output[:content_size] + msg

        truncated_size = len(truncated)
        reduction = 1.0 - (truncated_size / original_size) if original_size > 0 else 0.0

        return truncated, original_size, truncated_size, reduction

    def sandbox_tool_output(self, tool_name: str, raw_output: str) -> ToolOutput:
        """Sandbox a tool's output by truncating it."""
        truncated, orig_size, trunc_size, reduction = self._truncate_output(raw_output)
        return ToolOutput(
            tool_name=tool_name,
            raw_output=raw_output,
            truncated_output=truncated,
            original_size=orig_size,
            truncated_size=trunc_size,
            reduction_achieved=reduction,
        )

    def get_session(self, session_id: str) -> SessionMemory | None:
        """Get session from memory or load from disk."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        session_file = self.storage_path / f"{session_id}.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                session = SessionMemory(**data)
                self._sessions[session_id] = session
                return session
            except Exception:
                return None
        return None

    def save_session(self, session: SessionMemory) -> None:
        """Save session to memory and disk."""
        session.updated_at = time.time()
        self._sessions[session.session_id] = session
        session_file = self.storage_path / f"{session.session_id}.json"
        session_file.write_text(session.model_dump_json(indent=2))

    def create_session(self, session_id: str, metadata: dict[str, Any] | None = None) -> SessionMemory:
        """Create a new session."""
        session = SessionMemory(
            session_id=session_id,
            metadata=metadata or {},
        )
        self.save_session(session)
        return session

    def add_tool_output(self, session_id: str, tool_name: str, raw_output: str) -> ToolOutput:
        """Add tool output to session."""
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id)

        tool_output = self.sandbox_tool_output(tool_name, raw_output)
        session.tool_outputs.append(tool_output)
        self.save_session(session)
        return tool_output

    def get_session_summary(self, session_id: str) -> dict[str, Any] | None:
        """Get session summary with statistics."""
        session = self.get_session(session_id)
        if session is None:
            return None

        total_original = sum(t.original_size for t in session.tool_outputs)
        total_truncated = sum(t.truncated_size for t in session.tool_outputs)
        avg_reduction = sum(t.reduction_achieved for t in session.tool_outputs) / len(session.tool_outputs) if session.tool_outputs else 0.0

        return {
            "session_id": session.session_id,
            "tool_count": len(session.tool_outputs),
            "total_original_chars": total_original,
            "total_truncated_chars": total_truncated,
            "overall_reduction": 1.0 - (total_truncated / total_original) if total_original > 0 else 0.0,
            "average_reduction": avg_reduction,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "metadata": session.metadata,
        }

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from memory and disk."""
        now = time.time()
        removed = 0

        # Check in-memory sessions against their disk timestamps
        for session_id, session in list(self._sessions.items()):
            session_file = self.storage_path / f"{session_id}.json"
            disk_updated_at = session.updated_at
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text())
                    disk_updated_at = data.get("updated_at", session.updated_at)
                except Exception:
                    pass

            if now - disk_updated_at > self.config.session_ttl_seconds:
                del self._sessions[session_id]
                if session_file.exists():
                    session_file.unlink()
                removed += 1

        # Check on-disk sessions not in memory
        for session_file in self.storage_path.glob("*.json"):
            session_id = session_file.stem
            if session_id in self._sessions:
                continue
            try:
                data = json.loads(session_file.read_text())
                updated_at = data.get("updated_at", 0)
                if now - updated_at > self.config.session_ttl_seconds:
                    session_file.unlink()
                    removed += 1
            except Exception:
                pass

        return removed


# Global sandbox instance
_sandbox: ContextSandbox | None = None


def get_sandbox() -> ContextSandbox:
    """Get or create global sandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = ContextSandbox()
    return _sandbox
