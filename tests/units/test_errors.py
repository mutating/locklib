import pytest
from full_match import match

from locklib.errors import DeadLockError


def test_raise():
    with pytest.raises(DeadLockError, match=match('some message')):
        raise DeadLockError('some message')
