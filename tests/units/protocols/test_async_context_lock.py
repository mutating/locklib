from asyncio import Lock as ALock
from contextlib import asynccontextmanager
from multiprocessing import Lock as MLock
from threading import Lock as TLock
from threading import RLock as TRLock

import pytest
from full_match import match

from locklib import AsyncContextLockProtocol, SmartLock


@pytest.mark.parametrize(
    'lock',  # type: ignore[no-untyped-def, unused-ignore]
    [
        ALock(),
    ],
)
def test_locks_are_instances_of_context_lock_protocol(lock):  # type: ignore[no-untyped-def, unused-ignore]
    assert isinstance(lock, AsyncContextLockProtocol)


@pytest.mark.parametrize(
    'other',  # type: ignore[no-untyped-def, unused-ignore]
    [
        1,
        None,
        'kek',
        'lock',
        [],
        {},
        MLock(),
        TLock(),
        TRLock(),
        SmartLock(),
    ],
)
def test_other_objects_are_not_instances_of_context_lock(other):  # type: ignore[no-untyped-def, unused-ignore]
    assert not isinstance(other, AsyncContextLockProtocol)


def test_just_async_contextmanager_is_not_async_context_lock():  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def context_manager():  # type: ignore[no-untyped-def]
        yield 'kek'

    assert not isinstance(context_manager(), AsyncContextLockProtocol)


def test_not_implemented_methods_for_async_context_lock_protocol():  # type: ignore[no-untyped-def]
    class AsyncContextLockProtocolImplementation(AsyncContextLockProtocol):
        pass

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        AsyncContextLockProtocolImplementation().acquire()

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        AsyncContextLockProtocolImplementation().release()

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        AsyncContextLockProtocolImplementation().__aenter__()

    with pytest.raises(NotImplementedError, match=match('Do not use the protocol as a lock.')):
        AsyncContextLockProtocolImplementation().__aexit__(None, None, None)


def tests_for_type_checking():  # type: ignore[no-untyped-def]
    def some_function(lock: AsyncContextLockProtocol) -> AsyncContextLockProtocol:
        return lock

    some_function(ALock())
