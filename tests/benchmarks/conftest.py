import asyncio

import pytest


@pytest.fixture
async def aio_benchmark(benchmark):
    async def run_async_coroutine(func, *args, **kwargs):
        return await func(*args, **kwargs)

    def _wrapper(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):

            @benchmark
            def _():
                future = asyncio.ensure_future(run_async_coroutine(func, *args, **kwargs))
                return asyncio.get_event_loop().run_until_complete(future)
        else:
            benchmark(func, *args, **kwargs)

    return _wrapper
