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