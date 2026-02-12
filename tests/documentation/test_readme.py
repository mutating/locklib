from asyncio import Lock as ALock
from multiprocessing import Lock as MLock
from threading import Lock as TLock
from threading import RLock as TRLock

from locklib import (
    AsyncContextLockProtocol,
    ContextLockProtocol,
    LockProtocol,
    SmartLock,
)


def test_lock_protocols_basic():
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
    assert isinstance(MLock(), ContextLockProtocol)
    assert isinstance(TLock(), ContextLockProtocol)
    assert isinstance(TRLock(), ContextLockProtocol)
    assert isinstance(SmartLock(), ContextLockProtocol)


def test_asyncio_lock_is_async_context_lock():
    assert isinstance(ALock(), AsyncContextLockProtocol)
