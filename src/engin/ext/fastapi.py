import typing
from typing import ClassVar, TypeVar

from engin import Engin, Invoke, Option
from engin.ext.asgi import ASGIEngin

try:
    from fastapi import FastAPI
    from fastapi.params import Depends
    from starlette.requests import HTTPConnection
except ImportError:
    raise ImportError("fastapi must be installed to use the corresponding extension")


if typing.TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.params import Depends

__all__ = ["FastAPIEngin", "Inject"]


def _attach_engin(
    app: FastAPI,
    engin: Engin,
) -> None:
    app.state.engin = engin


class FastAPIEngin(ASGIEngin):
    _LIB_OPTIONS: ClassVar[list[Option]] = [*ASGIEngin._LIB_OPTIONS, Invoke(_attach_engin)]  # type: ignore[arg-type]
    _asgi_type = FastAPI


T = TypeVar("T")


def Inject(interface: type[T]) -> Depends:
    async def inner(conn: HTTPConnection) -> T:
        engin: Engin = conn.app.state.engin
        return await engin.assembler.get(interface)

    return Depends(inner)
