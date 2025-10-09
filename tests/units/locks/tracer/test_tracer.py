from typing import List, Union
from locklib import LockTraceWrapper, TracerEvent


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

    assert wrapper.trace == ['acquire', TracerEvent.ACQUIRE, 'release', TracerEvent.RELEASE]


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

    assert wrapper.trace == ['acquire', TracerEvent.ACQUIRE, 'release', TracerEvent.RELEASE]
