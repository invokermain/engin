import asyncio

from engin import Engin, Invoke, Lifecycle


async def delayed_error_task():
    await asyncio.sleep(0.5)
    raise RuntimeError("Process errored")


def a(lifecycle: Lifecycle) -> None:
    lifecycle.supervise(delayed_error_task)


async def test_error_in_task(caplog):
    engin = Engin(Invoke(a))

    with caplog.at_level("ERROR"):
        await engin.run()

    # a logged an error
    assert any("Process errored" in record.message for record in caplog.records)
