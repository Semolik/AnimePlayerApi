from datetime import datetime, timedelta
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
    recommended_titles: list['ParsedTitleShort'] = []
    additional_info: str | None = None
    genres_names: list[str] = []


class ParsedTitlesPage(BaseModel):
    titles: list[ParsedTitleShort]
    total_pages: int


class ParsedLink(BaseModel):
    name: str
    link: str


class ParsedEpisode(BaseModel):
    name: str
    links: list[ParsedLink]
    number: int
    preview: str | None = None


class ParsedTitle(ParsedTitleShort):
    description: str | None = None
    series_info: str
    year: str
    episodes_list: list[ParsedEpisode] = []
    kind: Literal[tuple(settings.shikimori_kinds)] | None = None  # nopep8 # type: ignore


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


class TitlesPage(BaseModel):
    titles: list[TitleShort]
    total_pages: int


class ParsedGenre(BaseModel):
    name: str
    id_on_website: str

    class Config:
        from_attributes = True


class Genre(BaseModel):
    id: uuid.UUID
    name: str
    parser_id: str

    class Config:
        from_attributes = True


class Episode(BaseModel):
    id: uuid.UUID
    name: str
    progress: int = 0
    number: int
    links: list[ParsedLink]
    is_m3u8: bool = False
    image_url: str | None = None


class TitleEpisode(Episode):
    title_id: uuid.UUID
    image_url: str

    class Config:
        from_attributes = True


class Title(TitleShort):
    description: str | None = None
    series_info: str | None = None
    year: str | None = None
    liked: bool = False
    genres: list[Genre] = []
    episodes: list[Episode] = []
    related: list[TitleLink] = []
    recommended: list[TitleShort] = []
    shikimori: ShikimoriTitle | None = None

    class Config:
        from_attributes = True


class ParserInfo(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True
