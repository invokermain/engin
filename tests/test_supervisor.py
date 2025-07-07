import asyncio
import contextlib
from asyncio import CancelledError
from dataclasses import dataclass

from engin import OnException, Supervisor


async def delayed_error_task():
    await asyncio.sleep(0.05)
    raise RuntimeError("Process errored")


async def happy_task():
    await asyncio.sleep(1)


async def endless_task():
    await asyncio.sleep(999)


async def block_task():
    await asyncio.sleep(999)


@dataclass
class ClassHappyTask:
    async def run(self) -> None:
        await asyncio.sleep(1)


async def test_empty_supervisor():
    supervisor = Supervisor()

    with contextlib.suppress(CancelledError):
        async with supervisor:
            await asyncio.sleep(0.1)


async def test_supervisor_on_exception_retry():
    supervisor = Supervisor()
    attempt = 0

    async def retry_task():
        nonlocal attempt
        if attempt == 0:
            attempt += 1
            raise RuntimeError("Process errored")

    supervisor.supervise(retry_task, on_exception=OnException.RETRY)

    with contextlib.suppress(CancelledError):
        async with supervisor:
            await asyncio.sleep(0.1)

    assert supervisor._tasks[0].complete
    assert isinstance(supervisor._tasks[0].last_exception, RuntimeError)
    assert attempt == 1


async def test_supervisor_on_exception_ignore():
    supervisor = Supervisor()

    async def error_task():
        raise RuntimeError("Process errored")

    async def complete_task():
        await asyncio.sleep(0.09)

    supervisor.supervise(error_task, on_exception=OnException.IGNORE)
    supervisor.supervise(complete_task, on_exception=OnException.SHUTDOWN)

    with contextlib.suppress(CancelledError):
        async with supervisor:
            await asyncio.sleep(0.1)

    assert supervisor._tasks[0].complete
    assert isinstance(supervisor._tasks[0].last_exception, RuntimeError)
    assert supervisor._tasks[1].complete
    assert supervisor._tasks[1].last_exception is None


async def test_supervisor():
    supervisor = Supervisor()

    supervisor.supervise(delayed_error_task)
    supervisor.supervise(happy_task)
    supervisor.supervise(ClassHappyTask().run)

    with contextlib.suppress(CancelledError):
        async with supervisor:
            await asyncio.sleep(1)

    # task one completed and has error (as raised exception)
    assert supervisor._tasks[0].complete
    assert supervisor._tasks[0].last_exception is not None

    # task two did not complete and has no error (as was cancelled)
    assert not supervisor._tasks[1].complete
    assert supervisor._tasks[1].last_exception is None

    # task three did not complete and has no error (as was cancelled)
    assert not supervisor._tasks[2].complete
    assert supervisor._tasks[2].last_exception is None


async def test_supervisor_is_cancellable():
    supervisor = Supervisor()

    supervisor.supervise(endless_task)

    await supervisor.__aenter__()
    await asyncio.wait_for(supervisor.__aexit__(None, None, None), 0.1)
