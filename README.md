# Engin 🏎️

Engin is a zero-dependency application framework for modern Python.

**Documentation**: https://engin.readthedocs.io/

## Features ✨

- **Dependency Injection** - Engin includes a fully-featured Dependency Injection system,
  powered by type hints.
- **Lifecycle Management** - Engin provides a simple & portable approach for attaching
  startup and shutdown tasks to the application's lifecycle.
- **Code Reuse** - Engin's modular components, called Blocks, work great as distributed
  packages allowing zero boiler-plate code reuse across multiple applications. Perfect for
  maintaining many services across your organisation.
- **Ecosystem Compatability** - Engin ships with integrations for popular frameworks that
  provide their own Dependency Injection, for example FastAPI, allowing you to integrate
  Engin into existing code bases incrementally.
- **Async Native**: Engin is an async framework, meaning first class support for async
  dependencies. However Engin will happily run synchronous code as well.

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

