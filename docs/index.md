# Engin 🏎️

Engin is a lightweight application framework powered by dependency injection, it helps
you build both large monoliths and multiple microservices.


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

## Getting Started

A minimal example:

```python
import asyncio

from httpx import AsyncClient

from engin import Engin, Invoke, Provide


def httpx_client() -> AsyncClient:
    return AsyncClient()


async def main(http_client: AsyncClient) -> None:
    print(await http_client.get("https://httpbin.org/get"))

engin = Engin(Provide(httpx_client), Invoke(main))

asyncio.run(engin.run())
```

