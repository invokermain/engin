import asyncio

from httpx import AsyncClient

from engin import Engin, Invoke, Provide


def new_httpx_client() -> AsyncClient:
    return AsyncClient()


async def main(http_client: AsyncClient) -> None:
    res = await http_client.get("https://httpbin.org/get")
    print(res)


engin = Engin(Provide(new_httpx_client), Invoke(main))

asyncio.run(engin.run())
