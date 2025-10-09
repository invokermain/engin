# Engin 🏎️

[![codecov](https://codecov.io/gh/invokermain/engin/graph/badge.svg?token=4PJOIMV6IB)](https://codecov.io/gh/invokermain/engin)
![Downloads](https://img.shields.io/pypi/dw/engin)
---

**Documentation**: [https://engin.readthedocs.io/](https://engin.readthedocs.io/)

**Source Code**: [https://github.com/invokermain/engin](https://github.com/invokermain/engin)

---

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

Engin is available on PyPI, install it using your favourite dependency manager:

- `pip install engin`
- `poetry add engin`
- `uv add engin`

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

## Inspiration

Engin is heavily inspired by [Uber's Fx framework for Go](https://github.com/uber-go/fx)
and the [Injector framework for Python](https://github.com/python-injector/injector).

They are both great projects, go check them out.

## Benchmarks

Automated performance benchmarks for Engin are available [here](https://invokermain.github.io/engin/dev/bench/).
