<details>
  <summary>ⓘ</summary>

[![Downloads](https://static.pepy.tech/badge/locklib/month)](https://pepy.tech/project/locklib)
[![Downloads](https://static.pepy.tech/badge/locklib)](https://pepy.tech/project/locklib)
[![Coverage Status](https://coveralls.io/repos/github/pomponchik/locklib/badge.svg?branch=main)](https://coveralls.io/github/pomponchik/locklib?branch=main)
[![Lines of code](https://sloc.xyz/github/pomponchik/locklib/?category=code?)](https://github.com/boyter/scc/)
[![Hits-of-Code](https://hitsofcode.com/github/pomponchik/locklib?branch=main)](https://hitsofcode.com/github/pomponchik/locklib/view?branch=main)
[![Test-Package](https://github.com/pomponchik/locklib/actions/workflows/tests_and_coverage.yml/badge.svg)](https://github.com/pomponchik/locklib/actions/workflows/tests_and_coverage.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/locklib.svg)](https://pypi.python.org/pypi/locklib)
[![PyPI version](https://badge.fury.io/py/locklib.svg)](https://badge.fury.io/py/locklib)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/pomponchik/locklib)

</details>

![logo](https://raw.githubusercontent.com/pomponchik/locklib/develop/docs/assets/logo_7.svg)

It contains several useful additions to the standard thread synchronization tools, such as lock protocols and locks with advanced functionality.


## Table of contents

- [**Installation**](#installation)
- [**Lock protocols**](#lock-protocols)
- [**SmartLock - deadlock is impossible with it**](#smartlock---deadlock-is-impossible-with-it)
- [**Test your locks**](#test-your-locks)


## Installation

Get the `locklib` from the [pypi](https://pypi.org/project/locklib/):

```bash
pip install locklib
```

... or directly from git:

```bash
pip install git+https://github.com/pomponchik/locklib.git
```

You can also quickly try out this and other packages without having to install using [instld](https://github.com/pomponchik/instld).


## Lock protocols

Protocols are needed so that you can write typed code without being bound to specific classes. Protocols from this library allow you to "equalize" locks from the standard library and third-party locks, including those provided by this library.

We consider the basic characteristic of the lock protocol to be the presence of two methods for an object:

```python
def acquire() -> None: pass
def release() -> None: pass
```

All the locks from the standard library correspond to this, as well as the locks presented in this one.

To check for compliance with this minimum standard, `locklib` contains the `LockProtocol`. You can check for yourself that all the locks match it:

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

However! Most idiomatic python code using locks uses them as context managers. If your code is like that too, you can use one of the two inheritors of the regular `LockProtocol`: `ContextLockProtocol` or `AsyncContextLockProtocol`. Thus, the protocol inheritance hierarchy looks like this:

```
LockProtocol
 ├── ContextLockProtocol
 └── AsyncContextLockProtocol
```

`ContextLockProtocol` describes the objects described by `LockProtocol`, which are also [context managers](https://docs.python.org/3/library/stdtypes.html#typecontextmanager). `AsyncContextLockProtocol`, by analogy, describes objects that are instances of `LockProtocol`, as well as [asynchronous context managers](https://docs.python.org/3/reference/datamodel.html#async-context-managers).

Almost all the locks from the standard library are instances of `ContextLockProtocol`, as well as `SmartLock`.

```python
from multiprocessing import Lock as MLock
from threading import Lock as TLock, RLock as TRLock

from locklib import SmartLock, ContextLockProtocol

print(isinstance(MLock(), ContextLockProtocol)) # True
print(isinstance(TLock(), ContextLockProtocol)) # True
print(isinstance(TRLock(), ContextLockProtocol)) # True
print(isinstance(SmartLock(), ContextLockProtocol)) # True
```

However, the [`Lock` from asyncio](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock) belongs to a separate category and `AsyncContextLockProtocol` is needed to describe it:

```python
from asyncio import Lock
from locklib import AsyncContextLockProtocol

print(isinstance(Lock(), AsyncContextLockProtocol)) # True
```

If you use type hints and static verification tools like [mypy](https://github.com/python/mypy), we highly recommend using the narrowest of the presented categories for lock protocols, which describe the requirements for your locales.


## `SmartLock` - deadlock is impossible with it

`locklib` contains a lock that cannot get into the [deadlock](https://en.wikipedia.org/wiki/Deadlock) - `SmartLock`, based on [Wait-for Graph](https://en.wikipedia.org/wiki/Wait-for_graph). You can use it as a usual [```Lock``` from the standard library](https://docs.python.org/3/library/threading.html#lock-objects). Let's check that it can protect us from the [race condition](https://en.wikipedia.org/wiki/Race_condition) in the same way:

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

Yeah, in this case the lock helps us not to get a race condition, as the standard ```Lock``` does. But! Let's trigger a deadlock and look what happens:

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

And... We have an exception like this:

```
...
locklib.errors.DeadLockError: A cycle between 1970256th and 1970257th threads has been detected.
```

Deadlocks are impossible for this lock!

If you want to catch the exception, import this from the `locklib` too:

```python
from locklib import DeadLockError
```


## Test your locks

Sometimes, when testing a code, you may need to detect if some action is taking place inside the lock. How to do this with a minimum of code? There is the `LockTraceWrapper` for this. It is a wrapper around a regular lock, which records it every time the code takes a lock or releases it. At the same time, the functionality of the wrapped lock is fully preserved.

It's easy to create an object of such a lock. Just pass any other lock to the class constructor:

```python
from threading import Lock
from locklib import LockTraceWrapper

lock = LockTraceWrapper(Lock())
```

You can use it in the same way as the wrapped lock:

```python
with lock:
    ...
```

Anywhere in your program, you can "inform" the lock that the action you need is being performed here:

```python
lock.notify('event_name')
```

And! Now you can easily identify if there were cases when an event with this identifier did not occur under the mutex. To do this, use the `was_event_locked` method:

```python
lock.was_event_locked('event_name')
```

If the `notify` method was called with the same parameter only when the lock activated, it will return `True`. If not, that is, if there was at least one case when the c method was called with such an identifier without an activated mutex, `False` will be returned.

How does it work? A modified [algorithm for determining the correct parenthesis sequence](https://ru.wikipedia.org/wiki/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D1%8C%D0%BD%D0%B0%D1%8F_%D1%81%D0%BA%D0%BE%D0%B1%D0%BE%D1%87%D0%BD%D0%B0%D1%8F_%D0%BF%D0%BE%D1%81%D0%BB%D0%B5%D0%B4%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D0%BE%D1%81%D1%82%D1%8C) is used here. For each thread for which any events were registered (taking the mutex, releasing the mutex, and also calling the `notify` method), the check takes place separately, that is, we determine that it was the same thread that held the mutex when `notify` was called, and not some other one.

> ⚠️ The thread id is used to identify the streams. This id may be reused if the current thread ends, which in some cases may lead to incorrect identification of lock coverage for operations that were not actually covered by the lock. Make sure that this cannot happen during your test.
