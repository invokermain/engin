import asyncio
import logging
import random

from valkey.asyncio import Valkey

from engin import Supervisor


class Publisher:
    def __init__(self, valkey: Valkey) -> None:
        self._valkey = valkey

    async def run(self) -> None:
        while True:
            number = random.randint(-100, 100)
            logging.info(f"Publishing: {number}")
            await self._valkey.xadd("numbers", {"number": str(number)})
            await asyncio.sleep(1)


def publisher_factory(valkey: Valkey, supervisor: Supervisor) -> Publisher:
    publisher = Publisher(valkey=valkey)

    # run the publisher as a supervised application task
    supervisor.supervise(publisher.run)

    return publisher
