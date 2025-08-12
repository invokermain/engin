# The Engin

An Engin instance is a self-contained application.

The Engin class manages your application's complete lifecycle, when ran it will:

1. Assemble the dependencies required by your invocations.
2. Runs all given invocations sequentially in the order they were passed in to the Engin. 
3. Run all lifecycle startup tasks that were registered by assembled dependencies sequentially.
4. Start any supervised background tasks.
5. Wait for a shutdown signal, SIGINT or SIGTERM, or for a supervised task to cause a shutdown.
6. Stop any supervised background tasks that are still running.
7. Run all corresponding lifecycle shutdown tasks in the reverse order to the startup order.


## Creating an Engin

Instantiate an Engin with any combination of options, i.e. providers, invocations, and blocks:

```python
from engin import Engin, Entrypoint, Provide, Supervisor

def my_service_factory(supervisor: Supervisor) -> MyService:
    my_service = MyService()
    supervisor.supervise(my_service.run)
    return my_service

engin = Engin(Provide(my_service_factory), Entrypoint(MyService))
```

## Running your application

### `engin.run()`

The recommended way to run your application.

This will not return until the application is stopped and shutdown has been performed. As it
listens for signals and handles cancellation this should be the top-most function called in
your application:

```python
import asyncio

asyncio.run(engin.run())
```


### `engin.start()` and `engin.stop()`

For advanced scenarios where you need more control over the application lifecycle:

```python
# Start the application in the background
await engin.start()

# Do other work...

# Gracefully stop the application  
await engin.stop()
```

This approach can be useful when writing tests for an Engin application.
