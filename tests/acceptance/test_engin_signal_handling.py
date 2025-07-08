import asyncio
import signal
import sys

import pytest

from engin import Engin


@pytest.mark.skipif(sys.platform == "win32", reason="`signal.raise_signal` not supported")
async def test_engin_signal_handling_when_run():
    engin = Engin()
    task = asyncio.create_task(engin.run())
    await asyncio.sleep(0.1)
    signal.raise_signal(signal.SIGTERM)
    await asyncio.sleep(0.1)
    assert engin.is_stopped()
    del task


@pytest.mark.skipif(sys.platform == "win32", reason="`signal.raise_signal` not supported")
async def test_engin_signal_handling_when_start():
    engin = Engin()
    await engin.start()
    await asyncio.sleep(0.1)
    signal.raise_signal(signal.SIGTERM)
    await asyncio.sleep(0.1)
    assert engin.is_stopped()
