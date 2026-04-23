# Modifiers

Modifiers allow you to alter values that have already been provided in the dependency graph.
A modifier takes a value of type T and returns a modified value of the same type T. Modifiers
are applied after the original provider is called.

This is useful when you want to augment or transform a provided value without replacing
the original provider, for example adding logging, wrapping with middleware, or applying
configuration.


## Defining a modifier

Any function that takes a value and returns the same type can be turned into a modifier
by using the marker class: `Modify`.

```python
from engin import Engin, Modify, Provide


def make_greeting() -> str:
    return "hello"


def add_excitement(greeting: str) -> str:
    return f"{greeting}!"


engin = Engin(Provide(make_greeting), Modify(add_excitement))

result = await engin.assembler.build(str)

print(result)  # hello!
```

The modifier receives the output from the provider and can transform it before returning.


## Modifiers can use other providers

Like providers, modifiers can depend on other types in the graph. The first parameter
is always the value being modified, and additional parameters are resolved from the
dependency graph.

```python
from engin import Engin, Modify, Provide


def make_greeting() -> str:
    return "hello"


def make_int() -> int:
    return 3


def add_repetition(greeting: str, times: int) -> str:
    return " ".join([greeting] * times)


engin = Engin(
    Provide(make_greeting),
    Provide(make_int),
    Modify(add_repetition),
)

result = await engin.assembler.build(str)

print(result)  # hello hello hello
```


## Modified values are cached

Like provider outputs, modified values are cached. The modifier is only called once,
and subsequent requests for the type return the cached modified value.

```python
from engin import Engin, Modify, Provide


call_count = 0


def make_number() -> int:
    return 1


def double_number(value: int) -> int:
    global call_count
    call_count += 1
    return value * 2


engin = Engin(Provide(make_number), Modify(double_number))

await engin.assembler.build(int)  # returns 2, call_count is 1
await engin.assembler.build(int)  # returns 2, call_count is still 1
```


## Only one modifier per type per scope

Engin supports one modifier per type at each scope level (global or per-block). If you
register multiple modifiers for the same type at the same scope level, you must use
`override=True` on the replacement modifier.

```python
from engin import Engin, Modify, Provide


def make_greeting() -> str:
    return "hello"


def add_prefix(value: str) -> str:
    return f"[INFO] {value}"


def add_suffix(value: str) -> str:
    return f"{value}!!!"


engin = Engin(
    Provide(make_greeting),
    Modify(add_prefix),
    Modify(add_suffix, override=True),  # replaces add_prefix
)

result = await engin.assembler.build(str)

print(result)  # hello!!!
```


## Using modifiers in Blocks

Within a Block, you can use the `@modify` decorator to define modifiers as methods.
Modifiers defined inside a Block are **scoped to that block** — they only affect
resolutions within the block's own invocations and do not affect other blocks or
top-level invocations.

```python
from engin import Block, Engin, Invoke, Provide, modify, invoke


class GreetingBlock(Block):
    @modify
    def add_excitement(self, greeting: str) -> str:
        return f"{greeting}!"

    @invoke
    def print_greeting(self, greeting: str) -> None:
        print(greeting)  # hello! (modified)


def print_raw(greeting: str) -> None:
    print(greeting)  # hello (unmodified)


def make_greeting() -> str:
    return "hello"


engin = Engin(Provide(make_greeting), GreetingBlock(), Invoke(print_raw))
```

In this example, `GreetingBlock`'s `print_greeting` invocation sees the modified value
`"hello!"`, while the top-level `print_raw` invocation sees the raw value `"hello"`.

### Composing with global modifiers

Block modifiers compose with global modifiers. When both exist for the same type, the
block modifier receives the globally-modified value as its input:

```python
from engin import Block, Engin, Modify, Provide, modify, invoke


def add_prefix(value: str) -> str:
    return f"[INFO] {value}"


class GreetingBlock(Block):
    @modify
    def upper(self, value: str) -> str:
        return value.upper()

    @invoke
    def print_greeting(self, greeting: str) -> None:
        print(greeting)  # [INFO] HELLO (global then block modifier)


engin = Engin(
    Provide(lambda: "hello", as_type=str),
    Modify(add_prefix),
    GreetingBlock(),
)
```

### Nested block composition

When blocks are nested (a block includes another block via `options`), inner blocks inherit
modifiers from their outer blocks. If both define a modifier for the same type, the outer
modifier is applied first and its result is passed to the inner modifier:

```python
from typing import ClassVar
from engin import Block, Engin, Provide, modify, invoke
from engin._option import Option


class InnerBlock(Block):
    @modify
    def add_suffix(self, value: str) -> str:
        return f"{value}!"

    @invoke
    def print_greeting(self, greeting: str) -> None:
        print(greeting)  # FOO! (outer then inner modifier)


class OuterBlock(Block):
    options: ClassVar[list[Option]] = [InnerBlock()]

    @modify
    def upper(self, value: str) -> str:
        return value.upper()


engin = Engin(Provide(lambda: "foo", as_type=str), OuterBlock())
```

In this example, `InnerBlock`'s invocation sees the value after both modifiers are applied:
`"foo"` → `"FOO"` (outer) → `"FOO!"` (inner). An inner block without its own modifier for
the type will simply inherit the outer block's modifier.

The `@modify` decorator accepts the same parameters as `Modify`, such as `override=True`:

```python
@modify(override=True)
def replace_modifier(self, value: str) -> str:
    return f"replaced: {value}"
```
