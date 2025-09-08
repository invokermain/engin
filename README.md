# Engin 🏎️

[![codecov](https://codecov.io/gh/invokermain/engin/graph/badge.svg?token=4PJOIMV6IB)](https://codecov.io/gh/invokermain/engin)

---

**Documentation**: [https://engin.readthedocs.io/](https://engin.readthedocs.io/)

**Source Code**: [https://github.com/invokermain/engin](https://github.com/invokermain/engin)

---

Engin is a lightweight application framework powered by dependency injection, it helps
you build and maintain large monoliths and many microservices.


## Features

The Engin framework gives you:

- A fully-featured dependency injection system.
- A robust application runtime with lifecycle hooks and supervised background tasks.
- Zero boilerplate code reuse across applications.
- Integrations for other frameworks such as FastAPI.
- Full async support.
- CLI commands to aid local development.


## Installation

Engin is available on PyPI, install it using your favourite dependency manager:

- `pip install engin`
- `poetry add engin`
- `uv add engin`

## Example

A small example which shows some of the features of Engin. This application
makes 3 http requests and shuts itself down.

```python
import asyncio
from httpx import AsyncClient
from engin import Engin, Invoke, Lifecycle, OnException, Provide, Supervisor


def httpx_client_factory(lifecycle: Lifecycle) -> AsyncClient:
    # create our http client
    client = AsyncClient()
    # this will open and close the AsyncClient as part of the application's lifecycle
    lifecycle.append(client)
    return client


async def main(
    httpx_client: AsyncClient,
    supervisor: Supervisor,
) -> None:
    async def http_requests_task():
        # simulate a background task
        for x in range(3):
            await httpx_client.get("https://httpbin.org/get")
            await asyncio.sleep(1.0)
        # raise an error to shutdown the application, normally you wouldn't do this!
        raise RuntimeError("Forcing shutdown")

    # supervise the http requests as part of the application's lifecycle
    supervisor.supervise(http_requests_task, on_exception=OnException.SHUTDOWN)


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
INFO:httpx:HTTP Request: GET https://httpbin.org/get "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: GET https://httpbin.org/get "HTTP/1.1 200 OK"
ERROR:engin:supervisor task 'http_requests_task' raised RuntimeError, starting shutdown
Traceback (most recent call last):
  File "C:\dev\python\engin\src\engin\_supervisor.py", line 58, in __call__
    await self.factory()
  File "C:\dev\python\engin\readme_example.py", line 29, in http_requests_task
    raise RuntimeError("Forcing shutdown")
RuntimeError: Forcing shutdown
INFO:engin:stopping engin
INFO:engin:shutdown complete
```

## Inspiration

Engin is heavily inspired by [Uber's Fx framework for Go](https://github.com/uber-go/fx)
and the [Injector framework for Python](https://github.com/python-injector/injector).

They are both great projects, go check them out.

## Benchmarks

Automated benchmarks for the Engin framework can be viewed
[here](https://invokermain.github.io/engin/dev/bench/).
