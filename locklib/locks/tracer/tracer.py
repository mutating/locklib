from typing import List, Optional, Type
from types import TracebackType
from threading import get_ident
from collections import defaultdict

from locklib.protocols.lock import LockProtocol
from locklib.locks.tracer.events import TracerEvent, TracerEventType
from locklib.errors import StrangeEventOrderError


class LockTraceWrapper:
    def __init__(self, lock: LockProtocol) -> None:
        self.lock = lock
        self.trace: List[TracerEvent] = []

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]) -> Optional[bool]:
        return self.release()

    def acquire(self) -> None:
        self.lock.acquire()
        self.trace.append(
            TracerEvent(
                TracerEventType.ACQUIRE,
                thread_id=get_ident(),
            )
        )

    def release(self) -> None:
        self.lock.release()
        self.trace.append(
            TracerEvent(
                TracerEventType.RELEASE,
                thread_id=get_ident(),
            )
        )

    def notify(self, identifier: str) -> None:
        self.trace.append(
            TracerEvent(
                TracerEventType.ACTION,
                thread_id=get_ident(),
                identifier=identifier,
            )
        )

    def was_event_locked(self, identifier: str) -> bool:
        stacks = defaultdict(list)

        for event in self.trace:
            stack = stacks[event.thread_id]

            if event.type == TracerEventType.ACQUIRE:
                stack.append(event)

            elif event.type == TracerEventType.RELEASE:
                if not stack:
                    raise StrangeEventOrderError('Release event without corresponding acquire event.')
                stack.pop()

            elif event.type == TracerEventType.ACTION:
                if event.identifier == identifier and not stack:
                    return False

        return True
