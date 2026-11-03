"""Future policy boundary. All execution is disabled in this boilerplate."""

from app.service.tools.registry import ToolDefinition


def require_execution_permission(
    tool: ToolDefinition,
    target: str,
    *,
    explicit_authorization: bool = False,
    approved_scope: frozenset[str] = frozenset(),
) -> None:
    if tool.active and (not explicit_authorization or target not in approved_scope):
        raise PermissionError(
            "Active tools require explicit authorization and separately approved target scope"
        )
    raise PermissionError("Tool execution is disabled in this boilerplate")
