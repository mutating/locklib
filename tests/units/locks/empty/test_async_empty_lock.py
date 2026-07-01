import asyncio

import pytest

from locklib import AsyncEmptyLock


async def test_acquire_does_not_raise():
    """acquire returns None per its signature and must not raise."""
    lock = AsyncEmptyLock()

    await lock.acquire()


def test_release_returns_none_without_prior_acquire():
    """
    Release on an unacquired async empty lock returns None immediately.

    The lock is stateless, so release does not require ownership, a prior acquire, or awaiting.
    """
    lock = AsyncEmptyLock()

    assert lock.release() is None


async def test_double_acquire_does_not_block():
    """
    AsyncEmptyLock acquire remains a non-blocking no-op across repeated awaits.

    The same instance can be acquired twice without an intervening release, and the second acquire should complete immediately.
    """
    lock = AsyncEmptyLock()

    await lock.acquire()
    await lock.acquire()


async def test_context_manager_binds_none():
    """
    An async empty lock context manager binds None on entry.

    async with AsyncEmptyLock() as value should complete successfully without exposing the lock instance or a token.
    """
    async with AsyncEmptyLock() as value:
        assert value is None


async def test_nested_context_manager_does_not_deadlock():
    """
    AsyncEmptyLock supports nested async context manager use without blocking.

    The same lock instance is entered twice with nested async with blocks, and both contexts must complete because the empty lock does not track ownership or held state.
    """
    lock = AsyncEmptyLock()

    async with lock, lock:
        pass


async def test_exception_inside_context_manager_propagates():
    """
    Exceptions raised inside an AsyncEmptyLock context are not suppressed.

    Raise a ValueError inside the context and assert that a ValueError with the sentinel message is observed outside.
    """
    lock = AsyncEmptyLock()

    with pytest.raises(ValueError, match='kek'):
        async with lock:
            raise ValueError('kek')


async def test_instance_is_reusable():
    """
    One AsyncEmptyLock instance stays reusable across sequential locking cycles.

    The same object can mix explicit acquire/release calls and async context-manager use without retaining state between cycles.
    """
    lock = AsyncEmptyLock()

    for _ in range(3):
        await lock.acquire()
        lock.release()
        async with lock:
            pass


async def test_no_serialization_between_coroutines():
    """The empty lock does not serialize tasks, unlike a real lock.

    Both tasks are inside the empty lock's section at once. A real ``asyncio.Lock``
    serializes them: the second task cannot acquire it while the first holds it,
    so the scenario deadlocks, surfaced here as a timeout so the test does not hang.
    """
    async def both_tasks_enter_section_together(lock):
        """Return whether two tasks can be inside the lock's section at once.

        The first task enters and waits, inside the lock, for the second one to
        enter too. They can only meet if the lock lets both in simultaneously; a
        real lock blocks the second task on acquire, so the scenario never ends.
        """
        second_entered = asyncio.Event()

        async def first() -> None:
            async with lock:
                await second_entered.wait()

        async def second() -> None:
            async with lock:
                second_entered.set()

        await asyncio.gather(first(), second())

        return second_entered.is_set()

    assert await both_tasks_enter_section_together(AsyncEmptyLock()) is True

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(both_tasks_enter_section_together(asyncio.Lock()), timeout=0.1)
