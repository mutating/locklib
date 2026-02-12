import sys
from asyncio import Lock as ALock
from contextlib import contextmanager
from multiprocessing import Lock as MLock
from threading import Lock as TLock
from threading import RLock as TRLock

import pytest
from full_match import match

from locklib import ContextLockProtocol, SmartLock


@pytest.mark.parametrize(
    'lock',  # type: ignore[no-untyped-def, unused-ignore]
    [
        MLock(),
        TLock(),
        TRLock(),
        SmartLock(),
    ],
)
def test_locks_are_instances_of_context_lock_protocol(lock):  # type: ignore[no-untyped-def, unused-ignore]
    assert isinstance(lock, ContextLockProtocol)


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
def test_other_objects_are_not_instances_of_context_lock(other):  # type: ignore[no-untyped-def, unused-ignore]
    assert not isinstance(other, ContextLockProtocol)


@pytest.mark.skipif(sys.version_info < (3, 9) and sys.version_info > (3, 7), reason='Problems with Python 3.8')
def test_asyncio_lock_is_not_just_context_lock():  # type: ignore[no-untyped-def]
    """
    asyncio lock is an instance of the AsyncContextLockProtocol, not just ContextLockProtocol.
    But! In python 3.8 it is both.
    """
    assert not isinstance(ALock(), ContextLockProtocol)


def test_just_contextmanager_is_not_context_lock():  # type: ignore[no-untyped-def]
    @contextmanager
    def context_manager():  # type: ignore[no-untyped-def]
        yield 'kek'

    assert not isinstance(context_manager(), ContextLockProtocol)


def test_not_implemented_methods_for_context_lock_protocol():  # type: ignore[no-untyped-def]
    class ContextLockProtocolImplementation(ContextLockProtocol):
        pass

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        ContextLockProtocolImplementation().acquire()

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        ContextLockProtocolImplementation().release()

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        ContextLockProtocolImplementation().__enter__()

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        ContextLockProtocolImplementation().__exit__(None, None, None)


def tests_for_type_checking():  # type: ignore[no-untyped-def]
    def some_function(lock: ContextLockProtocol) -> ContextLockProtocol:
        return lock

    some_function(MLock())
    some_function(TLock())
    some_function(TRLock())
    some_function(SmartLock())
