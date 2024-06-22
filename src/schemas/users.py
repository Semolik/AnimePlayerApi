import uuid
from pydantic import BaseModel, EmailStr
from fastapi_users.schemas import BaseUserCreate, BaseUser, BaseUserUpdate


class BaseUserEmail(BaseModel):
    email: EmailStr


class CustomUserFields(BaseModel):
    name: str


class UserReadAfterRegister(BaseUser[uuid.UUID], CustomUserFields):
    pass


class UserRead(UserReadAfterRegister):
    pass


class UserReadWithEmail(UserRead, BaseUserEmail):
    pass


class UserCreate(BaseUserCreate, CustomUserFields):
    pass


class UserUpdate(BaseUserUpdate, CustomUserFields):
    pass

