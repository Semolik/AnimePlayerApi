import uuid
from pydantic import BaseModel, EmailStr
from fastapi_users.schemas import BaseUserCreate, BaseUser
from src.schemas.images import ImageLink


class BaseUserEmail(BaseModel):
    email: EmailStr


class CustomUserFields(BaseModel):
    name: str | None = None


class UserReadAfterRegister(BaseUser[uuid.UUID], CustomUserFields):
    pass


class UserRead(UserReadAfterRegister):
    image: ImageLink | None = None
    pass


class UserReadWithEmail(UserRead, BaseUserEmail):
    pass


class UserCreate(BaseUserCreate, CustomUserFields):
    pass


class UserUpdate(CustomUserFields, BaseUserEmail):
    pass


class ChangePassword(BaseModel):
    new_password: str
