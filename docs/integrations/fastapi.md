# FastAPI

Engin ships with a FastAPI integration that is available under the `engin.ext.fastapi`
module. The integration allows one to write idiomatic FastAPI code whilst leveraging Engin
for Dependency Injection and modularising the application.

!!! note

    There is also a
    [fastapi example](https://github.com/invokermain/engin/tree/main/examples/fastapi) in
    the Github repo if you want to see it in action.


## Setup

To run an empty FastAPI server with Engin, simply use the `FastAPIEngin` class and
provide an instance of a `FastAPI` application:

```python
from engin import Supply
from engin.extensions.fastapi import FastAPIEngin
from fastapi import FastAPI
import uvicorn

app = FastAPIEngin(Supply(FastAPI()))

if __name__ == "__main__":
    uvicorn.run(app)
```

The `FastAPIEngin` instance is just a thin wrapper on top of the FastAPI application and
exposes the normal ASGI application interface and therefore can be run by uvicorn or
other server implementations. Under the hood it will just pass calls to the `FastAPI`
instance that you provided.


!!!tip

    It is also easy to integrate Engin with an existing FastAPI application by using the
    `engin_to_lifespan` function in the `engin.ext.asgi` module.


## Dependency Injection

FastAPI comes with its own simple dependency injection system which allows you inject
depenendencies into a route by declaring a parameter with a special type hint of the form
`Annotated[T, Depends(func)]`. For example if we wanted to inject an instance of
`SomeClass`:

```python
async def make_some_class():
    return SomeClass(a=1, b=2)

@app.get("/")
async def read_items(some_class: Annotated[SomeClass, Depends(make_some_class)]):
    # do something with some_class
    return "hello"
```

Engin ships with a similar marker, called `Inject`, which can be used to inject
dependencies it has providers for, for example if Engin provided `SomeClass` instead:

```python
@app.get("/")
async def read_items(some_class: Annotated[SomeClass, Inject(SomeClass)]):
    # do something with some_class
    return "hello"
```

The `Inject` marker can be used anywhere that `Depends` can be used. This can be useful as
FastAPI dependencies can have per request lifecycle, for example if we wanted to have a
reusable SQL session per request, we could use a nested dependency:

```python
from typing import Annotated, AsyncIterable

from engin.extensions.fastapi import Inject
from fastapi import Depends


async def database_session(
        database: Annotated[Database, Inject(Database)])

    ) -> AsyncIterable[Session]:
    with database.new_session() as session:
        yield session
    session.commit()

    @ app.post("/{id}")
    async

    def add_item(session: Annotated[Session, Depends(database_session)]):
        session.add(MyORMModel(...))
```


## Attaching Routers to Engin

The usual way to declare an `APIRouter` is as a module level variable, for example:

```python title="api.py"
from fastapi import APIRouter

users_router = APIRouter(prefix="/users")

@users_router.get("/{user_id}")
def get_user(user_id: int) -> dict[str, Any]:
    return {"id": user_id, "name": "Rakim"}
```

To attach this to our `FastAPIEngin`, we need to provide it. The recommended way to do
this is to use `Supply` as the router is already instantiated. We also need to add the
`APIRouter` to our `FastAPI` application, we can do this in the provider for `FastAPI`.

```python title="app.py"
from engin.extensions.fastapi import FastAPIEngin
from fastapi import FastAPI

from api import users_router


def create_fastapi_app(api_routers: list[APIRouter]) -> FastAPI:
    app = FastAPI()

    for api_router in api_routers:
        app.include_router(api_router)

    return app


app = FastAPIEngin(Provide(create_fastapi_app), Supply([users_router]))
```

!!!info

    Notice that the `users_router` is supplied in a list, as we want to be able to
    support multiple APIRouters as our application grows.

Or similarly, we could use a block instead:

```python title="app.py"
from engin import Block, provide
from engin.extensions.fastapi import FastAPIEngin
from fastapi import FastAPI

from api import users_router


class AppBlock(Block):
    options = [Supply([users_router])]

    @provide
    def create_fastapi_app(self, api_routers: list[APIRouter]) -> FastAPI:
        app = FastAPI()

        for api_router in api_routers:
            app.include_router(api_router)

        return app


app = FastAPIEngin(AppBlock())
```


## Graphing Dependencies

Engin provides dependency visualisation functionality via the `engin graph` script. When
working with a FastAPI application this can be used to visualise API Routes along with
their respective dependencies.

![fastapi-graph.png](fastapi-graph.png){ width="500", loading=lazy }
/// caption
Visualisation of the FastAPI example's dependency graph.
///

Note that due to the split between Engin's dependency injection framework and FastAPI's,
resolving API Routers and their dependencies is slightly harder for Engin. Due to this
there is currently a limitation where Engin will only be aware of APIRouters that have
been provided using `Supply` and not via `Provide` or `@provide` in a Block.