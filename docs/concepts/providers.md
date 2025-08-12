# Providers

Providers are the factories of your application, they are responsible for the construction
of the objects that your application needs.

Remember, the Engin only calls the providers that are necessary to run your application.
More specifically: when starting up the Engin will call all providers necessary to run its
invocations, and the Assembler (the component responsible for constructing types) will
call any providers that these providers require and so on.


## Defining a provider

Any function that returns an object can be turned into a provider by using the marker
class: `Provide`.

```python
from engin import Engin, Provide


# define our constructor
def string_factory() -> str:
    return "hello"


# register it as a provider with the Engin
engin = Engin(Provide(string_factory))

# construct the string
a_string = await engin.assembler.build(str)

print(a_string)  # hello
```

Providers can be asynchronous as well, this factory function would work exactly the same
in the above example.

```python
async def string_factory() -> str:
   return "hello"
```

## Providers can use other providers

Providers that construct more interesting objects generally require their own parameters.

```python
from engin import Engin, Provide


class Greeter:
    def __init__(self, greeting: str) -> None:
        self._greeting = greeting

    def greet(self, name: str) -> None:
        print(f"{self._greeting}, {name}!")


# define our constructors
def string_factory() -> str:
    return "hello"


def greeter_factory(greeting: str) -> Greeter:
    return Greeter(greeting=greeting)


# register them as providers with the Engin
engin = Engin(Provide(string_factory), Provide(greeter_factory))

# construct the Greeter
greeter = await engin.assembler.build(Greeter)

greeter.greet("Bob")  # hello, Bob!
```

## Providers are only called when required

The Assembler will only call a provider when the type is requested, directly or indirectly
when constructing an object. This means that your application will do the minimum work
required on startup.

```python
from engin import Engin, Provide


# define our constructors
def string_factory() -> str:
    return "hello"


def evil_factory() -> int:
    raise RuntimeError("I have ruined your plans")


# register them as providers with the Engin
engin = Engin(Provide(string_factory), Provide(evil_factory))

# this will not raise an error
await engin.assembler.build(str)

# this will raise an error
await engin.assembler.build(int)
```


## Multiproviders

Sometimes it is useful for many providers to construct a single collection of objects,
these are called multiproviders. For example in a web application, many
distinct providers could register one or more routes, and the root of the application
would handle registering them.

To turn a factory into a multiprovider, simply return a list:

```python
from engin import Engin, Provide


# define our constructors
def animal_names_factory() -> list[str]:
    return ["cat", "dog"]


def other_animal_names_factory() -> list[str]:
    return ["horse", "cow"]


# register them as providers with the Engin
engin = Engin(Provide(animal_names_factory), Provide(other_animal_names_factory))

# construct the list of strings
animal_names = await engin.assembler.build(list[str])

print(animal_names)  # ["cat", "dog", "horse", "cow"]
```


## Discriminating providers of the same type

Providers of the same type can be discriminated using annotations.

```python
from engin import Engin, Provide
from typing import Annotated


# define our constructors
def greeting_factory() -> Annotated[str, "greeting"]:
    return "hello"


def name_factory() -> Annotated[str, "name"]:
    return "Jelena"


# register them as providers with the Engin
engin = Engin(Provide(greeting_factory), Provide(name_factory))

# this will return "hello"
await engin.assembler.build(Annotated[str, "greeting"])

# this will return "Jelena"
await engin.assembler.build(Annotated[str, "name"])

# N.B. this will raise an error!
await engin.assembler.build(str)
```


## Supply can be used for static objects

The `Supply` marker class can be used as a shorthand when provided static objects. The
provided type is automatically inferred.

For example the first example on this page could be rewritten as:

```python
from engin import Engin, Supply

# Supply the Engin with a str value
engin = Engin(Supply("hello"))

# construct the string
a_string = await engin.assembler.build(str)

print(a_string)  # hello
```

## Overriding providers from the same package

Sometimes you need to replace an existing provider for the same type. If both providers
originate from the same Python package, overrides must be explicit by setting
`override=True` on the replacement provider. This prevents accidental overrides.

```python
from engin import Engin, Provide, Supply


def make_number() -> int:
    return 1


def make_number_override() -> int:
    return 2


engin = Engin(
    Provide(make_number),
    # Explicitly override the previous provider from the same package
    Provide(make_number_override, override=True),
)

# this will return 2
await engin.assembler.build(int)
```

You can also use `override=True` with `Supply`, and with the `@provide` decorator inside `Block`
classes: `@provide(override=True)`.

!!!tip

    Overriding providers from a different package is allowed implicitly. Explicit overrides are
    only required when replacing a provider defined in the same package. Adding or overriding a
    provider clears previously assembled values so subsequent builds use the new provider.

    Multiproviders (providers that return lists) are not replaced; new ones are always appended.


## Provider scopes

Providers can be associated with a named scope. A scoped provider can only be used while that
scope is active, and its cached value is cleared when the scope exits.

To set a scope, pass `scope="..."` to `Provide`, or use the `@provide(scope=...)` decorator
when defining providers inside a `Block`.

```python
from engin import Engin, Provide
import time


def make_timestamp() -> int:
    return time.time_ns()


# Register a provider that is only valid in the "request" scope
engin = Engin(Provide(make_timestamp, scope="request"))

# Outside the scope this will raise an error
# await engin.assembler.build(int)  # NotInScopeError

# Within the scope the value can be built and is cached for the duration
with engin.assembler.scope("request"):
    t1 = await engin.assembler.build(int)
    t2 = await engin.assembler.build(int)
    assert t1 == t2  # cached within the active scope

# After leaving the scope, the scoped cache is cleared
# await engin.assembler.build(int)  # NotInScopeError
```

Scopes compose via a stack. Nested scopes can be entered with additional
`with engin.assembler.scope("..."):` contexts. When a scope exits, any values produced by
providers in that scope are removed from the cache, while values produced by
unscoped providers remain cached.

!!!note

    In web applications built with `ASGIEngin`, each request is automatically wrapped in
    `with engin.assembler.scope("request"):`. Marking providers with `scope="request"` yields
    per-request values that are reused within the same request and discarded at the end of the
    request.
