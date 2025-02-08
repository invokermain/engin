# Providers

Providers are the factories of your application, they are reponsible for the construction
of the objects that your application needs.

The Engin only calls the providers that are necessary to do its job. More specifically:
when starting up the Engin will call all providers necessary to run its invocations, and
the Assembler (the component responsible for constructing types) will call any providers
that these providers require and so on.

## Defining a provider

Any function that returns an object can be turned into a provider by using the marker
class: 'Provide'.

```python
from engin import Engin, Provide

# define our constructor
def string_factory() -> str:
   return "hello"

# register it as a provider with the Engin
engin = Engin(Provide(string_factory))

# construct the string
a_string = await engin.assembler.get(str)

print(a_string) # hello
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
greeter = await engin.assembler.get(Greeter)

greeter.greet("Bob") # hello, Bob!
```

# Providers are only called when required

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

# this does not raise an error
await engin.assembler.get(str)

# this does raise an error
await engin.assembler.get(int)
```

# Multiproviders

Sometimes it is useful for many providers to construct a single collection of objects,
these are called multiproviders. An example usecase is in a web application, many
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
animal_names = await engin.assembler.get(list[str])

print(animal_names) # ["cat", "dog", "horse", "cow"]
```
