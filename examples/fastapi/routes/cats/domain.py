from enum import Enum

from pydantic import BaseModel, ConfigDict


class CatPersonality(Enum):
    CUTE = "CUTE"
    EVIL = "EVIL"


class Cat(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    name: str
    breed: str
    age: float
    personality: CatPersonality
