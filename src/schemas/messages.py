from typing import Literal
from pydantic import BaseModel
from uuid import UUID
from src.core.config import settings


class BaseMessage(BaseModel):
    content: str
    order: int = 0
    color: Literal[tuple(settings.message_colors)] | None = None  # nopep8 # type: ignore


class Message(BaseMessage):
    id: UUID

    class Config:
        from_attributes = True
