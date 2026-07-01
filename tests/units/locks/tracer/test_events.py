from locklib.locks.tracer.events import TracerEvent, TracerEventType


def test_it_has_2_kinds_of_event_types():
    """
    TracerEventType exposes all required event categories.

    ACQUIRE, RELEASE, and ACTION should be truthy and pairwise distinct so traced lock events can be classified unambiguously.
    """
    assert TracerEventType.ACQUIRE
    assert TracerEventType.RELEASE
    assert TracerEventType.ACTION

    assert TracerEventType.ACQUIRE != TracerEventType.RELEASE
    assert TracerEventType.ACQUIRE != TracerEventType.ACTION
    assert TracerEventType.RELEASE != TracerEventType.ACTION


def test_equality_of_events():
    """
    Events compare equal only when their type, thread id, and identifier all match.

    Changing any of those fields makes otherwise similar events unequal.
    """
    assert TracerEvent(TracerEventType.ACQUIRE, 1) == TracerEvent(TracerEventType.ACQUIRE, 1)
    assert TracerEvent(TracerEventType.RELEASE, 1) == TracerEvent(TracerEventType.RELEASE, 1)
    assert TracerEvent(TracerEventType.ACTION, 1) == TracerEvent(TracerEventType.ACTION, 1)
    assert TracerEvent(TracerEventType.ACTION, 1, 'kek') == TracerEvent(TracerEventType.ACTION, 1, 'kek')

    assert TracerEvent(TracerEventType.ACQUIRE, 1) != TracerEvent(TracerEventType.ACQUIRE, 2)
    assert TracerEvent(TracerEventType.ACQUIRE, 1) != TracerEvent(TracerEventType.RELEASE, 1)
    assert TracerEvent(TracerEventType.ACTION, 1, 'lol') != TracerEvent(TracerEventType.ACTION, 1, 'kek')
    assert TracerEvent(TracerEventType.ACQUIRE, 1) != TracerEvent(TracerEventType.ACTION, 1, 'kek')
    assert TracerEvent(TracerEventType.RELEASE, 1) != TracerEvent(TracerEventType.ACTION, 1, 'kek')
