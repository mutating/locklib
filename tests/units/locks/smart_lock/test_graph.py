import pytest

from locklib.errors import DeadLockError
from locklib.locks.smart_lock.graph import LocksGraph


def test_multiple_set_and_get():
    """
    LocksGraph preserves multiple outgoing links from one source.

    After several add_link calls from the same source, get_links_from returns the full adjacency set. Missing nodes and nodes that only appear as destinations return an empty set.
    """
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(1, 3)
    graph.add_link(1, 4)

    assert graph.get_links_from(1) == {2, 3, 4}

    assert graph.get_links_from(2) == set()

    assert graph.get_links_from(5) == set()


def test_reverse_deleting_of_nodes():
    """
    search_cycles finds a three-node path through a branching graph.

    With 1 -> 6 and 6 -> {3, 4, 5}, searching from 1 to 5 should return a path of length 3.
    """
    graph = LocksGraph()

    graph.add_link(1, 6)

    graph.add_link(6, 3)
    graph.add_link(6, 4)
    graph.add_link(6, 5)

    assert len(graph.search_cycles(1, 5)) == 3


def test_set_get_delete_and_get():
    """
    Deleting one outgoing edge preserves the remaining edges for the same source.

    Create multiple edges from one source, delete only one existing target, and assert the source adjacency still contains the other target.
    """
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(1, 3)
    graph.add_link(1, 4)

    assert graph.get_links_from(1) == {2, 3, 4}

    graph.delete_link(1, 2)

    assert graph.get_links_from(1) == {3, 4}


def test_delete_from_empty_graph():
    """
    Deleting a link from an empty graph is a no-op.

    delete_link on a fresh graph should not raise, should not materialize a defaultdict key, and should leave links unchanged.
    """
    graph = LocksGraph()

    graph.delete_link(1, 2)

    assert not graph.links


def test_delete_non_existing_link():
    """
    Deleting a missing target edge from an existing source node leaves the graph unchanged.

    An unrelated outgoing edge from the same source remains present after the delete operation.
    """
    graph = LocksGraph()

    graph.add_link(1, 2)

    graph.delete_link(1, 3)

    assert graph.get_links_from(1) == {2}


def test_detect_simple_cycle():
    """
    Reject a direct wait-for cycle without storing the closing edge.

    After 1 -> 2 exists, adding 2 -> 1 would create a two-node cycle. add_link must raise DeadLockError, and 2's outgoing links must not include the rejected edge to 1.
    """
    graph = LocksGraph()

    graph.add_link(1, 2)

    with pytest.raises(DeadLockError):
        graph.add_link(2, 1)

    assert 1 not in graph.get_links_from(2)


def test_detect_difficult_cycle():
    """
    Reject a long transitive cycle without storing the closing edge.

    Build a chain from 1 through 9, then try to close it with 9 -> 1. add_link must raise DeadLockError, and 9's outgoing links must not include the rejected edge to 1.
    """
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

    assert 1 not in graph.get_links_from(9)


def test_simple_exception_message():
    """
    A direct two-node cycle reports only the short DeadLockError message.

    After 1 -> 2 exists, closing it with 2 -> 1 should produce exactly the short message and no full-path tail.
    """
    graph = LocksGraph()

    graph.add_link(1, 2)

    with pytest.raises(DeadLockError) as e:
        graph.add_link(2, 1)

    assert str(e.value) == 'A cycle between 2th and 1th threads has been detected.'


def test_exception_message_not_so_simple():
    """
    A multi-node deadlock reports the full cycle path.

    Build a four-node wait-for cycle closed by the 4 -> 1 dependency. The raised DeadLockError should use the base deadlock message and include the path tail 4, 3, 2, 1.
    """
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(2, 3)
    graph.add_link(3, 4)

    with pytest.raises(DeadLockError) as e:
        graph.add_link(4, 1)

    assert str(e.value) == 'A cycle between 4th and 1th threads has been detected. The full path of the cycle: 4, 3, 2, 1.'


def test_exception_message_not_so_simple_2():
    """
    A three-node cycle includes its full path in the DeadLockError message.

    Closing 1 -> 2 and 2 -> 3 with 3 -> 1 should report the path 3, 2, 1.
    """
    graph = LocksGraph()

    graph.add_link(1, 2)
    graph.add_link(2, 3)

    with pytest.raises(DeadLockError) as e:
        graph.add_link(3, 1)

    assert str(e.value) == 'A cycle between 3th and 1th threads has been detected. The full path of the cycle: 3, 2, 1.'
