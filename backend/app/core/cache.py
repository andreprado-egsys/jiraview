# egSYS JiraView — Cache TTL em memória para endpoints NOC de alta frequência
import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    """Cache mínimo com expiração fixa para poucas chaves.

    Sem lock: uvicorn roda em evento único e todos os chamadores são `async def`.
    `now` é injetável para teste com relógio falso.
    """

    def __init__(self, ttl: float = 5.0, now: Callable[[], float] = time.monotonic):
        self._ttl = ttl
        self._now = now
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._now() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (self._now() + self._ttl, value)
