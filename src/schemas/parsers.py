from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, field_validator, validator
from src.core.config import settings


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
    kind: Literal[tuple(settings.shikimori_kinds)] = None  # nopep8 # type: ignore


class ShikimoriTitle(BaseModel):
    last_fetch: datetime
    data: dict


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
    shikimori: ShikimoriTitle | None = None
    shikimori_loaded: bool = False

    class Config:
        from_attributes = True


class ParserInfo(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True
