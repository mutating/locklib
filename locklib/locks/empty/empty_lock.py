from types import TracebackType
from typing import Optional, Type


class EmptyLock:
    """Provide the context-lock interface while deliberately doing no locking.

    Useful when some code expects a lock but no synchronization is actually
    needed, so a no-op lock can be injected instead of branching on whether to
    lock. It is stateless, so it never blocks and can be reused freely.
    """

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(self, exception_type: Optional[Type[BaseException]], exception_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.release()

    def acquire(self) -> None:
        ...

    def release(self) -> None:
        ...
