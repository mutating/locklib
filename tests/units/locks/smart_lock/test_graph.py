import pytest

from locklib.errors import DeadLockError
from locklib.locks.smart_lock.graph import LocksGraph


def test_multiple_set_and_get():
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(1, 3)
    graph.add_link(1, 4)

    assert graph.get_links_from(1) == {2, 3, 4}

    assert graph.get_links_from(2) == set()

    assert graph.get_links_from(5) == set()


def test_reverse_deleting_of_nodes():
    graph = LocksGraph()

    graph.add_link(1, 6)

    graph.add_link(6, 3)
    graph.add_link(6, 4)
    graph.add_link(6, 5)

    assert len(graph.search_cycles(1, 5)) == 3


def test_set_get_delete_and_get():
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(1, 3)
    graph.add_link(1, 4)

    assert graph.get_links_from(1) == {2, 3, 4}

    graph.delete_link(1, 2)

    assert graph.get_links_from(1) == {3, 4}


def test_delete_from_empty_graph():
    graph = LocksGraph()

    graph.delete_link(1, 2)

    assert not graph.links


def test_delete_non_existing_link():
    graph = LocksGraph()

    graph.add_link(1, 2)

    graph.delete_link(1, 3)

    assert graph.get_links_from(1) == {2}


def test_detect_simple_cycle():
    graph = LocksGraph()

    graph.add_link(1, 2)

    with pytest.raises(DeadLockError):
        graph.add_link(2, 1)


def test_detect_difficult_cycle():
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(2, 3)
    graph.add_link(3, 4)
    graph.add_link(4, 5)
    graph.add_link(5, 6)
    graph.add_link(6, 7)
    graph.add_link(7, 8)
    graph.add_link(8, 9)

    with pytest.raises(DeadLockError):
        graph.add_link(9, 1)


def test_simple_exception_message():
    graph = LocksGraph()

    graph.add_link(1, 2)

    with pytest.raises(DeadLockError) as e:
        graph.add_link(2, 1)

    assert str(e.value) == 'A cycle between 2th and 1th threads has been detected.'


def test_exception_message_not_so_simple():
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(2, 3)
    graph.add_link(3, 4)

    with pytest.raises(DeadLockError) as e:
        graph.add_link(4, 1)

    assert str(e.value) == 'A cycle between 4th and 1th threads has been detected. The full path of the cycle: 4, 3, 2, 1.'


def test_exception_message_not_so_simple_2():
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(2, 3)

    with pytest.raises(DeadLockError) as e:
        graph.add_link(3, 1)

    assert str(e.value) == 'A cycle between 3th and 1th threads has been detected. The full path of the cycle: 3, 2, 1.'
