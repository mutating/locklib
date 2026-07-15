from threading import Event, Thread, get_native_id
from typing import List

import pytest
from full_match import match

from locklib import SmartRLock
from locklib.locks.smart_lock.abstract import AbstractSmartLock
from locklib.locks.smart_lock.graph import LocksGraph


def test_smart_rlock_is_abstract_smart_lock_subclass() -> None:
    """SmartRLock remains an AbstractSmartLock subclass in recursive mode."""
    assert issubclass(SmartRLock, AbstractSmartLock)
    assert SmartRLock.recursive is True


@pytest.mark.parametrize('number_of_acquires', range(11))
def test_smart_rlock_allows_recursive_acquire_and_requires_matching_releases(number_of_acquires: int) -> None:
    """SmartRLock requires one release per acquire for depths 0 through 10, then raises unlocked-lock RuntimeError."""
    lock = SmartRLock()

    for _ in range(number_of_acquires):
        lock.acquire()

    for _ in range(number_of_acquires):
        lock.release()

    with pytest.raises(RuntimeError, match=match('Release unlocked lock.')):
        lock.release()


def test_smart_rlock_nested_context_manager_keeps_lock_until_outer_exit() -> None:
    """SmartRLock keeps ownership after leaving an inner recursive context manager."""
    graph = LocksGraph()
    lock = SmartRLock(local_graph=graph)
    attempting_event = Event()
    entered_event = Event()
    unexpected_errors: List[Exception] = []

    def enter_lock() -> None:
        try:
            attempting_event.set()
            with lock:
                entered_event.set()
        except Exception as error:  # noqa: BLE001
            unexpected_errors.append(error)

    thread = Thread(target=enter_lock, daemon=True)

    try:
        with lock:
            with lock:
                pass

            thread.start()

            if not attempting_event.wait(1):
                thread.join(1)
                if unexpected_errors:
                    raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
                raise AssertionError(f'Worker did not attempt to enter lock. unexpected_errors={unexpected_errors!r}')

            assert not entered_event.wait(0.1)
    finally:
        thread.join(1)

    assert not thread.is_alive()
    if unexpected_errors:
        raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
    assert entered_event.is_set()
    with lock.lock:
        assert not lock.deque
        assert not lock.local_locks
        assert not lock.recursion_depths


def test_smart_rlock_partial_release_does_not_unlock_for_other_threads() -> None:
    """SmartRLock keeps ownership after a partial recursive release."""
    graph = LocksGraph()
    lock = SmartRLock(local_graph=graph)
    owner_thread_id = get_native_id()

    lock.acquire()
    lock.acquire()
    releases_left = 2
    attempting_event = Event()
    entered_event = Event()
    unexpected_errors: List[Exception] = []

    def enter_lock() -> None:
        try:
            attempting_event.set()
            with lock:
                entered_event.set()
        except Exception as error:  # noqa: BLE001
            unexpected_errors.append(error)

    thread = Thread(target=enter_lock, daemon=True)

    try:
        thread.start()

        if not attempting_event.wait(1):
            thread.join(1)
            if unexpected_errors:
                raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
            raise AssertionError(f'Worker did not attempt to enter lock. unexpected_errors={unexpected_errors!r}')

        lock.release()
        releases_left -= 1

        with lock.lock:
            assert lock.deque[-1] == owner_thread_id
            assert lock.recursion_depths[owner_thread_id] == 1
        assert not entered_event.wait(0.1)

        lock.release()
        releases_left -= 1
    finally:
        try:
            for _ in range(releases_left):
                lock.release()
        finally:
            thread.join(1)

    assert not thread.is_alive()
    if unexpected_errors:
        raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
    assert entered_event.is_set()


def test_smart_rlock_recursive_acquire_does_not_touch_graph() -> None:
    """SmartRLock recursive acquire leaves the wait-for graph unchanged."""
    graph = LocksGraph()
    lock = SmartRLock(local_graph=graph)

    lock.acquire()
    assert not graph.links

    lock.acquire()

    assert not graph.links

    lock.release()
    lock.release()
    assert not graph.links


def test_smart_rlock_recursion_depth_resets_after_full_release() -> None:
    """SmartRLock clears recursive depth after fully releasing the lock."""
    lock = SmartRLock()

    for _ in range(3):
        lock.acquire()

    for _ in range(3):
        lock.release()

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

    with pytest.raises(RuntimeError, match=match('Release unlocked lock.')):
        lock.release()
