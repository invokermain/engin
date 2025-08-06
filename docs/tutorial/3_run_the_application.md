Let's try to run our application.

```bash
$ python examples/tutorial/main.py
INFO:engin:starting engin
INFO:engin:startup complete
INFO:engin:stopping engin
INFO:engin:shutdown complete
```

You'll notice that the application starts and then immediately shuts down. This is because we haven't told `engin` to actually *do* anything. We have registered providers, but nothing is using them. The `engin` will only assemble dependencies that are required by an `Invocation` or `Entrypoint`.

To fix this, we'll register the `Publisher` as an `Entrypoint`. This tells the `engin` that the `Publisher` is a core component of our application and should be started.

```python
# examples/tutorial/main.py
# ...
from engin import Entrypoint

engin = Engin(
    Provide(valkey_client_factory),
    Entrypoint(Publisher),
)
```

Now if you run the application, you will see the publisher running and logging messages.