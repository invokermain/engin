from pydantic_settings import BaseSettings
from valkey.asyncio import Valkey

from engin import Block, Lifecycle, provide


class ValkeyConfig(BaseSettings):
    valkey_url: str = "valkey://localhost:6379"


class ValkeyBlock(Block):
    @provide
    def config(self) -> ValkeyConfig:
        return ValkeyConfig()

    @provide
    def client(self, config: ValkeyConfig, lifecycle: Lifecycle) -> Valkey:
        client: Valkey = Valkey.from_url(config.valkey_url)

        # close the client when the app is shutting down
        lifecycle.hook(on_stop=client.aclose)

        return client
