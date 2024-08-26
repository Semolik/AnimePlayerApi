import aiohttp
from fastapi.responses import RedirectResponse
from src.schemas.users import UserRead
from src.users_controller import auth_backend, fastapi_users
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.github import GitHubOAuth2
from fastapi import APIRouter, Request, Response
from src.core.config import settings

google_oauth_client = GoogleOAuth2(
    settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET)
github_oauth_client = GitHubOAuth2(
    settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET)

oauth_router = APIRouter()

oauth_router.include_router(
    fastapi_users.get_oauth_router(
        google_oauth_client,
        auth_backend,
        settings.SECRET,
        associate_by_email=True,
        redirect_url=f"{settings.API_DOMAIN}/api/v1/auth/google/callback",
        is_verified_by_default=True,
    ),
    prefix="/google",
)
oauth_router.include_router(
    fastapi_users.get_oauth_associate_router(
        google_oauth_client, UserRead, settings.SECRET, redirect_url=settings.FRONTEND_DOMAIN),
    prefix="/associate/google",
)

oauth_router.include_router(
    fastapi_users.get_oauth_router(
        github_oauth_client,
        auth_backend,
        settings.SECRET,
        associate_by_email=True,
        redirect_url=f"{settings.API_DOMAIN}/api/v1/auth/github/callback/redirect",
        is_verified_by_default=True,
    ),
    prefix="/github",
)


@oauth_router.get("/github/callback/redirect", response_class=RedirectResponse)
async def github_callback_redirection(request: Request, response: Response):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{settings.API_DOMAIN}/api/v1/auth/github/callback", params=request.query_params) as response_callback:
            response.set_cookie(key="fastapiusersauth",
                                value=response_callback.cookies.get("fastapiusersauth"))
            return RedirectResponse(url=settings.FRONTEND_DOMAIN)
oauth_router.include_router(
    fastapi_users.get_oauth_associate_router(
        github_oauth_client, UserRead, settings.SECRET, redirect_url=settings.FRONTEND_DOMAIN),
    prefix="/associate/github",
)
