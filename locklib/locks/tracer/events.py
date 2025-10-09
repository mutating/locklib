from enum import StrEnum


class TracerEvent(StrEnum):
    ACQUIRE = 'acquire'
    RELEASE = 'release'
