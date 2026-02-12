try:
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import (  # type: ignore[assignment]
        Protocol,
        runtime_checkable,
    )

from typing import Any


@runtime_checkable
class LockProtocol(Protocol):
    def acquire(self) -> Any:
        raise NotImplementedError('Do not use the protocol as a lock.')
        return None  # pragma: no cover

    def release(self) -> Any:
        raise NotImplementedError('Do not use the protocol as a lock.')
        return None  # pragma: no cover
