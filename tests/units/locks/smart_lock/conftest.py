from typing import Type

import pytest

from locklib import SmartLock, SmartRLock
from locklib.locks.smart_lock.abstract import AbstractSmartLock


@pytest.fixture(params=[SmartLock, SmartRLock])
def smartlock_class(request: pytest.FixtureRequest) -> Type[AbstractSmartLock]:
    return request.param
