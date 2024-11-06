from starlette.routing import Mount, Route

from engin import Block, provide
from examples.asgi.common.db.ports import DatabaseInterface
from examples.asgi.features.cats.api.get import GetCatEndpoint
from examples.asgi.features.cats.api.post import PostCatEndpoint


class CatBlock(Block):
    @provide
    def get_cat_route(self, db: DatabaseInterface) -> GetCatEndpoint:
        return GetCatEndpoint(db=db)

    @provide
    def post_cat_route(self, db: DatabaseInterface) -> PostCatEndpoint:
        return PostCatEndpoint(db=db)

    @provide
    def mount(
        self,
        get_cat_endpoint: GetCatEndpoint,
        post_cat_endpoint: PostCatEndpoint,
    ) -> list[Mount]:
        return [
            Mount(
                "/cats",
                routes=[
                    Route(
                        "/{name:str}",
                        get_cat_endpoint,
                        methods=get_cat_endpoint.ALLOWED_METHODS,
                    ),
                    Route(
                        "/",
                        get_cat_endpoint,
                        methods=get_cat_endpoint.ALLOWED_METHODS,
                    ),
                    Route(
                        "/",
                        post_cat_endpoint,
                        methods=post_cat_endpoint.ALLOWED_METHODS,
                    ),
                ],
            )
        ]
