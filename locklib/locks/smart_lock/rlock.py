from locklib.locks.smart_lock.abstract import AbstractSmartLock


class SmartRLock(AbstractSmartLock):
    recursive = True
