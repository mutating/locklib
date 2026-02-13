from threading import Lock, Thread, get_ident
from time import sleep
from typing import List, Union

import pytest
from full_match import match

from locklib import LockTraceWrapper, StrangeEventOrderError, ThereWasNoSuchEventError
from locklib.locks.tracer.events import TracerEvent, TracerEventType


def test_base_trace_with_methods():
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
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('kek')

    assert len(wrapper.trace) == 1
    assert wrapper.trace[0] == TracerEvent(TracerEventType.ACTION, get_ident(), 'kek')


def test_try_to_release_event_without_corresponding_acquire_event():
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
    wrapper = LockTraceWrapper(Lock())

    assert not wrapper.was_event_locked('kek', raise_exception=False)

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek')

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek', raise_exception=True)


def test_event_is_locked_if_there_are_only_opening_and_slosing_events():
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        pass

    assert not wrapper.was_event_locked('kek', raise_exception=False)

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek')

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "kek" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('kek', raise_exception=True)


def test_simple_case_of_locked_event():
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('kek')

    assert wrapper.was_event_locked('kek')


def test_simple_case_of_locked_multiple_events():
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')

    assert wrapper.was_event_locked('kek')


def test_locked_events_with_only_acquire():
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')
        wrapper.notify('kek')

        assert wrapper.was_event_locked('kek')


def test_multiple_locked_events_in_100_threads():
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
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('kek')

    assert not wrapper.was_event_locked('kek')


def test_simple_one_not_locked_event_and_one_locked():
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('lol')

    with wrapper:
        wrapper.notify('kek')

    assert not wrapper.was_event_locked('lol')
    assert wrapper.was_event_locked('kek')


def test_when_event_locked_and_unlocked_its_unlocked():
    wrapper = LockTraceWrapper(Lock())

    with wrapper:
        wrapper.notify('lol')
    wrapper.notify('lol')

    assert not wrapper.was_event_locked('lol')


def test_when_event_unlocked_and_locked_its_unlocked():
    wrapper = LockTraceWrapper(Lock())

    wrapper.notify('lol')
    with wrapper:
        wrapper.notify('lol')

    assert not wrapper.was_event_locked('lol')


def test_unknown_event_type():
    wrapper = LockTraceWrapper(Lock())

    wrapper.trace.append(TracerEvent('unknown', 1))

    assert not wrapper.was_event_locked('lol', raise_exception=False)

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "lol" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('lol')

    with pytest.raises(ThereWasNoSuchEventError, match=match('No events with identifier "lol" occurred in any of the threads, so the question "was it thread-safe" is meaningless.')):
        wrapper.was_event_locked('lol', raise_exception=True)
