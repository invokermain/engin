We'll use `pydantic-settings` to manage our configuration. Let's define a `ValkeyConfig` class.

```python
# examples/tutorial/_valkey.py
from pydantic_settings import BaseSettings
from valkey import Valkey


class ValkeyConfig(BaseSettings):
    valkey_url: str = "..."


def valkey_client_factory() -> Valkey:
    config = ValkeyConfig()
    return Valkey.from_url(config.valkey_url)
```

Our application is growing, and the `engin` definition is getting more complex. To keep our code organized, we can group related dependencies into a `Block`. A `Block` is a reusable component that can provide dependencies to the `engin`.

Let's create a `ValkeyBlock` to house our Valkey-related components.

```python
# examples/tutorial/main.py
# ...
from engin import Block, provide

class ValkeyBlock(Block):
    @provide
    def valkey_config_factory(self) -> ValkeyConfig:
        return ValkeyConfig()

    @provide
    def valkey_client_factory(self, config: ValkeyConfig) -> Valkey:
        return Valkey.from_url(config.valkey_url)
```

We've moved the `ValkeyConfig` and `valkey_client_factory` into the `ValkeyBlock` and decorated them with `@provide`. This tells the `engin` that these methods are providers.

Now, we can update our `engin` to use the `ValkeyBlock`.

```python
# examples/tutorial/main.py
# ...

engin = Engin(
    ValkeyBlock(),
    Entrypoint(Publisher),
    Entrypoint(Consumer),
)
```

Our `engin` is now much cleaner and easier to read. The `ValkeyBlock` encapsulates the details of creating the Valkey client, making our application more modular and maintainable.
