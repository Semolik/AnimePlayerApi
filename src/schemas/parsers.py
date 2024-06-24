from typing import Literal
import uuid
from pydantic import BaseModel


class LinkParsedTitle(BaseModel):
    id_on_website: str
    name: str


class ParsedTitleShort(LinkParsedTitle):
    image_url: str
    related_titles: list[LinkParsedTitle] = []
    additional_info: str = None


class ParsedTitle(ParsedTitleShort):
    description: str | None = None
    series: str | None = None
    year: str
    genres_names: list[str]


class TitleLink(BaseModel):
    id: uuid.UUID
    name: str
    parser_id: str

    class Config:
        from_attributes = True


class TitleShort(TitleLink):
    image_url: str
    additional_info: str = None

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


class Title(TitleShort):
    description: str | None = None
    year: str | None = None
    related: list[TitleLink] = []
    recommended: list[TitleShort] = []
    genres: list[Genre] = []

    class Config:
        from_attributes = True
