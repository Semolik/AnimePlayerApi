
from pydantic import BaseModel, field_validator, model_validator, validator
from src.models.files import Image
from src.utils.files import get_image_link
from uuid import UUID

from pydantic_core import core_schema


class ImageLink(BaseModel):
    '''convert relationship to image link'''
    @classmethod
    def validate(cls, v, handler) -> str | None:
        if not v:
            return None
        if isinstance(v, str):  # regex test
            return v
        if not isinstance(v, Image):
            raise TypeError('ImageLink must be Image (model)')
        return get_image_link(image_id=v.id)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, _handler) -> core_schema.CoreSchema:
        return core_schema.no_info_wrap_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )


class ImageInfo(BaseModel):
    id: UUID
    url: str = None

    @validator('url', pre=True, always=True)
    def set_url(cls, url, values, **kwargs):
        if url is not None:
            return
        return get_image_link(values['id'])

    class Config:
        from_attributes = True
