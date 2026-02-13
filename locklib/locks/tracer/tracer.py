from collections import defaultdict
from threading import get_ident
from types import TracebackType
from typing import Dict, List, Optional, Type

from locklib.errors import StrangeEventOrderError, ThereWasNoSuchEvent
from locklib.locks.tracer.events import TracerEvent, TracerEventType
from locklib.protocols.lock import LockProtocol


class LockTraceWrapper:
    def __init__(self, lock: LockProtocol) -> None:
        self.lock = lock
        self.trace: List[TracerEvent] = []

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]) -> None:
        self.release()

    def acquire(self) -> None:
        self.lock.acquire()
        self.trace.append(
            TracerEvent(
                TracerEventType.ACQUIRE,
                thread_id=get_ident(),
            ),
        )

    def release(self) -> None:
        self.lock.release()
        self.trace.append(
            TracerEvent(
                TracerEventType.RELEASE,
                thread_id=get_ident(),
            ),
        )

    def notify(self, identifier: str) -> None:
        self.trace.append(
            TracerEvent(
                TracerEventType.ACTION,
                thread_id=get_ident(),
                identifier=identifier,
            ),
        )

    def was_event_locked(self, identifier: str, raise_exception: bool = True) -> bool:
        stacks: Dict[int, List[TracerEvent]] = defaultdict(list)

        there_was_action_with_this_identifier = False

        for event in self.trace:
            stack = stacks[event.thread_id]

            if event.type == TracerEventType.ACQUIRE:
                stack.append(event)

            elif event.type == TracerEventType.RELEASE:
                if not stack:
                    if raise_exception:
                        raise StrangeEventOrderError('Release event without corresponding acquire event.')
                    return False
                stack.pop()

            elif event.type == TracerEventType.ACTION:
                if event.identifier == identifier:
                    there_was_action_with_this_identifier = True
                    if not stack:
                        return False

        if (not there_was_action_with_this_identifier) and raise_exception:
            raise ThereWasNoSuchEvent(f'No events with identifier "{identifier}" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')

        return there_was_action_with_this_identifier
