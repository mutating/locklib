from asyncio import Lock as ALock
from multiprocessing import Lock as MLock
from threading import Lock as TLock
from threading import RLock as TRLock

from locklib import (
    AsyncContextLockProtocol,
    AsyncEmptyLock,
    ContextLockProtocol,
    EmptyLock,
    LockProtocol,
    SmartLock,
)


def test_lock_protocols_basic():
    """
    The README lock examples satisfy LockProtocol at runtime.

    This checks multiprocessing.Lock, threading.Lock, threading.RLock, asyncio.Lock, and SmartLock by protocol membership, without exercising locking behavior.
    """
    assert isinstance(MLock(), LockProtocol)
    assert isinstance(TLock(), LockProtocol)
    assert isinstance(TRLock(), LockProtocol)
    assert isinstance(ALock(), LockProtocol)
    assert isinstance(SmartLock(), LockProtocol)


def test_inheritance_order():
    """
    Prove that we have this inheritance order:

    LockProtocol
     ├── ContextLockProtocol
     └── AsyncContextLockProtocol
    """
    assert issubclass(ContextLockProtocol, LockProtocol)
    assert issubclass(AsyncContextLockProtocol, LockProtocol)


def test_almost_all_lock_are_context_locks():
    """
    ContextLockProtocol describes the listed synchronous locks as context-manager locks.

    The README smoke test checks multiprocessing.Lock, threading.Lock, threading.RLock, and SmartLock by runtime protocol membership without exercising their locking behavior.
    """
    assert isinstance(MLock(), ContextLockProtocol)
    assert isinstance(TLock(), ContextLockProtocol)
    assert isinstance(TRLock(), ContextLockProtocol)
    assert isinstance(SmartLock(), ContextLockProtocol)


def test_asyncio_lock_is_async_context_lock():
    """
    asyncio.Lock satisfies the async context lock protocol at runtime.

    The test checks interface recognition for asyncio.Lock without exercising locking behavior or asserting anything about synchronous context-manager protocols.
    """
    assert isinstance(ALock(), AsyncContextLockProtocol)


def test_empty_lock_usage_and_protocols():
    """EmptyLock can be used as a context manager and satisfies LockProtocol and ContextLockProtocol."""
    lock = EmptyLock()

    with lock:
        pass

    assert isinstance(lock, LockProtocol)
    assert isinstance(lock, ContextLockProtocol)


async def test_async_empty_lock_usage_and_protocols():
    """AsyncEmptyLock can be used as an async context manager and satisfies LockProtocol and AsyncContextLockProtocol."""
    lock = AsyncEmptyLock()

    async with lock:
        pass

    assert isinstance(lock, LockProtocol)
    assert isinstance(lock, AsyncContextLockProtocol)
