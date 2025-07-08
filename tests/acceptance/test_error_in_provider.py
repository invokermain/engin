import asyncio

import pytest

from engin import Engin, Invoke, Provide
from engin.exceptions import ProviderError


async def test_error_in_provider_when_run():
    async def raise_value_error() -> int:
        raise ValueError("foo")

    async def main(foo: int) -> None:
        return

    engin = Engin(Provide(raise_value_error), Invoke(main))

    with pytest.raises(ProviderError, match="foo"):
        await asyncio.wait_for(engin.run(), timeout=0.5)


async def test_error_in_provider_when_start():
    async def raise_value_error() -> int:
        raise ValueError("foo")

    async def main(foo: int) -> None:
        return

    engin = Engin(Provide(raise_value_error), Invoke(main))

    with pytest.raises(ProviderError, match="foo"):
        await asyncio.wait_for(engin.start(), timeout=0.5)

    # check we can shutdown the app
    await asyncio.wait_for(engin.stop(), timeout=0.5)
