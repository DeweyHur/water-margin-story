from pydantic import BaseModel

class Map(BaseModel):
    id: int
    name: str
    width: int
    height: int
    towns: list[str]