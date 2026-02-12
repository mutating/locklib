from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TracerEventType(Enum):
    ACQUIRE = 'acquire'
    RELEASE = 'release'
    ACTION = 'action'


@dataclass
class TracerEvent:
    type: TracerEventType
    thread_id: int
    identifier: Optional[str] = None
