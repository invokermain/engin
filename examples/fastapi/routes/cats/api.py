from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel

from engin.extensions.fastapi import Inject
from examples.fastapi.routes.cats.domain import Cat, CatPersonality
from examples.fastapi.routes.cats.ports import CatRepository

router = APIRouter(prefix="/cats")


@router.get("/{cat_id}")
async def get_cat(
    cat_id: int,
    repository: Annotated[CatRepository, Inject(CatRepository)],
) -> Cat:
    return repository.get(cat_id=cat_id)


class CatPostModel(BaseModel):
    name: str
    breed: str
    age: float
    personality: CatPersonality


@router.post("/")
async def post_cat(
    cat: CatPostModel,
    repository: Annotated[CatRepository, Inject(CatRepository)],
) -> int:
    cat_id = repository.next_id()
    cat_domain = Cat(
        id=cat_id,
        name=cat.name,
        personality=cat.personality,
        age=cat.age,
        breed=cat.breed,
    )
    repository.set(cat=cat_domain)
    return cat_id
