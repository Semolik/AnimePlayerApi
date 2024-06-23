from dataclasses import dataclass
from typing import Callable, Generic, TypeVar
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from fastapi.logger import logger
from src.db.session import get_async_session, AsyncSession
from src.crud.titles_crud import TitlesCrud
from src.schemas.parsers import ParsedTitleShort, Title
from src.redis.services import ParserInfoService
from src.redis.containers import Container
from src.models.parsers import Title as TitleModel

@dataclass
class ParserFunctions:
    get_titles: Callable[[int], list[ParsedTitleShort]]
    get_title: Callable[[str], None]
    # get_genres: Callable[[int], None]
    # get_genre: Callable[[str], None]


class Parser:
    def __init__(self, *, id: str, name: str, cache_period: int, functions: ParserFunctions) -> None:
        """
        :param id: The identifier to be used as the prefix for the API routes.
        :param name: The name to be used for the API router tags.
        :param cache_period: The cache period in hours.
        :param functions: A ParserFunctions dataclass instance containing the parsing functions.
        :param title_id_type: The data type for the title ID, default is str.
        """
            
        self.parser_id = id
        self.cache_period = cache_period
        self.functions = functions
    
    async def get_title(self, title_id: UUID, background_tasks: BackgroundTasks, db: AsyncSession, service: ParserInfoService = Depends(Provide[Container.service])):
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_title = await service.get_title(parser_id=self.parser_id, title_id=title_id)
        existing_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
        if not existing_title:
            raise HTTPException(status_code=404, detail="Title not found.")
        title_obj = ParsedTitleShort(**cached_title) if cached_title else await self.update_title(id_on_website=existing_title.id_on_website, service=service, raise_error=True, title_id=title_id)
        if is_expired:
            background_tasks.add_task(self.update_title_in_db, existing_title.id_on_website, title_id, db, service)
        title_db_obj = Title.model_validate(existing_title)
        title_db_obj.additional_info = title_obj.additional_info
        return title_db_obj

    
    async def update_titles(self, page: int, service: ParserInfoService, raise_error:bool = False) -> list[ParsedTitleShort]:
        try:
            titles = await self.functions.get_titles(page)
            await service.set_titles(titles=[title.model_dump() for title in titles], page=page, parser_id=self.parser_id)
            await self.update_expire_status(service=service)
            return titles
        except Exception as e:
            logger.error(f'Failed to fetch titles: {e}')
            if raise_error:
                raise e
    
    async def update_title_in_db(self, id_on_website: str, title_id: UUID, db: AsyncSession, service: ParserInfoService, raise_error:bool = False) -> Title:
        try:
            title = await self.update_title(id_on_website=id_on_website, title_id=title_id, service=service, raise_error=True)
            db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
            await TitlesCrud(db).update_title(db_title, title)
            await self.update_expire_status(service=service)
        except Exception as e:
            logger.error(f'Failed to fetch title: {e}')
            if raise_error:
                raise e
            
    async def update_expire_status(self, service: ParserInfoService = Depends(Provide[Container.service])):
        expired = await service.expire_status(parser_id=self.parser_id)
        if expired:
            await service.update_expire_status(parser_id=self.parser_id, hours=self.cache_period)
            
    async def update_title(self, id_on_website: str, title_id: UUID, service: ParserInfoService, raise_error:bool = False) -> ParsedTitleShort:
        try:
            title = await self.functions.get_title(id_on_website)
            await service.set_title(title_id=title_id, title=title.model_dump(), parser_id=self.parser_id)
            return title
        except Exception as e:
            logger.error(f'Failed to fetch title: {e}')
            if raise_error:
                raise e

    @inject
    async def get_titles(self, page: int, background_tasks: BackgroundTasks, db: AsyncSession, service: ParserInfoService = Depends(Provide[Container.service])) -> list[Title]:
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_titles = await service.get_titles(parser_id=self.parser_id, page=page)

        if is_expired and cached_titles:
            background_tasks.add_task(self.update_titles, page, service)
        titles = [ParsedTitleShort(**title) for title in cached_titles] if cached_titles else await self.update_titles(page=page, service=service)

        website_ids = [title.id_on_website for title in titles]
        existing_titles = await TitlesCrud(db).get_titles_by_website_ids(website_ids=website_ids)
        existing_ids_set = {title.id_on_website for title in existing_titles}
        db_titles = []
        for parsed_title in titles:
            if parsed_title.id_on_website not in existing_ids_set:
                title = await TitlesCrud(db).create_title(parsed_title, self.parser_id)
            else:
                title = next(title for title in existing_titles if title.id_on_website == parsed_title.id_on_website)
            title_obj = Title.model_validate(title)
            title_obj.additional_info = parsed_title.additional_info
            db_titles.append(title_obj)
        return db_titles

    async def get_genres(self, page: int):
        pass

    async def get_genre(self, genre: str):
        pass

container = Container()
container.config.redis_host.from_env("REDIS_HOST", "localhost")
container.config.redis_password.from_env("REDIS_PASSWORD", "")
container.wire(modules=[__name__])