import asyncio
import signal
import sys

import pytest

from engin import Engin

PARAMETERS = [
    pytest.param(signal.SIGINT, id="SIGINT"),
    pytest.param(
        signal.SIGTERM,
        marks=pytest.mark.skipif(
            sys.platform == "win32", reason="SIGTERM is not supported on Windows"
        ),
        id="SIGTERM",
    ),
]


@pytest.mark.parametrize("signal_value", PARAMETERS)
async def test_engin_signal_handling_when_run(signal_value):
    engin = Engin()
    task = asyncio.create_task(engin.run())
    await asyncio.sleep(0.1)
    signal.raise_signal(signal_value)
    await asyncio.sleep(0.1)
    assert engin.is_stopped()
    del task


@pytest.mark.parametrize("signal_value", PARAMETERS)
async def test_engin_signal_handling_when_start(signal_value):
    engin = Engin()
    await engin.start()
    await asyncio.sleep(0.1)
    signal.raise_signal(signal_value)
    await asyncio.sleep(0.1)
    assert engin.is_stopped()
