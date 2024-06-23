from src.schemas.users import UserRead
from src.users_controller import auth_backend, fastapi_users
from httpx_oauth.clients.google import GoogleOAuth2
from fastapi import APIRouter
from src.core.config import settings

google_oauth_client = GoogleOAuth2(
    settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET)
oauth_router = APIRouter()
oauth_router.include_router(
    fastapi_users.get_oauth_router(
        google_oauth_client,
        auth_backend,
        "SECRET",
        is_verified_by_default=True,
    ),
    prefix="/google",
)
oauth_router.include_router(
    fastapi_users.get_oauth_associate_router(
        google_oauth_client, UserRead, "SECRET"),
    prefix="/associate/google",
)
