import logging

from valkey import ResponseError
from valkey.asyncio import Valkey

from engin import Supervisor


class Consumer:
    def __init__(self, valkey: Valkey) -> None:
        self._valkey = valkey
        self._total = 0

    async def run(self) -> None:
        logging.info("Consumer starting")
        try:
            await self._valkey.xgroup_create("numbers", "total", mkstream=True)
        except ResponseError:
            pass  # group already exists

        while True:
            messages = await self._valkey.xreadgroup("total", "consumer", {"numbers": ">"})
            for _, stream_messages in messages:
                for _, message in stream_messages:
                    number = int(message[b"number"])
                    self._total += number
                    logging.info(f"Consumed: {number}, Total: {self._total}")


def consumer_factory(valkey: Valkey, supervisor: Supervisor) -> Consumer:
    consumer = Consumer(valkey=valkey)

    # run the consumer as a supervised application task
    supervisor.supervise(consumer.run)

    return consumer
