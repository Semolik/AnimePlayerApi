from fastapi import APIRouter
from  src.parsers import animevost

api_router = APIRouter(prefix="/parsers")

parsers = [animevost.parser]

for parser in parsers:
    api_router.include_router(parser.router)