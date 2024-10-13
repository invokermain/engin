from httpx import AsyncClient

from engin import Engin, Provide


async def test_provide_async():
    async def provider() -> AsyncClient:
        return AsyncClient()

    provide = Provide(provider)
    assert provide.provided_type == "httpx.AsyncClient"

    Engin(provide)
