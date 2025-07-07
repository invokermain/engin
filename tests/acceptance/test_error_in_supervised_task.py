import asyncio
import logging

from engin import Engin, Invoke, Supervisor


async def delayed_error_task():
    raise RuntimeError("Process errored")


def supervise(supervisor: Supervisor) -> None:
    supervisor.supervise(delayed_error_task)


async def test_error_in_supervised_task_handled_when_run(caplog):
    caplog.set_level(logging.INFO)
    engin = Engin(Invoke(supervise))
    await engin.run()
    assert "Process errored" in caplog.text
    assert engin.is_stopped()


async def test_error_in_supervised_task_handled_when_start(caplog):
    caplog.set_level(logging.INFO)
    engin = Engin(Invoke(supervise))
    await engin.start()
    await asyncio.sleep(0.1)
    assert "Process errored" in caplog.text
    assert engin.is_stopped()
