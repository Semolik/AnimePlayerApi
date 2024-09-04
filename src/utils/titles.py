from src.redis.services import CacheService
from src.crud.titles_crud import TitlesCrud
from src.db.session import AsyncSession
from src.utils.shikimori import Shikimori
from src.schemas.parsers import SearchTitle, TitleShortLink
from src.redis.containers import Container
from fastapi import Depends
from dependency_injector.wiring import Provide
from src.core.config import settings


class TitlesService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.retries = 3

    async def get_popular_titles(self, page_size: int = 10, service: CacheService = Depends(Provide[Container.service])) -> list[SearchTitle]:
        page = 1
        titles_objs = []
        while page < self.retries:
            titles_page = await Shikimori(service).get_popular_ongoings(page)
            for title in titles_page:
                linked_titles = await TitlesCrud(self.db).get_titles_by_shikimori_id(shikimori_id=int(title['id']))
                if linked_titles:
                    title_obj = SearchTitle.model_validate(
                        linked_titles[0], from_attributes=True)
                    title_obj.on_other_parsers = [TitleShortLink.model_validate(
                        linked, from_attributes=True) for linked in linked_titles]

                    titles_objs.append(title_obj)
                if len(titles_objs) >= page_size:
                    break
            else:
                page += 1
                continue
            break
        return titles_objs


container = Container()
container.config.redis_host.from_value(settings.REDIS_HOST)
container.config.redis_password.from_value(settings.REDIS_PASSWORD)
container.wire(modules=[__name__])
