from fastapi import APIRouter
from src.api.api_v1 import auth
from src.api.api_v1 import parsers, titles, genres, episodes
api_router = APIRouter()

api_router.include_router(auth.api_router)
api_router.include_router(parsers.api_router)
api_router.include_router(titles.api_router)
api_router.include_router(genres.api_router)
api_router.include_router(episodes.api_router)
