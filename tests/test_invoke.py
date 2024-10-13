from httpx import AsyncClient

from engin import Invoke
from engin._utils import type_to_key


async def test_invoke():
    invoked = False

    def invocation(http_client: AsyncClient) -> None:
        assert isinstance(http_client, AsyncClient)
        nonlocal invoked
        invoked = True

    invoke = Invoke(invocation)
    invoke.bind({type_to_key(AsyncClient): AsyncClient()})

    await invoke()
    assert invoked
