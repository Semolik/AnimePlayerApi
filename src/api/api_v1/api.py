from fastapi import APIRouter
from src.api.api_v1 import auth
from src.api.api_v1 import parsers
api_router = APIRouter()

api_router.include_router(auth.api_router)
api_router.include_router(parsers.api_router)
