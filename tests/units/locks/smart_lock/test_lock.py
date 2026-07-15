from threading import Event, Lock, Thread, get_native_id
from time import monotonic
from typing import List, Type

import pytest
from full_match import match

from locklib import DeadLockError, SmartLock, SmartRLock
from locklib.locks.smart_lock.abstract import AbstractSmartLock
from locklib.locks.smart_lock.graph import LocksGraph


@pytest.mark.timeout(5)
def test_smart_lock_raises_on_recursive_acquire_instead_of_hanging() -> None:
    """SmartLock rejects recursive acquire without hanging, remains reusable, and rejects recursion again."""
    lock = SmartLock()
    unexpected_errors: List[Exception] = []

    def verify_recursive_acquire_rejections() -> None:
        try:
            thread_id = get_native_id()
            expected_message = f'A cycle between {thread_id}th and {thread_id}th threads has been detected.'

            for _ in range(2):
                lock.acquire()

                with pytest.raises(DeadLockError, match=match(expected_message)):
                    lock.acquire()

                lock.release()
        except Exception as error:  # noqa: BLE001
            unexpected_errors.append(error)

    thread = Thread(target=verify_recursive_acquire_rejections, daemon=True)
    thread.start()
    thread.join(2)

    assert not thread.is_alive()
    if unexpected_errors:
        raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]


@pytest.mark.timeout(5)
def test_smart_lock_recursive_acquire_error_preserves_lock_and_graph_state() -> None:
    """SmartLock recursive-acquire errors preserve reusable lock and graph state."""
    graph = LocksGraph()
    lock = SmartLock(local_graph=graph)
    unexpected_errors: List[Exception] = []

    def exercise_recursive_acquire_recovery() -> None:
        try:
            thread_id = get_native_id()
            expected_message = f'A cycle between {thread_id}th and {thread_id}th threads has been detected.'

            lock.acquire()

            with pytest.raises(DeadLockError, match=match(expected_message)):
                lock.acquire()

            lock.release()
            with lock.lock:
                assert not lock.deque
                assert not lock.local_locks
                assert not lock.recursion_depths

            lock.acquire()
            lock.release()
        except Exception as error:  # noqa: BLE001
            unexpected_errors.append(error)

    thread = Thread(target=exercise_recursive_acquire_recovery, daemon=True)
    thread.start()
    thread.join(2)

    assert not thread.is_alive()
    if unexpected_errors:
        raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
    assert not graph.links
    with lock.lock:
        assert not lock.deque
        assert not lock.local_locks
        assert not lock.recursion_depths


@pytest.mark.parametrize(
    ('first_lock_class', 'second_lock_class'),
    [
        (SmartLock, SmartRLock),
        (SmartRLock, SmartLock),
    ],
)
@pytest.mark.timeout(10)
def test_mixed_smart_lock_and_smart_rlock_detect_deadlock(first_lock_class: Type[AbstractSmartLock], second_lock_class: Type[AbstractSmartLock]) -> None:  # noqa: PLR0915
    """SmartLock and SmartRLock share an explicit local graph and detect a two-lock deadlock in either order."""
    graph = LocksGraph()
    lock_1 = first_lock_class(local_graph=graph)
    lock_2 = second_lock_class(local_graph=graph)
    deadline = monotonic() + 2.5
    first_lock_acquired_events = [Event(), Event()]
    request_second_lock_event = Event()
    result_lock = Lock()
    deadlock_errors: List[DeadLockError] = []
    unexpected_errors: List[Exception] = []

    def acquire_locks(owned_lock: AbstractSmartLock, requested_lock: AbstractSmartLock, first_lock_acquired_event: Event) -> None:
        owns_first_lock = False
        owns_second_lock = False

        try:
            owned_lock.acquire()
            owns_first_lock = True
            first_lock_acquired_event.set()

            if not request_second_lock_event.wait(max(deadline - monotonic(), 0.01)):
                raise TimeoutError('Coordinator did not release second-lock attempt.')

            requested_lock.acquire()
            owns_second_lock = True
        except DeadLockError as error:
            with result_lock:
                deadlock_errors.append(error)
        except Exception as error:  # noqa: BLE001
            with result_lock:
                unexpected_errors.append(error)
        finally:
            try:
                if owns_second_lock:
                    requested_lock.release()
                if owns_first_lock:
                    owned_lock.release()
            except Exception as error:  # noqa: BLE001
                with result_lock:
                    unexpected_errors.append(error)

    threads = [
        Thread(target=acquire_locks, args=(lock_1, lock_2, first_lock_acquired_events[0]), daemon=True),
        Thread(target=acquire_locks, args=(lock_2, lock_1, first_lock_acquired_events[1]), daemon=True),
    ]

    for thread in threads:
        thread.start()

    all_threads_ready = False
    try:
        all_threads_ready = all(event.wait(max(deadline - monotonic(), 0.01)) for event in first_lock_acquired_events)
    finally:
        request_second_lock_event.set()
        for thread in threads:
            thread.join(1)

    if unexpected_errors:
        raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
    assert all_threads_ready
    assert all(not thread.is_alive() for thread in threads)
    assert len(deadlock_errors) == 1
    assert all(not links for links in graph.links.values())

    for lock in (lock_1, lock_2):
        with lock.lock:
            assert not lock.deque
            assert not lock.local_locks
            assert not lock.recursion_depths
        lock.acquire()
        lock.release()
        with lock.lock:
            assert not lock.deque
            assert not lock.local_locks
            assert not lock.recursion_depths
