from enum import Enum


class TracerEvent(Enum):
    ACQUIRE = 'acquire'
    RELEASE = 'release'
