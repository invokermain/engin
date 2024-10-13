from collections.abc import Callable


class Lifecyle:
    def __init__(self) -> None:
        self._on_startup: list[Callable]

    def add_hook(self): ...
