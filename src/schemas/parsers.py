from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel,  model_validator, validator
from src.core.config import settings
month_names = [
    "января", "февраля", "марта",
    "апреля", "мая", "июня",
    "июля", "августа", "сентября",
    "октября", "ноября", "декабря"
]


class BaseTitleInfo(BaseModel):
    name: str
    en_name: str | None = None
    image_url: str


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
    quality: int | None = None


class ParsedEpisode(BaseModel):
    name: str
    links: list[ParsedLink]
    number: int
    preview: str | None = None
    is_m3u8: bool = False


class ParsedTitle(ParsedTitleShort):
    description: str | None = None
    series_info: str | None = None
    year: str | None = None
    episodes_list: list[ParsedEpisode] = []
    kind: Literal[tuple(settings.shikimori_kinds)] | None = None  # nopep8 # type: ignore
    duration: str | None = None
    episodes_message: str | None = None


class ShikimoriTitle(BaseModel):
    last_fetch: datetime
    data: dict


class TitleShortLink(BaseModel):
    id: uuid.UUID
    parser_id: str


class TitleLink(TitleShortLink):
    name: str
    en_name: str | None = None

    class Config:
        from_attributes = True


class FavoriteTitle(TitleLink):
    image_url: str


class TitleShort(FavoriteTitle):

    additional_info: str = None

    class Config:
        from_attributes = True


class SearchTitle(BaseTitleInfo):
    on_other_parsers: list[TitleShortLink] = []


class TitlesPage(BaseModel):
    titles: list[TitleShort]
    total_pages: int


class MainPage(TitlesPage):
    pages_on_main: int = 1


class ParsedGenre(BaseModel):
    name: str
    id_on_website: str

    class Config:
        from_attributes = True


class GenreBase(BaseModel):
    id: uuid.UUID
    parser_id: str

    class Config:
        from_attributes = True


class Genre(GenreBase):
    name: str

    class Config:
        from_attributes = True


class UniqueGenre(BaseModel):
    name: str
    variants: list[GenreBase]

    class Config:
        from_attributes = True


class Episode(BaseModel):
    id: uuid.UUID
    name: str
    progress: int = 0
    seconds: int = 0
    number: int
    is_m3u8: bool = False
    image_url: str | None = None
    duration: int | None = None
    links: list[ParsedLink] = []
    duration_label: str | None = None

    @validator("duration_label", always=True)
    def duration_label_validator(cls, v, values):
        if v:
            return v
        duration = values.get("duration")
        if duration:
            return f"{duration // 60} мин."
        return None

    class Config:
        from_attributes = True


class TitleEpisodes(BaseModel):
    title: TitleShort
    episodes: list[Episode]

    class Config:
        from_attributes = True


class TitleEpisode(Episode):
    title_id: uuid.UUID
    title: TitleShort
    image_url: str

    @model_validator(mode='before')
    def image_url_validator(self):
        print(self.title.image_url)
        if not self.image_url:
            self.image_url = self.title.image_url
        return self

    class Config:
        from_attributes = True


class Title(TitleShort):
    description: str | None = None
    series_info: str | None = None
    year: str | None = None
    liked: bool = False
    current_episode: Episode | None = None
    genres: list[Genre] = []
    episodes: list[Episode] = []
    related: list[TitleShort] = []
    recommended: list[TitleShort] = []
    shikimori: ShikimoriTitle | None = None
    shikimori_failed: bool = False
    duration: str | None = None
    episodes_message: str | None = None
    on_other_parsers: list[TitleLink] = []

    class Config:
        from_attributes = True


class ParserInfo(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class HistoryDay(BaseModel):
    date: datetime
    date_label: str | None = None
    episodes: list[TitleEpisode]

    @validator("date_label", always=True)
    def date_label_validator(cls, v, values):
        if v:
            return v
        date = values.get("date")
        date_label = f"{date.day} {month_names[date.month - 1]}"
        if date.year != datetime.now().year:
            date_label += f" {date.year}"
        return date_label

    class Config:
        from_attributes = True
