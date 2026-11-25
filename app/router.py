"""MCP Platform Router: Routes requests across platforms via MCP hooks."""

from __future__ import annotations

from typing import Any

# Platform registry: maps platform identifiers to routing config
_PLATFORM_REGISTRY: dict[str, dict[str, Any]] = {}

# Routing hooks: functions that can modify/validate requests per platform
_routing_hooks: dict[str, list[callable]] = {}


def register_platform(
    platform_id: str,
    *,
    priority: int = 0,
    enabled: bool = True,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Register a platform in the MCP routing registry.

    Args:
        platform_id: Unique platform identifier (e.g. "github", "gitlab", "jira")
        priority: Routing priority (higher = evaluated first)
        enabled: Whether the platform is active
        metadata: Additional platform-specific routing config
    """
    _PLATFORM_REGISTRY[platform_id] = {
        "priority": priority,
        "enabled": enabled,
        "metadata": metadata or {},
    }
    _routing_hooks.setdefault(platform_id, [])


def add_routing_hook(platform_id: str, hook: callable) -> None:
    """Add a routing hook for a specific platform.

    Hooks are called in order and can modify the request dict or raise
    HTTPException to reject the request.
    """
    _routing_hooks.setdefault(platform_id, []).append(hook)


def route_request(platform_id: str, request: dict[str, Any]) -> dict[str, Any]:
    """Route a request to the appropriate platform handler.

    Enforces routing rules via registered hooks. Returns the routed response.

    Raises:
        ValueError: If the platform is not registered or routing is disabled.
    """
    if platform_id not in _PLATFORM_REGISTRY:
        raise ValueError(f"Unknown platform: {platform_id}")

    platform = _PLATFORM_REGISTRY[platform_id]

    if not platform["enabled"]:
        raise ValueError(f"Platform disabled: {platform_id}")

    # Execute routing hooks
    hooks = _routing_hooks.get(platform_id, [])
    for hook in hooks:
        try:
            result = hook(request)
            if result is not None:
                request = result
        except Exception as e:
            raise ValueError(f"Routing hook failed for {platform_id}: {e}")

    # Determine handler based on platform metadata
    handler = platform["metadata"].get("handler", "default_handler")

    return {
        "platform": platform_id,
        "handler": handler,
        "routed_request": request,
        "status": "routed",
    }
