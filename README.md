# Engin 🏎️

Engin is a zero-dependency application framework for modern Python.

## Features ✨

- **Lightweight**: Engin has no dependencies.
- **Async First**: Engin provides first-class support for applications. 
- **Dependency Injection**: Engin promotes a modular decoupled architecture in your application.
- **Lifecycle Management**: Engin provides an simple, portable approach for implememting
  startup and shutdown tasks.
- **Ecosystem Compatability**: seamlessly integrate with frameworks such as FastAPI without
  having to migrate your dependencies.
- **Code Reuse**: Engin's modular components work great as packages and distributions. Allowing
  low boiler-plate code reuse within your Organisation.

## Installation

Engin is available on PyPI, install using your favourite dependency manager:

- **pip**:`pip install engin`
- **poetry**: `poetry add engin`
- **uv**: `uv add engin`

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

