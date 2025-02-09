from uuid import UUID
from sqlalchemy import select
from src.crud.base import BaseCRUD
from src.models.messages import Message


class MessagesCrud(BaseCRUD):

    async def create_message(self, content: str, order: int, color: str | None) -> Message:
        message = Message(content=content, order=order, color=color)
        return await self.create(message)

    async def get_messages(self) -> list[Message]:
        query = select(Message).order_by(
            Message.created_at.desc(), Message.order.desc())
        return (await self.db.execute(query)).scalars().all()

    async def update_message(self, message: Message, content: str, order: int, color: str | None) -> Message:
        message.content = content
        message.order = order
        message.color = color
        return await self.update(message)

    async def get_by_id(self, message_id: UUID) -> Message:
        query = select(Message).where(Message.id == message_id)
        return (await self.db.execute(query)).scalar()
