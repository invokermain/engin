# Invocations

Invocations define the behaviour of your application, without any Invocations your
application will not do anything.

Invocations usually take one ore more parameters and always return None, as the return
type is not used by the Engin.


## Defining an invocation

Any function can be turned into an invocation by using the marker class: `Invoke`.

```python
import asyncio
from engin import Engin, Invoke

# define a function with some behaviour
def print_hello_world() -> None:
   print("hello world!")

# register it as a invocation with the Engin
engin = Engin(Invoke(print_hello_world))

# run your application
asyncio.run(engin.run())  # hello world!
```


## Invocations can use provided types

Invocations can use any types as long as they have the matching providers.

```python
import asyncio
from engin import Engin, Invoke

# define a constructor
def name_factory() -> str:
    return "Dmitrii"

def print_hello(name: str) -> None:
   print(f"hello {name}!")

# register it as a invocation with the Engin
engin = Engin(Provide(name_factory()), Invoke(hello_world))

# run your application
asyncio.run(engin.run())  # hello Dmitrii!
```
