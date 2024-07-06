from datetime import datetime, timedelta
from fastapi import BackgroundTasks
from src.schemas.parsers import ParsedTitle, ShikimoriTitle
from src.redis.services import CacheService
from shikimori_api import Shikimori
from src.core.config import settings
session = Shikimori()
api = session.get_api()


class Shikimori:
    def __init__(self, service: CacheService) -> None:
        self.service = service

    async def get_title(self, title: ParsedTitle) -> ShikimoriTitle:
        title_info = api.animes.GET(
            search=title.en_name or title.name, kind=title.kind)
        if len(title_info) > 0:
            return await self.service.set_shikimori_title(title_info[0]['id'], title_info[0])

    async def update_shikimori_title(self, title_id: int):
        title_json = await api.animes.GET(id=title_id)
        title = self.service.set_shikimori_title(title_id, title_json)
        return title

    async def get_shikimori_title(self, title_id: int, background_tasks: BackgroundTasks) -> ShikimoriTitle:
        cached = await self.service.get_shikimori_title(title_id)
        if not cached:
            title = await self.update_shikimori_title(title_id)
        else:
            title = cached
            if title.last_fetch < datetime.now() - timedelta(days=7):
                background_tasks.add_task(
                    self.update_shikimori_title, title_id)
        return title
