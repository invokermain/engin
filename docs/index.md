# Engin 🏎️

Engin is a lightweight application framework powered by dependency injection, it helps
you build and maintain large monoliths and many microservices.


## Features

The Engin framework includes:

- A fully-featured dependency injection system.
- A robust application runtime with lifecycle hooks and supervised background tasks.
- Zero boiler-plate code reuse across multiple applications.
- Integrations for other frameworks such as FastAPI.
- Full async support.
- CLI commands to aid local development.


## Installation

=== "uv"

    ```shell
    uv add engin
    ```

=== "poetry"

    ```shell
    poetry add engin
    ```

=== "pip"

    ```shell
    pip install engin
    ```

## Example

A small example which shows some of the runtime features of Engin. This application
makes a http request and then performs a shutdown.

```python
import asyncio
from httpx import AsyncClient
from engin import Engin, Invoke, Lifecycle, Provide, ShutdownSwitch, Supervisor


def httpx_client_factory(lifecycle: Lifecycle) -> AsyncClient:
    # create our http client
    client = AsyncClient()
    # this will open and close the AsyncClient as part of the application's lifecycle
    lifecycle.append(client)
    return client


async def main(
    httpx_client: AsyncClient,
    shutdown: ShutdownSwitch,
    supervisor: Supervisor,
) -> None:
    async def http_request():
        await httpx_client.get("https://httpbin.org/get")
        # one we've made the http request shutdown the application
        shutdown.set()

    # supervise the http request as part of the application's lifecycle
    supervisor.supervise(http_request)

# define our modular application
engin = Engin(Provide(httpx_client_factory), Invoke(main))

# run it!
asyncio.run(engin.run())
```

With logs enabled this will output:

```shell
INFO:engin:starting engin
INFO:engin:startup complete
INFO:httpx:HTTP Request: GET https://httpbin.org/get "HTTP/1.1 200 OK"
INFO:engin:stopping engin
INFO:engin:shutdown complete
```
