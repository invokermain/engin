Let's try to run our application.

```
INFO:engin:starting engin
INFO:engin:startup complete
```

And then stop it.

```
INFO:engin:stopping engin
INFO:engin:shutdown complete
```

Where are the publisher logs? Well we haven't actually told our application to actually *do*
anything yet. We have registered providers, but nothing is using them. Engin will only assemble
dependencies that are required by an `Invocation` or `Entrypoint`.

To fix this, we can mark the `Publisher` as an `Entrypoint`. This tells our application that
the `Publisher` should always be assembled, which will cause the `Publisher.run` method to be
registered as a supervised task.

```python title="app.py"
# ... existing code ...
from examples.tutorial.publisher import Publisher, publisher_factory
from engin import Entrypoint

engin = Engin(
    Provide(publisher_factory),
    Provide(valkey_client_factory),
    Entrypoint(Publisher),
)
```

Now if you run the application, you will see the publisher running and logging messages.

```
INFO:engin:starting engin
INFO:engin:startup complete
INFO:engin:supervising task: Publisher.run
INFO:root:Publishing: -55
INFO:root:Publishing: 15
```

However, when we stop the application we see a weird exception to do with the `Valkey` client.

```
INFO:engin:stopping engin
INFO:engin:shutdown complete
Exception ignored in: <function AbstractConnection.__del__ at 0x0000021E6273B880>
Traceback (most recent call last):
  File "C:\dev\python\engin\.venv\Lib\site-packages\valkey\asyncio\connection.py", line 243, in __del__
  File "C:\dev\python\engin\.venv\Lib\site-packages\valkey\asyncio\connection.py", line 250, in _close
  File "C:\Users\tutorial\AppData\Roaming\uv\python\cpython-3.13.0-windows-x86_64-none\Lib\asyncio\streams.py", line 352, in close
  File "C:\Users\tutorial\AppData\Roaming\uv\python\cpython-3.13.0-windows-x86_64-none\Lib\asyncio\proactor_events.py", line 109, in close
  File "C:\Users\tutorial\AppData\Roaming\uv\python\cpython-3.13.0-windows-x86_64-none\Lib\asyncio\base_events.py", line 829, in call_soon
  File "C:\Users\tutorial\AppData\Roaming\uv\python\cpython-3.13.0-windows-x86_64-none\Lib\asyncio\base_events.py", line 552, in _check_closed
RuntimeError: Event loop is closed
```

Let's take another look at the `Valkey` client factory.
