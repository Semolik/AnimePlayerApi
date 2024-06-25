from typing import Literal
import uuid
from pydantic import BaseModel


class LinkParsedTitle(BaseModel):
    id_on_website: str
    name: str
    en_name: str | None = None


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


class FavoriteTitle(TitleLink):
    image_url: str


class TitleShort(FavoriteTitle):

    additional_info: str = None
    en_name: str | None = None

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
    liked: bool = False

    class Config:
        from_attributes = True
