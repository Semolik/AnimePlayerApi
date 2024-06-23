import uuid
from pydantic import BaseModel


class ParsedTitleShort(BaseModel):
    name: str
    image_url: str
    additional_info: str = None
    id_on_website: str


class ParsedTitle(ParsedTitleShort):
    description: str | None = None
    series: str | None = None
    year: str


class TitleShort(BaseModel):
    id: uuid.UUID
    name: str
    image_url: str
    parser_id: str
    additional_info: str = None

    class Config:
        from_attributes = True


class Title(TitleShort):
    description: str | None = None
    year: str | None = None

    class Config:
        from_attributes = True


class ParsedGenre(BaseModel):
    name: str
    id_on_website: str


class Genre(BaseModel):
    id: uuid.UUID
    name: str
    parser_id: str

    class Config:
        from_attributes = True
