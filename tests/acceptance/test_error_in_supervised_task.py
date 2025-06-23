import asyncio

from engin import Engin, Invoke, Supervisor


async def delayed_error_task():
    await asyncio.sleep(0.5)
    raise RuntimeError("Process errored")


def supervise(supervisor: Supervisor) -> None:
    supervisor.supervise(delayed_error_task)


async def test_error_in_task(caplog):
    engin = Engin(Invoke(supervise))
    await engin.run()
