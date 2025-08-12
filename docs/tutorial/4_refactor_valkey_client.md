In the last section we saw an exception when shutting down our application.

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

Analysing this we can infer that the `Valkey` client is trying to close itself as its been
garbage collected, but the application is already shutdown so its too late.

If we look at the `valkey-py` docs we see this line.

> Using asyncio Valkey requires an explicit disconnect of the connection since there is no
> asyncio deconstructor magic method.

So we want to call `aclose()` on the `Valkey` client when the application is shutting down.
Luckily this type of concern is quite common and Engin provides another built-in dependency to
help manage this, the `Lifecycle`.

Let's update our `valkey_client_factory` to handle this lifecycle concern.

```python title="valkey_client.py"
from engin import Lifecycle
from valkey.asyncio import Valkey

def valkey_client_factory(lifecycle: Lifecycle) -> Valkey:
    client = Valkey.from_url("valkey://localhost:6379")

    # close the client when the app is shutting down
    lifecycle.hook(on_stop=client.aclose)

    return client
```

Now when we run the application we will not see any errors.

While we are here we can continue to improve the factory by making the connection url
configurable. We can use `pydantic-settings` for this by defining a `ValkeyConfig` class and
creating a factory for it.

```python title="valkey_client.py"
from engin import Lifecycle
from pydantic_settings import BaseSettings
from valkey.asyncio import Valkey

class ValkeyConfig(BaseSettings):
    valkey_url: str = "..."

def valkey_config() -> ValkeyConfig:
    return ValkeyConfig()

def valkey_client_factory(config: ValkeyConfig, lifecycle: Lifecycle) -> Valkey:
    client = Valkey.from_url(config.valkey_url)
    lifecycle.hook(on_stop=client.aclose)
    return client
```

To keep our code organized, we can group related dependencies into a "block". We can then
register the block with our application instead, this makes sure that all Valkey related
dependencies are always registered.

We can create a block by inheriting from the `Block` type. Factory functions become
methods in the block marked with decorator equivalents of the marker types we saw before to,
e.g. `Provide` & `Invoke` become `@provide` & `@invoke`.

```python title="valkey_client.py"
from engin import Block, provide

class ValkeyBlock(Block):
    @provide
    def config_factory(self) -> ValkeyConfig:
        return ValkeyConfig()

    @provide
    def client_factory(config: ValkeyConfig, lifecycle: Lifecycle) -> Valkey:
        client = Valkey.from_url(config.valkey_url)
        lifecycle.hook(on_stop=client.aclose)
        return client
```

Now, we can update our `engin` to use the `ValkeyBlock`.

```python title="app.py"
# ... existing code ...

engin = Engin(
    ValkeyBlock,
    Provide(publisher_factory),
    Entrypoint(Publisher),
)
```
