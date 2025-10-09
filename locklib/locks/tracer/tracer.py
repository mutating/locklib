from typing import List, Optional, Type
from types import TracebackType

from locklib.protocols.lock import LockProtocol
from locklib.locks.tracer.events import TracerEvent


class LockTraceWrapper:
    def __init__(self, lock: LockProtocol) -> None:
        self.lock = lock
        self.trace: List[TracerEvent] = []

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]) -> Optional[bool]:
        self.release()

    def acquire(self) -> None:
        self.lock.acquire()
        self.trace.append(TracerEvent.ACQUIRE)

    def release(self) -> None:
        self.lock.release()
        self.trace.append(TracerEvent.RELEASE)
