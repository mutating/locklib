from asyncio import Lock as ALock
from multiprocessing import Lock as MLock
from threading import Lock as TLock
from threading import RLock as TRLock

import pytest
from full_match import match

from locklib import AsyncEmptyLock, EmptyLock, LockProtocol, SmartLock, SmartRLock


@pytest.mark.parametrize(
    'lock',  # type: ignore[no-untyped-def, unused-ignore]
    [
        MLock(),
        TLock(),
        TRLock(),
        ALock(),
        SmartLock(),
        SmartRLock(),
        EmptyLock(),
        AsyncEmptyLock(),
    ],
)
def test_locks_are_instances_of_lock_protocol(lock):  # type: ignore[no-untyped-def, unused-ignore]
    """
    The listed stdlib and locklib locks satisfy LockProtocol at runtime.

    This includes both synchronous and asynchronous context-lock implementations because LockProtocol only requires acquire and release.
    """
    assert isinstance(lock, LockProtocol)


@pytest.mark.parametrize(
    'other',  # type: ignore[no-untyped-def, unused-ignore]
    [
        1,
        None,
        'kek',
        'lock',
        [],
        {},
    ],
)
def test_other_objects_are_not_instances_of_lock(other):  # type: ignore[no-untyped-def, unused-ignore]
    """
    Unrelated objects are not accepted as lock protocol instances.

    Verify common non-lock primitives and containers fail isinstance checks so LockProtocol stays limited to objects exposing the lock API.
    """
    assert not isinstance(other, LockProtocol)


def test_not_implemented_methods_for_lock_protocol():  # type: ignore[no-untyped-def]
    """Inherited LockProtocol methods on a minimal subclass raise the exact protocol misuse error."""
    class LockProtocolImplementation(LockProtocol):
        pass

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        LockProtocolImplementation().acquire()

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        LockProtocolImplementation().release()


def tests_for_type_checking():  # type: ignore[no-untyped-def]
    def some_function(lock: LockProtocol) -> LockProtocol:
        return lock

    some_function(MLock())
    some_function(TLock())
    some_function(TRLock())
    some_function(ALock())
    some_function(SmartLock())
    some_function(SmartRLock())
    some_function(EmptyLock())
    some_function(AsyncEmptyLock())
