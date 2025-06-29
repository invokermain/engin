# Lifecycle

Certain types of object naturally have some form of startup and shutdown behaviour
associated with them, these steps need to be tied the lifecycle of the application itself
in order to be useful. For example, a database connection manager might want to fill its
connection pool on startup, and gracefully release the connections on shutdown.

Doing this yourself can be tricky and is application dependent: most will not have any
special support for this and will expect you to manage your lifecycle concerns in your
entrypoint function, leading to unwieldy code in larger applications, whilst other
types application might expected you to translate the lifecyle tasks into something they
offer, e.g. an ASGI server would expect you to manage this via its lifespan. In both cases
you end up managing lifecycle in a completely different place to where you declare your
objects, which make the codebase more complicated to understand.

Luckily, engin makes declaring lifecycle tasks a breeze, and it can be done in the same
provider that build your object keeping your code nicely collocated.

## The Lifecycle type

Engin automatically provides a special type called `Lifecycle` that can be used like any
other provided type. This type allows you to register lifecycle tasks with the Engin which
will automatically be run as part of your application lifecycle.

## Registering lifecycle tasks

There are a few different ways to declare and register your lifecycle tasks, they all do
the same thing, so which one to use depends on whichever is easiest for your specific
lifecycle tasks.

### 1. Existing context manager

If your type exposes a context manager interface to handle its lifecycle, registering it
is as easy as calling `lifecycle.append(...)`, this works for sync and async context
managers.

Let's look at an example using `httpx.AsyncClient`:

```python
from engin import Lifecycle
from httpx import AsyncClient


def httpx_client(lifecycle: Lifecycle) -> AsyncClient:
    client = AsyncClient()
    lifecycle.append(client)  # register the lifecycle tasks
    return client
```

### 2. Explict startup & shutdown methods

If your type exposes meathods that must be called as part of the lifecycle, e.g. `start()`
& `stop()`, then `lifecycle.hook(on_start=..., on_stop=...)` is the way.

Let's look at an example using `piccolo.engine.PostgresEngin`:

```python
from engin import Lifecycle
from piccolo.engine import PostgresEngine

def postgres_engine(lifecyle: Lifecycle) -> PostgresEngine:
    db_engine = PostgresEngine(...)  # fill in actual connection details

    lifecyle.hook(
        on_start=db_engine.start_connection_pool(),
        on_stop=db_engine.close_connection_pool(),
    )

    return db_engine
```

### 3. Custom context managers

For more advanced use cases you can always define your own context manager.

In this example assume that `worker.run()` will not return to us when we await it, and
therefore we want to manage it as a task.


```python
import asyncio
from engin import Lifecycle
from some_package import BlockingAsyncWorker

def blocking_worker(lifecycle: Lifecycle) -> BlockingWorker:
    worker = BlockingAsyncWorker()

    @asynccontextmanager
    async def worker_lifecycle() -> AsyncIterator[None]:
        task = asyncio.create_task(worker.run())
        yield None
        worker.stop()
        del task

    lifecycle.append(worker_lifecycle())

    return worker
```
