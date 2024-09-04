from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, applications
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from src.redis.containers import Container
from src.api.api_v1.api import api_router
from src.core.config import settings
from src.db.init import init_superuser
from src.db.session import create_db_and_tables
from src.utils.files import init_folders
import src.models.event_watcher
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(title=settings.PROJECT_NAME,
              openapi_url=f"{settings.API_V1_STR}/openapi.json")
print(Path("static/swagger-ui.css").exists())
if Path("static/swagger-ui.css").exists() and Path("static/swagger-ui-bundle.js").exists():
    app.mount("/assets", StaticFiles(directory='static'), name="static")

    def swagger_monkey_patch(*args, **kwargs):
        return get_swagger_ui_html(
            *args,
            **kwargs,
            swagger_favicon_url="",
            swagger_css_url="/assets/swagger-ui.css",
            swagger_js_url="/assets/swagger-ui-bundle.js",
        )
    applications.get_swagger_ui_html = swagger_monkey_patch
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
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS_LIST,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
