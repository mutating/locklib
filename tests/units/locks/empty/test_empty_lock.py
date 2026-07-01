from threading import Barrier, BrokenBarrierError, Lock, Thread

import pytest

from locklib import EmptyLock


def test_acquire_returns_none_and_does_not_raise():
    """
    EmptyLock.acquire is a no-op that returns None.

    On a fresh instance, calling acquire should not raise and should return exactly None.
    """
    lock = EmptyLock()

    assert lock.acquire() is None


def test_release_returns_none_without_prior_acquire():
    """
    EmptyLock.release is a no-op that returns None without a prior acquire.

    Calling release on a fresh EmptyLock should not raise and should return exactly None.
    """
    lock = EmptyLock()

    assert lock.release() is None


def test_double_acquire_does_not_block():
    """
    EmptyLock can be acquired repeatedly without blocking.

    Calling acquire twice in a row should complete immediately and should not require an intervening release, because EmptyLock does not track ownership or held state.
    """
    lock = EmptyLock()

    lock.acquire()
    lock.acquire()


def test_context_manager_binds_none():
    """
    EmptyLock context manager binds None on entry.

    with EmptyLock() as value should not expose the lock instance or any acquisition token.
    """
    with EmptyLock() as value:
        assert value is None


def test_nested_context_manager_does_not_deadlock():
    """
    A single EmptyLock instance can be entered twice in one with statement.

    Nested context-manager entry on the same no-op lock should complete without blocking or raising.
    """
    lock = EmptyLock()

    with lock, lock:
        pass


def test_exception_inside_context_manager_propagates():
    """
    An EmptyLock context does not suppress exceptions raised inside it.

    A ValueError with the sentinel message should be observed outside the with block.
    """
    lock = EmptyLock()

    with pytest.raises(ValueError, match='kek'), lock:
        raise ValueError('kek')


def test_instance_is_reusable():
    """
    An EmptyLock instance can be reused across repeated locking cycles.

    Mix direct acquire/release calls with with-block usage to confirm each cycle completes independently and leaves no retained state.
    """
    lock = EmptyLock()

    for _ in range(3):
        lock.acquire()
        lock.release()
        with lock:
            pass


def test_no_serialization_between_threads():
    """The empty lock does not serialize threads, unlike a real lock.

    Both threads pass the shared barrier together inside the empty lock, so it
    never has to fall back on the safety timeout. A real ``threading.Lock`` lets
    only one thread in at a time, so the second never reaches the barrier while
    the first waits on it, and they are never inside the section together.
    """
    def both_threads_enter_section_together(lock, barrier_timeout):
        """Return whether two threads can be inside the lock's section at once.

        Both threads must pass a shared barrier from within the critical section,
        so they only succeed if the lock lets them in simultaneously;
        ``barrier_timeout`` bounds the wait so a serializing lock does not hang.
        """
        barrier = Barrier(2)
        entered_together = []

        def function():
            with lock:
                try:
                    barrier.wait(timeout=barrier_timeout)
                except BrokenBarrierError:
                    return
                entered_together.append(True)

        threads = [Thread(target=function) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        return len(entered_together) == 2

    assert both_threads_enter_section_together(EmptyLock(), barrier_timeout=None) is True
    assert both_threads_enter_section_together(Lock(), barrier_timeout=1) is False
