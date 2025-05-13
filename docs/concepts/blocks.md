# Blocks

A Block is a collection of options defined as a class.

Blocks are useful for grouping related options, as they can then be passed to the Engin in
one go helping manage complex applications.

Blocks are preferred over other data structures such as a list of options as they
integrate with other functionality in the rest of the framework.


## Defining an empty Block

A Block is just a class that inherits from `Block`:

```python
from engin import Engin, Block, provide, invoke


class ExampleBlock(Block):
    ...
```

## Adding options to the Block

Blocks have a class attribute named `options` which can be used to include existing
options.

```python
from engin import Engin, Block, Invoke, Provide, Supply


def print_string(self, string: str) -> None:
   print(string)

   
class ExampleBlock(Block):
   options = [
      Supply("hello"),
      Invoke(print_string)
   ]


# register it as a provider with the Engin
engin = Engin(ExampleBlock())

await engin.run()  # prints 'hello'
```

!!!tip

Blocks are themselves valid options, so Blocks can include other Blocks as options. This
compisitional approach can help you build and manage larger applications.


## Defining Providers & Invocations in the Block

Engin ships two decorators: `@provide` & `@invoke` that can be used to define providers
and invocations within a Block as methods. These decorators mirror the signature of their
respective classes `Provide` & `Invoke`.


```python
from engin import Engin, Block, provide, invoke


# this block is equivalent to the one in the example above
class ExampleBlock(Block):
    @provide
    def string_factory() -> str:
        return "hello"
    
    @invoke
    def print_string(self, string: str) -> None:
       print(string)
```

!!!note

The `self` parameter in these methods is replaced with an empty object at runtime so
should not be used. Blocks do not need to be instantiated to be passed to Engin as an
option.
