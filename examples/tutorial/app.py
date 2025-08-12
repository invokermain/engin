import asyncio
import logging

from engin import Engin, Entrypoint, Provide
from examples.tutorial.publisher import Publisher, publisher_factory
from examples.tutorial.valkey_client import ValkeyBlock

logging.basicConfig(level=logging.INFO)

engin = Engin(
    ValkeyBlock,
    Provide(publisher_factory),
    Entrypoint(Publisher),
)


if __name__ == "__main__":
    asyncio.run(engin.run())
