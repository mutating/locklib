try:
    from threading import (  # type: ignore[attr-defined, unused-ignore]
        Lock,
        get_native_id,
    )
except ImportError:  # pragma: no cover
    from threading import Lock  # get_native_id is available only since python 3.8
    from threading import get_ident as get_native_id

from collections import deque
from types import TracebackType
from typing import Deque, Dict, Optional, Type

from locklib.locks.smart_lock.graph import LocksGraph

graph = LocksGraph()

class SmartLock:
    def __init__(self, local_graph: LocksGraph = graph) -> None:
        self.graph: LocksGraph = local_graph
        self.lock: Lock = Lock()
        self.deque: Deque[int] = deque()
        self.local_locks: Dict[int, Lock] = {}

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(self, exception_type: Optional[Type[BaseException]], exception_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.release()

    def acquire(self) -> None:
        thread_id = get_native_id()
        previous_element_lock = None

        with self.lock, self.graph.lock:
            if not self.deque:
                self.deque.appendleft(thread_id)
                self.local_locks[thread_id] = Lock()
                self.local_locks[thread_id].acquire()
            else:
                previous_element = self.deque[0]
                self.graph.add_link(thread_id, previous_element)
                self.deque.appendleft(thread_id)
                self.local_locks[thread_id] = Lock()
                self.local_locks[thread_id].acquire()
                previous_element_lock = self.local_locks[previous_element]

        if previous_element_lock is not None:
            previous_element_lock.acquire()

    def release(self) -> None:
        thread_id = get_native_id()

        with self.lock, self.graph.lock:
            if thread_id not in self.local_locks:
                raise RuntimeError('Release unlocked lock.')

            self.deque.pop()
            lock = self.local_locks[thread_id]
            del self.local_locks[thread_id]

            if len(self.deque) != 0:
                next_element = self.deque[-1]
                self.graph.delete_link(next_element, thread_id)

            lock.release()
