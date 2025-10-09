from locklib.locks.tracer.events import TracerEvent, TracerEventType


def test_it_has_2_kinds_of_event_types():
    assert TracerEventType.ACQUIRE
    assert TracerEventType.RELEASE
    assert TracerEventType.ACTION

    assert TracerEventType.ACQUIRE != TracerEventType.RELEASE
    assert TracerEventType.ACQUIRE != TracerEventType.ACTION
    assert TracerEventType.RELEASE != TracerEventType.ACTION


def test_equality_of_events():
    assert TracerEvent(TracerEventType.ACQUIRE, 1) == TracerEvent(TracerEventType.ACQUIRE, 1)
    assert TracerEvent(TracerEventType.RELEASE, 1) == TracerEvent(TracerEventType.RELEASE, 1)
    assert TracerEvent(TracerEventType.ACTION, 1) == TracerEvent(TracerEventType.ACTION, 1)
    assert TracerEvent(TracerEventType.ACTION, 1, 'kek') == TracerEvent(TracerEventType.ACTION, 1, 'kek')

    assert TracerEvent(TracerEventType.ACQUIRE, 1) != TracerEvent(TracerEventType.ACQUIRE, 2)
    assert TracerEvent(TracerEventType.ACQUIRE, 1) != TracerEvent(TracerEventType.RELEASE, 1)
    assert TracerEvent(TracerEventType.ACTION, 1, 'lol') != TracerEvent(TracerEventType.ACTION, 1, 'kek')
    assert TracerEvent(TracerEventType.ACQUIRE, 1) != TracerEvent(TracerEventType.ACTION, 1, 'kek')
    assert TracerEvent(TracerEventType.RELEASE, 1) != TracerEvent(TracerEventType.ACTION, 1, 'kek')
