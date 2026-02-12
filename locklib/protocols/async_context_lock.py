from types import TracebackType
from typing import Any, Optional, Protocol, Type, runtime_checkable

from locklib.protocols.lock import LockProtocol


@runtime_checkable
class AsyncContextLockProtocol(LockProtocol, Protocol):
    def __aenter__(self) -> Any:
        raise NotImplementedError('Do not use the protocol as a lock.')
        return None  # pragma: no cover

    def __aexit__(self, exception_type: Optional[Type[BaseException]], exception_value: Optional[BaseException], traceback: Optional[TracebackType]) -> Any:
        raise NotImplementedError('Do not use the protocol as a lock.')
        return None  # pragma: no cover
