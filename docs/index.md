# Engin 🏎️

Engin is a lightweight application framework powered by dependency injection. It helps
you build and maintain everything from large monoliths to hundreds of microservices.


## Features

Engin provides:

- A fully-featured dependency injection system.
- A robust runtime with lifecycle hooks and supervised background tasks.
- Zero-boilerplate code reuse across applications.
- Integrations for popular frameworks like FastAPI.
- Full asyncio support.
- A CLI for development utilities.


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

Here’s a minimal example showing how Engin wires dependencies, manages background tasks, and
handles graceful shutdown.

```python
import asyncio
from httpx import AsyncClient
from engin import Engin, Invoke, Lifecycle, OnException, Provide, Supervisor


def httpx_client_factory(lifecycle: Lifecycle) -> AsyncClient:
    client = AsyncClient()
    lifecycle.append(client)  # easily manage the AsyncClient's lifecycle concerns
    return client


async def main(httpx_client: AsyncClient, supervisor: Supervisor) -> None:
    async def long_running_task():
        while True:
            await httpx_client.get("https://example.org/")
            await asyncio.sleep(1.0)

    supervisor.supervise(long_running_task)  # let the app run the task in a supervised manner


engin = Engin(Provide(httpx_client_factory), Invoke(main))  # define our modular application

asyncio.run(engin.run())  # run it!
```

Expected output (with logging enabled):

```
[INFO]  engin: starting engin
[INFO]  engin: startup complete
[INFO]  engin: supervising task: long_running_task
[INFO]  httpx: HTTP Request: GET https://example.org/ "HTTP/1.1 200 OK"
[INFO]  httpx: HTTP Request: GET https://example.org/ "HTTP/1.1 200 OK"
[INFO]  httpx: HTTP Request: GET https://example.org/ "HTTP/1.1 200 OK"
[DEBUG] engin: received signal: SIGINT
[DEBUG] engin: supervised task 'long_running_task' was cancelled
[INFO]  engin: stopping engin
[INFO]  engin: shutdown complete
```
