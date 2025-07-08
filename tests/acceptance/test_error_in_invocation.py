import asyncio

import pytest

from engin import Engin, Invoke


async def test_error_in_invocation_when_run():
    async def main() -> None:
        raise ValueError("foo")

    engin = Engin(Invoke(main))

    with pytest.raises(ValueError, match="foo"):
        await asyncio.wait_for(engin.run(), timeout=0.5)


async def test_error_in_invocation_when_start():
    async def main() -> None:
        raise ValueError("foo")

    engin = Engin(Invoke(main))

    with pytest.raises(ValueError, match="foo"):
        await asyncio.wait_for(engin.start(), timeout=0.5)

    # check we can shutdown the app
    await asyncio.wait_for(engin.stop(), timeout=0.5)
