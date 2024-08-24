from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.models.files import Image
from src.models.users import User
from src.schemas.users import UserUpdate
from src.crud.base import BaseCRUD
from src.utils.files import save_image

from src.users_controller import get_password_hash


class UsersCrud(BaseCRUD):

    async def get_user_by_id(self, user_id: int) -> User:
        query = select(User).where(User.id == user_id).options(
            selectinload(User.image))
        return (await self.db.execute(query)).scalar()

    async def get_user_by_email(self, email: str) -> User:
        query = select(User).where(User.email == email).options(
            selectinload(User.image))
        return (await self.db.execute(query)).scalar()

    async def update_user(self, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump().items():
            setattr(user, field, value)
        await self.update(user)
        return user

    async def change_password(self, user: User, new_password: str) -> User:
        user.hashed_password = await get_password_hash(new_password)
        return await self.update(user)

    async def update_user_image(self, user: User, image: UploadFile) -> Image | None:
        if user.image_id:
            image_id = user.image_id
            user.image_id = None
            old_image = await self.get(image_id, Image)
            await self.delete(old_image)
        image_model = await save_image(db=self.db, upload_file=image)
        user.image_id = image_model.id
        await self.update(user)
        return image_model

    async def delete_user_image(self, user: User) -> None:
        if user.image_id:
            image_id = user.image_id
            user.image_id = None
            old_image = await self.get(image_id, Image)
            await self.delete(old_image)
            await self.update(user)
