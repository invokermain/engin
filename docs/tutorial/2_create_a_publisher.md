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
    [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection), specifically
    Constructor injection. Doing this separates out the concerns of configuring the client and
    using it.


Let's register the `Publisher` with our application so we can use it later. We do this by:

1. Creating a factory function which is responsible for creating the `Publisher` instance.
2. Registering this factory function with our `Engin` instance as a "provider".

We can write a simple factory function below the `Publisher` class. Notice that the factory
function also asks for the `Valkey` client to be injected. We will provide the `Valkey`
dependency later and Engin will automatically take care of giving it to the
`publisher_factory`.

```python
def publisher_factory(valkey: Valkey) -> Publisher:
    return Publisher(valkey=valkey)
```

We need to tell the application how to run the `Publisher` as well. We want Engin to call
`Publisher.run` when the application is run which we can do by using the `Supervisor`
dependency. The `Supervisor` is a dependency that is provided by Engin and it can be used to
supervise long running tasks.

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
`Provide` marker class which allows us to "provide" a dependency to our application.

```python title="app.py"
# ... existing code ...
from engin import Provide
from examples.tutorial.publisher import publisher_factory


engin = Engin(Provide(publisher_factory))
```

Our `Publisher` requires a `Valkey` client, so let's create a factory for that too, we can
hardcode the url to make this simple for now.


```python title="valkey_client.py"
from valkey.asyncio import Valkey

def valkey_client_factory() -> Valkey:
    return Valkey.from_url("valkey://localhost:6379")
```

And let's provide this dependency to the application as well.

```python title="app.py"
# ... existing code ...
from engin import Provide
from examples.tutorial.publisher import publisher_factory
from examples.tutorial.valkey_client import valkey_client_factory


engin = Engin(Provide(publisher_factory), Provide(valkey_client_factory))
```
