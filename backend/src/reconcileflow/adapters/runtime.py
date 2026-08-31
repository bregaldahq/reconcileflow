"""Runtime adapters for IDs, clocks, and demo authorization."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from reconcileflow.application.errors import AuthorizationError


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidGenerator:
    def new(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4()}"


class DemoAuthorizer:
    """Local-demo boundary; production replaces this with authenticated policy."""

    def require(self, actor_id: str, permission: str) -> None:
        if not actor_id.strip():
            raise AuthorizationError("a identidade do responsável é obrigatória")
        if permission not in {"review:write", "export:write"}:
            raise AuthorizationError(f"permissão não aceita: {permission}")


class NoopDispatcher:
    def dispatch_reconciliation(self, run_id: str) -> None:
        del run_id
