from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.redis.containers import Container
from src.api.api_v1.api import api_router
from src.core.config import settings
from src.db.init import init_superuser
from src.db.session import create_db_and_tables
from src.utils.files import init_folders
import src.models.event_watcher

app = FastAPI(title=settings.PROJECT_NAME,
              openapi_url=f"{settings.API_V1_STR}/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.50.32"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.API_V1_STR)


main_app_lifespan = app.router.lifespan_context


@asynccontextmanager
async def lifespan_wrapper(app):
    await create_db_and_tables()
    await init_superuser()
    init_folders()
    async with main_app_lifespan(app) as maybe_state:
        yield maybe_state

app.router.lifespan_context = lifespan_wrapper
