
Next, we'll create a `Consumer` to process the messages from our `Publisher`. This class will read from the `numbers` stream, parse the number from the message, and keep a running total. Just like the `Publisher`, we'll supervise the `run` method to execute it as a background task.

```python
# examples/tutorial/main.py
# ...

class Consumer:
    def __init__(self, valkey: Valkey, supervisor: Supervisor):
        self._valkey = valkey
        self._total = 0
        supervisor.supervise(self.run)

    async def run(self) -> None:
        logging.info("Consumer starting")
        await self._valkey.xgroup_create("numbers", "total", mkstream=True)
        while True:
            messages = await self._valkey.xreadgroup("total", "consumer", {"numbers": ">"})
            for _, message in messages:
                number = int(message[b"number"])
                self._total += number
                logging.info(f"Consumed: {number}, Total: {self._total}")

```

Now, we'll also register the `Consumer` as an `Entrypoint`. Since `engin` is an asynchronous framework, it can manage multiple entrypoints concurrently. Both the `Publisher` and `Consumer` will run in the same event loop.

```python
# examples/tutorial/main.py
# ...

engin = Engin(
    Provide(valkey_client_factory),
    Entrypoint(Publisher),
    Entrypoint(Consumer),
)
```