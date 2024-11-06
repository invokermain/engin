from engin import Block, provide
from examples.asgi.common.db.adapaters.memory import InMemoryDatabase
from examples.asgi.common.db.ports import DatabaseInterface


class DatabaseBlock(Block):
    @provide
    def database(self) -> DatabaseInterface:
        return InMemoryDatabase()
