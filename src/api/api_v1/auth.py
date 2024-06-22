from fastapi import APIRouter
from src.schemas.users import UserCreate, UserRead, UserReadAfterRegister
from src.users_controller import auth_backend, fastapi_users
from .oauth import oauth_router

api_router = APIRouter(prefix="/auth", tags=["auth"])

api_router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/jwt"
)

api_router.include_router(
    fastapi_users.get_reset_password_router(),
)
api_router.include_router(
    fastapi_users.get_verify_router(UserReadAfterRegister)
)

api_router.include_router(
    fastapi_users.get_register_router(UserReadAfterRegister, UserCreate)
)

api_router.include_router(oauth_router)