# Invocations

Invocations define the behaviour of your application, therefore without any Invocations
your application will not do anything.

Like providers, invocations are functions that take one or more dependencies as
parameters, but they should always return None as the return value will not used by Engin.

As part of the Engin's startup, all declared invocations will be called sequentially in
the order they were registered.

Invocations can be used to define behaviour in two ways.

**Implicit: Provider Lifecycle**

Invocations are always called and therefore their dependencies are always assembled. This
means that any providers with lifecycles will register their lifecycles with the
application if directly or indirectly used by an invocation.

To illustrate this, imagine we have a provider for an imaginary `Worker` type that is our
applications primary functionality. Our factory might look like the below (omitting 
imports for brevity):

```python
def worker_factory(lifecycle: Lifecycle) -> Worker:
    worker = Worker()
   
    lifecycle.hook(
        on_start=worker.start,
        on_stop=worker.shutdown
    )
   
    return worker
```

We can register it with the Engin as a provider.

```python 
engin = Engin(Provide(worker_factory))
```

However, when we run the `engin` nothing happens. It will not start the `Worker` as it is
not required by any invocations. Let us fix that by adding the invocation.

```python
def use_worker(worker: Worker) -> None:
    return None


engin = Engin(Provide(worker_factory), Invoke(use_worker))
```

Now when we run the `engin` a `Worker` is constructed and it starts up. This invocation
has no behaviour of its own, hence we can call it implicit, but by registering it with the
Engin it declares the behaviour we want our modular application to have at runtime.

This pattern of empty invocations as declaration of intended behaviour is very common, so
the framework has a marker class called `Entrypoint` as a shorthand for the above.

```python
engin = Engin(Provide(worker_factory), Entrypoint(Worker))
```

This `engin` has the same behaviour as the one declared above. Entrypoints can be
considered idiomatic as they have more explicit semantics.

**Explicit: Invoked Behaviour**

Sometimes you want to have logic that runs before the lifecycle startup occurs and after
the dependency graph is built, some examples might be:

- Pinging a server to check its healthy.
- Running database migrations.
- Configuring a logger.

In these cases you would simply write an invocation that does these things, for example:

```python
def run_database_migrations(conn: SQLConnection) -> None:
    print("running database migrations")
    required_migrations = get_migrations(conn)
    for migration in required_migrations:
        print(f"migrating database to version {migration.version}")
        migration.execute(conn)

engin = Engin(Provide(sql_connection_factory), Invoke(run_database_migrations), ...)
```


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
