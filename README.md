<details>
  <summary>ⓘ</summary>

[![Downloads](https://static.pepy.tech/badge/locklib/month)](https://pepy.tech/project/locklib)
[![Downloads](https://static.pepy.tech/badge/locklib)](https://pepy.tech/project/locklib)
[![Coverage Status](https://coveralls.io/repos/github/mutating/locklib/badge.svg?branch=main)](https://coveralls.io/github/mutating/locklib?branch=main)
[![Lines of code](https://sloc.xyz/github/mutating/locklib/?category=code?)](https://github.com/boyter/scc/)
[![Hits-of-Code](https://hitsofcode.com/github/mutating/locklib?branch=main)](https://hitsofcode.com/github/mutating/locklib/view?branch=main)
[![Test-Package](https://github.com/mutating/locklib/actions/workflows/tests_and_coverage.yml/badge.svg)](https://github.com/mutating/locklib/actions/workflows/tests_and_coverage.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/locklib.svg)](https://pypi.python.org/pypi/locklib)
[![PyPI version](https://badge.fury.io/py/locklib.svg)](https://badge.fury.io/py/locklib)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/mutating/locklib)

</details>

<p align="center">

![logo](https://raw.githubusercontent.com/mutating/locklib/develop/docs/assets/logo_7.svg)

</p>

It adds several useful features to Python’s standard synchronization primitives, including lock protocols and enhanced lock implementations.


## Table of contents

- [**Installation**](#installation)
- [**Lock protocols**](#lock-protocols)
- [**`SmartLock` turns deadlocks into exceptions**](#smartlock-turns-deadlocks-into-exceptions)
- [**Test your locks**](#test-your-locks)


## Installation

Install [`locklib`](https://pypi.org/project/locklib/) with `pip`:

```bash
pip install locklib
```

... or directly from the Git repository:

```bash
pip install git+https://github.com/mutating/locklib.git
```

You can also use [`instld`](https://github.com/pomponchik/instld) to quickly try out this package and others without installing them.


## Lock protocols

Protocols let you write type-annotated code without depending on concrete classes. The protocols in this library let you treat lock implementations from the standard library, third-party packages, and this library uniformly.

At a minimum, a lock object should provide two methods:

```python
def acquire(self) -> None: ...
def release(self) -> None: ...
```

All standard library locks conform to this, as do the locks provided by this library.

To check for compliance with this minimum standard, `locklib` contains the `LockProtocol`. You can verify that all of these locks satisfy it:

```python
from multiprocessing import Lock as MLock
from threading import Lock as TLock, RLock as TRLock
from asyncio import Lock as ALock

from locklib import SmartLock, LockProtocol

print(isinstance(MLock(), LockProtocol)) # True
print(isinstance(TLock(), LockProtocol)) # True
print(isinstance(TRLock(), LockProtocol)) # True
print(isinstance(ALock(), LockProtocol)) # True
print(isinstance(SmartLock(), LockProtocol)) # True
```

However, most idiomatic Python code uses locks as context managers. If your code does too, you can use one of the two protocols derived from the base `LockProtocol`: `ContextLockProtocol` or `AsyncContextLockProtocol`. Thus, the protocol hierarchy looks like this:

```
LockProtocol
 ├── ContextLockProtocol
 └── AsyncContextLockProtocol
```

`ContextLockProtocol` describes objects that satisfy `LockProtocol` and also implement the [context manager protocol](https://docs.python.org/3/library/stdtypes.html#typecontextmanager). Similarly,`AsyncContextLockProtocol` describes objects that satisfy `LockProtocol` and implement the [asynchronous context manager](https://docs.python.org/3/reference/datamodel.html#async-context-managers) protocol.

Almost all standard library locks, as well as `SmartLock`, satisfy `ContextLockProtocol`:

```python
from multiprocessing import Lock as MLock
from threading import Lock as TLock, RLock as TRLock

from locklib import SmartLock, ContextLockProtocol

print(isinstance(MLock(), ContextLockProtocol)) # True
print(isinstance(TLock(), ContextLockProtocol)) # True
print(isinstance(TRLock(), ContextLockProtocol)) # True
print(isinstance(SmartLock(), ContextLockProtocol)) # True
```

However, the [`asyncio.Lock`](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock) belongs to a separate category and `AsyncContextLockProtocol` is needed to describe it:

```python
from asyncio import Lock
from locklib import AsyncContextLockProtocol

print(isinstance(Lock(), AsyncContextLockProtocol)) # True
```

If you use type hints and static verification tools like [mypy](https://github.com/python/mypy), we highly recommend using the narrowest applicable protocol for your use case.


## `SmartLock` turns deadlocks into exceptions

`locklib` includes a lock that prevents [deadlocks](https://en.wikipedia.org/wiki/Deadlock) — `SmartLock`, based on [Wait-for Graph](https://en.wikipedia.org/wiki/Wait-for_graph). You can use it like a regular [`Lock` from the standard library](https://docs.python.org/3/library/threading.html#lock-objects). Let’s verify that it prevents [race conditions](https://en.wikipedia.org/wiki/Race_condition) in the same way:

```python
from threading import Thread
from locklib import SmartLock

lock = SmartLock()
counter = 0

def function():
    global counter

    for _ in range(1000):
        with lock:
            counter += 1

thread_1 = Thread(target=function)
thread_2 = Thread(target=function)
thread_1.start()
thread_2.start()

assert counter == 2000
```

As expected, this lock prevents race conditions just like the standard `Lock`. Now let’s deliberately trigger a deadlock and see what happens:

```python
from threading import Thread
from locklib import SmartLock

lock_1 = SmartLock()
lock_2 = SmartLock()

def function_1():
    while True:
        with lock_1:
            with lock_2:
                pass

def function_2():
    while True:
        with lock_2:
            with lock_1:
                pass

thread_1 = Thread(target=function_1)
thread_2 = Thread(target=function_2)
thread_1.start()
thread_2.start()
```

This raises an exception like the following:

```
...
locklib.errors.DeadLockError: A cycle between 1970256th and 1970257th threads has been detected.
```

So, with this lock, a deadlock results in an exception instead of blocking forever.

If you want to catch this exception, you can also import it from `locklib`:

```python
from locklib import DeadLockError
```


## Test your locks

Sometimes, when testing code, you may need to detect whether some action occurs while the lock is held. How can you do this with minimal boilerplate? Use `LockTraceWrapper`. It is a wrapper around a regular lock that records every acquisition and release. At the same time, it fully preserves the wrapped lock’s behavior.

Creating such a wrapper is easy. Just pass any lock to the constructor:

```python
from threading import Lock
from locklib import LockTraceWrapper

lock = LockTraceWrapper(Lock())
```

You can use it exactly like the wrapped lock:

```python
with lock:
    ...
```

Anywhere in your program, you can record that a specific event occurred:

```python
lock.notify('event_name')
```

You can then easily check whether an event with this identifier ever occurred outside the lock. To do this, use the `was_event_locked` method:

```python
lock.was_event_locked('event_name')
```

If the `notify` method was called with the same parameter only while the lock was held, it will return `True`. If not, that is, if there was at least one case when the `notify` method was called with that identifier without the lock being held, `False` will be returned.

How does it work? It uses a modified [balanced-parentheses algorithm](https://ru.wikipedia.org/wiki/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D1%8C%D0%BD%D0%B0%D1%8F_%D1%81%D0%BA%D0%BE%D0%B1%D0%BE%D1%87%D0%BD%D0%B0%D1%8F_%D0%BF%D0%BE%D1%81%D0%BB%D0%B5%D0%B4%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D0%BE%D1%81%D1%82%D1%8C). For each thread for which any events were registered (taking the mutex, releasing the mutex, and also calling the `notify` method), the check takes place separately, that is, we determine that it was the same thread that held the mutex when `notify` was called, and not some other one.

> ⚠️ The thread id is used to identify the threads. A thread ID may be reused after a thread exits, which may in some cases cause the wrapper to incorrectly report that an operation was protected by the lock. Make sure this cannot happen during your tests.

If no event with the specified identifier was recorded in any thread, the `ThereWasNoSuchEventError` exception will be raised by default. If you want to disable this so that the method simply returns `False` in such situations, pass the keyword argument `raise_exception=False` to `was_event_locked`.
