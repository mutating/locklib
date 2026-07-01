import pytest
from full_match import match

from locklib.errors import DeadLockError


def test_raise():
    """DeadLockError can be raised directly with a caller-supplied message."""
    with pytest.raises(DeadLockError, match=match('some message')):
        raise DeadLockError('some message')
