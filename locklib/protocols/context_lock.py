from types import TracebackType
from typing import Any, Optional, Type

try:
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import (  # type: ignore[assignment]
        Protocol,
        runtime_checkable,
    )

from locklib.protocols.lock import LockProtocol


@runtime_checkable
class ContextLockProtocol(LockProtocol, Protocol):
    def __enter__(self) -> Any:
        raise NotImplementedError('Do not use the protocol as a lock.')
        return None  # pragma: no cover

    def __exit__(self, exception_type: Optional[Type[BaseException]], exception_value: Optional[BaseException], traceback: Optional[TracebackType]) -> Any:
        raise NotImplementedError('Do not use the protocol as a lock.')
        return None  # pragma: no cover
