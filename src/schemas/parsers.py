import uuid
from pydantic import BaseModel


class ParsedTitleShortBase(BaseModel):
    name: str
    image_url: str
    additional_info:str = None

class ParsedTitleShortInt(ParsedTitleShortBase):
    id_on_website: int

class ParsedTitleShortStr(ParsedTitleShortBase):
    id_on_website: str


class Title(BaseModel):
    id: uuid.UUID
    parser_id: str
    name: str
    page_fetched: bool = False
    description: str | None
    image_url: str
    additional_info:str = None

class TitleIntId(Title):
    id_on_website: int

class TitleStrId(Title):
    id_on_website: str