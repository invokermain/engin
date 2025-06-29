import asyncio
from asyncio import TaskGroup

from engin import Engin
from engin._engin import _EnginState


async def test_engin_signal_handling():
    engin = Engin()

    async with TaskGroup() as tg:
        tg.create_task(engin.run())
        # give it time to startup
        await asyncio.sleep(0.1)

        assert engin._state == _EnginState.RUNNING

        # closest thing to emulating the actual signal with subprocesses
        engin._stop_requested_event.set()

        # give it time to shutdown
        await asyncio.sleep(0.1)

        assert engin._state == _EnginState.SHUTDOWN
