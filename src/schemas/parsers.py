import uuid
from pydantic import BaseModel


class ParsedTitleShort(BaseModel):
    name: str
    image_url: str
    additional_info:str = None
    id_on_website: str

class ParsedTitle(ParsedTitleShort):
    description: str | None = None
    series: str | None = None

class Title(BaseModel):
    id: uuid.UUID
    name: str
    parser_id: str
    page_fetched: bool = False
    image_url: str
    additional_info: str = None

    class Config:
        from_attributes = True

class ParsedGenre(BaseModel):
    name: str
    id_on_website: str
    description: str | None = None

class Genre(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    parser_id: str

    class Config:
        from_attributes = True