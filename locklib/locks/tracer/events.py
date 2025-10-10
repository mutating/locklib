from typing import Optional
from enum import Enum
from dataclasses import dataclass


class TracerEventType(Enum):
    ACQUIRE = 'acquire'
    RELEASE = 'release'
    ACTION = 'action'


@dataclass
class TracerEvent:
    type: TracerEventType
    thread_id: int
    identifier: Optional[str] = None
