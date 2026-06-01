from types import TracebackType
from typing import Optional, Type


class AsyncEmptyLock:
    """Provide the async-context-lock interface while deliberately doing no locking.

    The asynchronous counterpart of ``EmptyLock``: it mirrors the shape of
    ``asyncio.Lock`` (an awaitable ``acquire`` and a synchronous ``release``)
    but performs no synchronization. It is stateless, so it never blocks and
    can be reused freely.
    """

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, exception_type: Optional[Type[BaseException]], exception_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.release()

    async def acquire(self) -> None:
        ...

    def release(self) -> None:
        ...
