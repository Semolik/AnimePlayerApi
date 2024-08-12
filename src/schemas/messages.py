from pydantic import BaseModel
from uuid import UUID


class BaseMessage(BaseModel):
    content: str
    order: int = 0


class Message(BaseMessage):
    id: UUID

    class Config:
        from_attributes = True
