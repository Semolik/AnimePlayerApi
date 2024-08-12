from fastapi import APIRouter, Depends, HTTPException, Query
from src.db.session import get_async_session, AsyncSession
from src.schemas.messages import Message, BaseMessage
from src.crud.messages_crud import MessagesCrud
from src.users_controller import current_superuser
from uuid import UUID
api_router = APIRouter(prefix="/messages", tags=["messages"])


@api_router.get("", response_model=list[Message])
async def get_messages(db: AsyncSession = Depends(get_async_session)):
    return await MessagesCrud(db).get_messages()


@api_router.post("", response_model=Message, status_code=201, dependencies=[Depends(current_superuser)])
async def create_message(message_data: BaseMessage, db: AsyncSession = Depends(get_async_session)):
    return await MessagesCrud(db).create_message(content=message_data.content, order=message_data.order, color=message_data.color)


@api_router.put("/{message_id}", response_model=Message, dependencies=[Depends(current_superuser)])
async def update_message(message_id: UUID, message_data: BaseMessage, db: AsyncSession = Depends(get_async_session)):
    message = await MessagesCrud(db).get_by_id(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found.")
    return await MessagesCrud(db).update_message(message=message, content=message_data.content, order=message_data.order, color=message_data.color)


@api_router.delete("/{message_id}", response_model=None, status_code=204, dependencies=[Depends(current_superuser)])
async def delete_message(message_id: UUID, db: AsyncSession = Depends(get_async_session)):
    message = await MessagesCrud(db).get_by_id(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found.")
    await MessagesCrud(db).delete(message)
