# Providers

Providers are the factories of your application, they are reponsible for the construction
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