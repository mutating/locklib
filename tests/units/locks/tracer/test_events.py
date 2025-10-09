from locklib import TracerEvent


def test_it_has_2_kinds_of_events():
    assert TracerEvent.ACQUIRE
    assert TracerEvent.RELEASE
    assert TracerEvent.ACQUIRE != TracerEvent.RELEASE
