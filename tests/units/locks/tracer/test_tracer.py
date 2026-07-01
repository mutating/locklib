from threading import Lock, Thread, get_ident
from time import sleep
from typing import List, Union

import pytest
from full_match import match

from locklib import LockTraceWrapper, StrangeEventOrderError, ThereWasNoSuchEventError
from locklib.locks.tracer.events import TracerEvent, TracerEventType


def test_base_trace_with_methods():
    """
    Delegated acquire and release calls are traced after each wrapped method returns.

    The pseudo-lock records its own markers; the wrapper should append the matching ACQUIRE or RELEASE event immediately after each marker.
    """
    class PseudoLock:
        def acquire(self):
            self.trace.append('acquire')
        def release(self):
            self.trace.append('release')
        def set_trace_collection(self, trace: List[Union[str, TracerEvent]]):
            self.trace = trace

    pseudo_lock = PseudoLock()
    wrapper = LockTraceWrapper(pseudo_lock)
    pseudo_lock.set_trace_collection(wrapper.trace)

    wrapper.acquire()
    wrapper.release()

    assert wrapper.trace == ['acquire', TracerEvent(TracerEventType.ACQUIRE, get_ident()), 'release', TracerEvent(TracerEventType.RELEASE, get_ident())]


def test_base_trace_with_context_manager():
    """A LockTraceWrapper context manager delegates to acquire and release in order.

    Wrap a lock whose methods record markers, enter an empty with block, and assert the wrapper appends matching ACQUIRE and RELEASE events after those calls.
    """
    class PseudoLock:
        def acquire(self):
            self.trace.append('acquire')
        def release(self):
            self.trace.append('release')
        def set_trace_collection(self, trace: List[Union[str, TracerEvent]]):
            self.trace = trace

    pseudo_lock = PseudoLock()
    wrapper = LockTraceWrapper(pseudo_lock)
    pseudo_lock.set_trace_collection(wrapper.trace)

    with wrapper:
        pass

    assert wrapper.trace == ['acquire', TracerEvent(TracerEventType.ACQUIRE, get_ident()), 'release', TracerEvent(TracerEventType.RELEASE, get_ident())]


def test_notify_adds_new_event():
    """
    notify appends one ACTION event for the current thread.

    Calling notify(identifier) should add exactly one TracerEvent with type ACTION and the provided identifier.
    """
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('kek')

    assert len(wrapper.trace) == 1
    assert wrapper.trace[0] == TracerEvent(TracerEventType.ACTION, get_ident(), 'kek')


def test_try_to_release_event_without_corresponding_acquire_event():
    """
    An unmatched RELEASE event makes the trace order invalid.

    was_event_locked raises StrangeEventOrderError unless exceptions are disabled, in which case it returns False.
    """
    class PseudoLock:
        def acquire(self):
            pass
        def release(self):
            pass

    wrapper = LockTraceWrapper(PseudoLock())

    wrapper.release()

    assert len(wrapper.trace) == 1
    assert wrapper.trace[0] == TracerEvent(TracerEventType.RELEASE, get_ident())

    with pytest.raises(StrangeEventOrderError):
        wrapper.was_event_locked('kek')

    with pytest.raises(StrangeEventOrderError):
        wrapper.was_event_locked('kek', raise_exception=True)

    assert not wrapper.was_event_locked('kek', raise_exception=False)


def test_event_is_locked_if_there_was_no_events():
    """
    An empty trace follows the missing-event path.

    was_event_locked returns False with raise_exception=False and otherwise raises ThereWasNoSuchEventError with the exact missing-event message.
    """
    wrapper = LockTraceWrapper(Lock())

    assert not wrapper.was_event_locked('kek', raise_exception=False)

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek')

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek', raise_exception=True)


def test_event_is_locked_if_there_are_only_opening_and_slosing_events():
    """
    A balanced acquire/release trace without the target ACTION is still missing the event.

    It returns False with exceptions disabled and otherwise raises ThereWasNoSuchEventError.
    """
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        pass

    assert not wrapper.was_event_locked('kek', raise_exception=False)

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek')

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek', raise_exception=True)


def test_simple_case_of_locked_event():
    """
    An event recorded inside a completed lock context is treated as locked.

    was_event_locked should return True after the context exits, since the lock only needed to be held when notify was called.
    """
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('kek')

    assert wrapper.was_event_locked('kek')


def test_simple_case_of_locked_multiple_events():
    """
    Repeated matching events inside one completed lock section are treated as locked.

    Record several actions with the same identifier under one context and assert was_event_locked returns True.
    """
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')

    assert wrapper.was_event_locked('kek')


def test_locked_events_with_only_acquire():
    """
    An event after an acquire is considered locked even if the lock has not been released yet.

    was_event_locked treats matching actions in the same thread as protected while the acquire stack remains open.
    """
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')

        assert wrapper.was_event_locked('kek')


def test_multiple_locked_events_in_100_threads():
    """
    Matching events are checked against each event's own thread lock span.

    Start many threads that each acquire the wrapper once, emit many matching ACTION notifications inside that context, and release it; every matching action should be treated as locked.
    """
    wrapper = LockTraceWrapper(Lock())

    def function():
        with wrapper:
            for _ in range(1000):
                wrapper.notify('kek')
        sleep(0.1)

    threads = [Thread(target=function) for _ in range(100)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert wrapper.was_event_locked('kek')


def test_multiple_locked_events_and_1_not_locked_in_100_threads():
    """
    Return False when any matching event is emitted without that thread acquiring the wrapper.

    Many threads emit locked ACTION events; one thread emits the same identifier without entering the wrapper, so was_event_locked rejects the whole set.
    """
    wrapper = LockTraceWrapper(Lock())

    def function_with_locked_events():
        with wrapper:
            for _ in range(1000):
                wrapper.notify('kek')
        sleep(0.1)

    def function_with_not_locked_event():
        wrapper.notify('kek')

    threads = [Thread(target=function_with_locked_events) for _ in range(100)]
    threads.append(Thread(target=function_with_not_locked_event))

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not wrapper.was_event_locked('kek')


def test_simple_not_locked_event():
    """
    Return False when a matching action exists outside an open acquire.

    The event is present in the trace, so the check should report it as unlocked instead of treating it as missing.
    """
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('kek')

    assert not wrapper.was_event_locked('kek')


def test_simple_one_not_locked_event_and_one_locked():
    """
    Lock-state checks are scoped to the requested event identifier.

    Record one unlocked 'lol' action and a separate locked 'kek' action in the same trace; 'lol' should report False while 'kek' reports True.
    """
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('lol')

    with wrapper:
        wrapper.notify('kek')

    assert not wrapper.was_event_locked('lol')
    assert wrapper.was_event_locked('kek')


def test_when_event_locked_and_unlocked_its_unlocked():
    """
    An event identifier is locked only when every matching occurrence happens while the lock is held.

    A locked occurrence followed by an unlocked occurrence must return False.
    """
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('lol')
    wrapper.notify('lol')

    assert not wrapper.was_event_locked('lol')


def test_when_event_unlocked_and_locked_its_unlocked():
    """
    An event identifier is unsafe if any occurrence happens outside the lock.

    This covers an unlocked occurrence followed by a locked occurrence and expects the result to stay False.
    """
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('lol')
    with wrapper:
        wrapper.notify('lol')

    assert not wrapper.was_event_locked('lol')


def test_unknown_event_type():
    """
    Unknown tracer event types are ignored when checking whether an event was locked.

    If the trace contains only an unrecognized event and no matching ACTION, was_event_locked should follow the normal missing-event behavior.
    """
    wrapper = LockTraceWrapper(Lock())

    wrapper.trace.append(TracerEvent('unknown', 1))

    assert not wrapper.was_event_locked('lol', raise_exception=False)

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "lol" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('lol')

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "lol" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('lol', raise_exception=True)
