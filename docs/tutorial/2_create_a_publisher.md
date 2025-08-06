Let's write our Publisher class next. To simulate some sort of real work we can sleep
and publish a number in a loop, mimicking a sensor reader for example.

```python title="publisher.py"
import asyncio
import logging
import random

from valkey.asyncio import Valkey


class Publisher:
    def __init__(self, valkey: Valkey) -> None:
        self._valkey = valkey

    async def run(self) -> None:
        while True:
            number = random.randint(-100, 100)
            logging.info(f"Publishing: {number}")
            await self._valkey.xadd("numbers", {"number": str(number)})
            await asyncio.sleep(1)

```

!!! note
    The Publisher asking for the Valkey instance when being initialised is a form of
    [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection) (specifically
    Constructor injection). Doing this separates out the concerns of configuring the client and
    using it.


Let's register the Publisher with our engin. We can do this by making a simple factory function
below the `Publisher`.

```python
def publisher_factory(valkey: Valkey) -> Publisher:
    return Publisher(valkey=valkey)
```

This isn't enough though as we need to tell the engin how to run the publisher as well. We want
our engin to call `Publisher.run` when the application is run, we can do that by using the
`Supervisor` type which is always provided by Engin.

```python
def publisher_factory(valkey: Valkey, supervisor: Supervisor) -> Publisher:
    publisher = Publisher(valkey=valkey)

    # run the publisher as a supervised application task
    supervisor.supervise(publisher.run)

    return publisher
```

!!! tip
    
    Supervised tasks can handle exceptions in different ways, controlled by the `OnException`
    enum. By default if the supervised task errors then it will cause the engin to shutdown,
    but you can also choose for the error to be ignored or the task to be restarted.

Now we just need to register our `publisher_factory` with the engin. We can do this using the
`Provide` marker class which allows us to "provide a dependency" to the engin.

```python title="app.py"
# ... existing code ...
from engin import Provide
from examples.tutorial.publisher import publisher_factory


engin = Engin(Provide(publisher_factory))
```

Our publisher requires a Valkey client, so let's create a factory for that too.

```python title="valkey_client.py"
from valkey.asyncio import Valkey

def valkey_client_factory() -> Valkey:
    return Valkey.from_url("valkey://localhost:6379")
```

And let's provide this factory to the engin.

```python title="app.py"
# ... existing code ...
from engin import Provide
from examples.tutorial.publisher import publisher_factory
from examples.tutorial.valkey_client import valkey_client_factory


engin = Engin(Provide(publisher_factory), Provide(valkey_client_factory))
```