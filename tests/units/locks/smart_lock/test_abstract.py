from threading import Event, Lock, Thread
from time import monotonic, sleep
from typing import List, Sequence, Type

import pytest
from full_match import match

from locklib.errors import DeadLockError
from locklib.locks.smart_lock.abstract import AbstractSmartLock
from locklib.locks.smart_lock.abstract import graph as shared_graph
from locklib.locks.smart_lock.graph import LocksGraph


def test_abstract_smart_lock_subclass_is_abstract_smart_lock_subclass(smartlock_class: Type[AbstractSmartLock]) -> None:
    """Every public smart lock class inherits from AbstractSmartLock."""
    assert issubclass(smartlock_class, AbstractSmartLock)


def test_abstract_smart_lock_subclass_release_unlocked(smartlock_class: Type[AbstractSmartLock]) -> None:
    """Every public AbstractSmartLock subclass rejects release without ownership."""
    lock = smartlock_class()

    with pytest.raises(RuntimeError, match=match('Release unlocked lock.')):
        lock.release()


def test_abstract_smart_lock_subclass_protects_shared_state(smartlock_class: Type[AbstractSmartLock]) -> None:
    """Every public AbstractSmartLock subclass serializes contended increments without losing updates."""
    number_of_threads = 5
    number_of_increments_per_thread = 1000

    lock = smartlock_class(local_graph=LocksGraph())
    counter = 0
    errors_lock = Lock()
    unexpected_errors: List[Exception] = []

    def increment_counter() -> None:
        nonlocal counter

        try:
            for _ in range(number_of_increments_per_thread):
                with lock:
                    counter_snapshot = counter
                    sleep(0)
                    counter = counter_snapshot + 1
        except Exception as error:  # noqa: BLE001
            with errors_lock:
                unexpected_errors.append(error)

    threads = [Thread(target=increment_counter, daemon=True) for _ in range(number_of_threads)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(2)

    assert all(not thread.is_alive() for thread in threads)

    if unexpected_errors:
        raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
    assert counter == number_of_threads * number_of_increments_per_thread


@pytest.mark.timeout(5)
def test_abstract_smart_lock_subclass_cleans_wait_for_graph_after_contention(smartlock_class: Type[AbstractSmartLock]) -> None:
    """
    Every public AbstractSmartLock subclass cleans up its wait-for graph after contention.

    With the lock held, a waiter creates a waiter-to-owner edge. Releasing the lock lets the waiter finish and leaves the queue and dedicated graph empty.
    """
    graph = LocksGraph()
    lock = smartlock_class(local_graph=graph)
    unexpected_errors: List[Exception] = []

    def acquire_lock() -> None:
        try:
            with lock:
                pass
        except Exception as error:  # noqa: BLE001
            unexpected_errors.append(error)

    waiter_thread = Thread(target=acquire_lock, daemon=True)
    contention_observed = False

    try:
        with lock:
            waiter_thread.start()
            deadline = monotonic() + 2.5

            while monotonic() < deadline:
                with lock.lock, graph.lock:
                    if len(lock.deque) == 2:
                        waiter_thread_id, owner_thread_id = lock.deque
                        assert graph.links == {waiter_thread_id: {owner_thread_id}}
                        contention_observed = True
                        break
                sleep(0.001)
    finally:
        if waiter_thread.ident is not None:
            waiter_thread.join(1)

    assert not waiter_thread.is_alive()
    if unexpected_errors:
        raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
    assert contention_observed, 'Waiter did not enter the lock queue.'
    with lock.lock:
        assert not lock.deque
    assert graph.links == {}


@pytest.mark.timeout(10)
def test_abstract_smart_lock_subclass_detects_simple_deadlock(smartlock_class: Type[AbstractSmartLock]) -> None:  # noqa: PLR0915
    """Every public AbstractSmartLock subclass breaks a two-thread deadlock with one DeadLockError and graph cleanup."""
    number_of_attempts = 50
    graph = LocksGraph()
    lock_1 = smartlock_class(local_graph=graph)
    lock_2 = smartlock_class(local_graph=graph)

    def acquire_locks(  # noqa: PLR0913
        owned_lock: AbstractSmartLock,
        requested_lock: AbstractSmartLock,
        first_lock_acquired_event: Event,
        request_second_lock_event: Event,
        deadline: float,
        result_lock: Lock,
        deadlock_errors: List[DeadLockError],
        unexpected_errors: List[Exception],
    ) -> None:
        try:
            with owned_lock:
                first_lock_acquired_event.set()

                if not request_second_lock_event.wait(max(deadline - monotonic(), 0.01)):
                    raise TimeoutError('Coordinator did not release second-lock attempt.')

                with requested_lock:
                    pass
        except DeadLockError as error:
            with result_lock:
                deadlock_errors.append(error)
        except Exception as error:  # noqa: BLE001
            with result_lock:
                unexpected_errors.append(error)

    for _ in range(number_of_attempts):
        deadline = monotonic() + 2.5
        first_lock_acquired_events = [Event(), Event()]
        request_second_lock_event = Event()
        result_lock = Lock()
        deadlock_errors: List[DeadLockError] = []
        unexpected_errors: List[Exception] = []

        threads = [
            Thread(
                target=acquire_locks,
                args=(lock_1, lock_2, first_lock_acquired_events[0], request_second_lock_event, deadline, result_lock, deadlock_errors, unexpected_errors),
                daemon=True,
            ),
            Thread(
                target=acquire_locks,
                args=(lock_2, lock_1, first_lock_acquired_events[1], request_second_lock_event, deadline, result_lock, deadlock_errors, unexpected_errors),
                daemon=True,
            ),
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


@pytest.mark.timeout(10)
def test_abstract_smart_lock_subclass_detects_three_lock_deadlock(smartlock_class: Type[AbstractSmartLock]) -> None:
    """Every public AbstractSmartLock subclass breaks a three-lock cyclic wait with two DeadLockErrors and graph cleanup."""
    number_of_attempts = 50
    graph = LocksGraph()
    locks = [
        smartlock_class(local_graph=graph),
        smartlock_class(local_graph=graph),
        smartlock_class(local_graph=graph),
    ]

    def acquire_locks(  # noqa: PLR0913
        index: int,
        ordered_locks: Sequence[AbstractSmartLock],
        first_lock_acquired_events: Sequence[Event],
        request_other_locks_event: Event,
        deadline: float,
        result_lock: Lock,
        deadlock_errors: List[DeadLockError],
        unexpected_errors: List[Exception],
    ) -> None:
        try:
            with ordered_locks[0]:
                first_lock_acquired_events[index].set()

                if not request_other_locks_event.wait(max(deadline - monotonic(), 0.01)):
                    raise TimeoutError('Coordinator did not release remaining lock attempts.')

                with ordered_locks[1], ordered_locks[2]:
                    pass
        except DeadLockError as error:
            with result_lock:
                deadlock_errors.append(error)
        except Exception as error:  # noqa: BLE001
            with result_lock:
                unexpected_errors.append(error)

    for _ in range(number_of_attempts):
        deadline = monotonic() + 2.5
        result_lock = Lock()
        first_lock_acquired_events = [Event(), Event(), Event()]
        request_other_locks_event = Event()
        deadlock_errors: List[DeadLockError] = []
        unexpected_errors: List[Exception] = []

        threads = [
            Thread(
                target=acquire_locks,
                args=(0, (locks[0], locks[1], locks[2]), first_lock_acquired_events, request_other_locks_event, deadline, result_lock, deadlock_errors, unexpected_errors),
                daemon=True,
            ),
            Thread(
                target=acquire_locks,
                args=(1, (locks[1], locks[2], locks[0]), first_lock_acquired_events, request_other_locks_event, deadline, result_lock, deadlock_errors, unexpected_errors),
                daemon=True,
            ),
            Thread(
                target=acquire_locks,
                args=(2, (locks[2], locks[0], locks[1]), first_lock_acquired_events, request_other_locks_event, deadline, result_lock, deadlock_errors, unexpected_errors),
                daemon=True,
            ),
        ]

        for thread in threads:
            thread.start()

        all_threads_ready = False
        try:
            all_threads_ready = all(event.wait(max(deadline - monotonic(), 0.01)) for event in first_lock_acquired_events)
        finally:
            request_other_locks_event.set()
            for thread in threads:
                thread.join(1)

        if unexpected_errors:
            raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
        assert all_threads_ready
        assert all(not thread.is_alive() for thread in threads)
        assert len(deadlock_errors) == 2
        assert all(not links for links in graph.links.values())

        for lock in locks:
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


@pytest.mark.timeout(10)
def test_abstract_smart_lock_subclass_default_instances_share_deadlock_graph(smartlock_class: Type[AbstractSmartLock]) -> None:  # noqa: PLR0915
    """Default-constructed public AbstractSmartLock subclasses share the graph used for deadlock detection."""
    number_of_attempts = 50

    def clear_shared_graph() -> None:
        with shared_graph.lock:
            shared_graph.links.clear()

    def acquire_locks(  # noqa: PLR0913
        owned_lock: AbstractSmartLock,
        requested_lock: AbstractSmartLock,
        first_lock_acquired_event: Event,
        request_second_lock_event: Event,
        deadline: float,
        result_lock: Lock,
        deadlock_errors: List[DeadLockError],
        unexpected_errors: List[Exception],
    ) -> None:
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

    clear_shared_graph()
    try:
        for _ in range(number_of_attempts):
            lock_1 = smartlock_class()
            lock_2 = smartlock_class()
            deadline = monotonic() + 2.5
            first_lock_acquired_events = [Event(), Event()]
            request_second_lock_event = Event()
            result_lock = Lock()
            deadlock_errors: List[DeadLockError] = []
            unexpected_errors: List[Exception] = []

            threads = [
                Thread(
                    target=acquire_locks,
                    args=(lock_1, lock_2, first_lock_acquired_events[0], request_second_lock_event, deadline, result_lock, deadlock_errors, unexpected_errors),
                    daemon=True,
                ),
                Thread(
                    target=acquire_locks,
                    args=(lock_2, lock_1, first_lock_acquired_events[1], request_second_lock_event, deadline, result_lock, deadlock_errors, unexpected_errors),
                    daemon=True,
                ),
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
    finally:
        clear_shared_graph()


def test_abstract_smart_lock_subclass_context_manager_blocks_other_threads_until_exit(smartlock_class: Type[AbstractSmartLock]) -> None:
    """Every public AbstractSmartLock subclass holds the lock until context-manager exit."""
    graph = LocksGraph()
    lock = smartlock_class(local_graph=graph)
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

    try:
        with lock:
            thread = Thread(target=enter_lock, daemon=True)
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


def test_abstract_smart_lock_subclass_release_from_non_owner_thread_raises(smartlock_class: Type[AbstractSmartLock]) -> None:
    """Every public AbstractSmartLock subclass rejects release from a non-owner thread."""
    lock = smartlock_class()
    release_error_messages: List[str] = []
    unexpected_errors: List[Exception] = []

    def release_without_ownership() -> None:
        try:
            lock.release()
        except RuntimeError as error:
            release_error_messages.append(str(error))
        except Exception as error:  # noqa: BLE001
            unexpected_errors.append(error)

    lock.acquire()

    thread = Thread(target=release_without_ownership, daemon=True)
    try:
        thread.start()
        thread.join(1)

        assert not thread.is_alive()
        if unexpected_errors:
            raise AssertionError(f'Unexpected worker exceptions: {unexpected_errors!r}') from unexpected_errors[0]
        assert release_error_messages == ['Release unlocked lock.']
    finally:
        lock.release()
