from dataclasses import dataclass
from typing import Callable, Generic, TypeVar
from fastapi import APIRouter, BackgroundTasks, Depends
from dependency_injector.wiring import inject, Provide
from fastapi.logger import logger
from src.db.session import get_async_session, AsyncSession
from src.crud.titles_crud import TitlesCrud
from src.schemas.parsers import ParsedTitleShortInt, ParsedTitleShortStr, Title, TitleIntId, TitleStrId
from src.redis.services import ParserInfoService
from src.redis.containers import Container

@dataclass
class ParserFunctions:
    get_titles: Callable[[int], list[ParsedTitleShortInt | ParsedTitleShortStr]]
    # get_title: Callable[[str | int], None]
    # get_genres: Callable[[int], None]
    # get_genre: Callable[[str], None]


class Parser:
    def __init__(self, *, id: str, name: str, cache_period: int, functions: ParserFunctions, title_id_type: type = str) -> None:
        """
        :param id: The identifier to be used as the prefix for the API routes.
        :param name: The name to be used for the API router tags.
        :param cache_period: The cache period in hours.
        :param functions: A ParserFunctions dataclass instance containing the parsing functions.
        :param title_id_type: The data type for the title ID, default is str.
        """
            
        self.parser_id = id
        self.title_id_type = title_id_type
        self.cache_period = cache_period
        self.functions = functions
        self.router = APIRouter(prefix=f'/{id}', tags=[f'{name} parser'])
        
        self.add_endpoint('/titles', self.get_titles, response_model=list[TitleIntId if title_id_type == int else TitleStrId])
        self.add_endpoint('/titles/{id}', self.get_title_type_wrapper())
        self.add_endpoint('/genres', self.get_genres)
        self.add_endpoint('/genres/{genre}', self.get_genre)

    def get_schema(self, id_type: type = str) -> ParsedTitleShortInt | ParsedTitleShortStr:
        if id_type == int:
            return ParsedTitleShortInt
        return ParsedTitleShortStr

    def add_endpoint(self, path: str, endpoint_function, method: str = "GET", **kwargs):
        if method == "GET":
            self.router.get(path, **kwargs)(endpoint_function)
        elif method == "POST":
            self.router.post(path, **kwargs)(endpoint_function)
    
    async def get_title(self, id: str | int):
        pass

    def get_title_type_wrapper(self):
        async def get_title_by_id(id: self.title_id_type):
            return await self.get_title(id=id)
        return get_title_by_id
    
    async def update_titles(self, page: int, service: ParserInfoService, raise_error:bool = False) -> list[ParsedTitleShortInt | ParsedTitleShortStr]:
        try:
            titles = await self.functions.get_titles(page)
            await service.set_titles(titles=[title.model_dump() for title in titles], page=page, parser_id=self.parser_id)
            return titles
        except Exception as e:
            logger.error(f'Failed to fetch titles: {e}')
            if raise_error:
                raise e

    @inject
    async def get_titles(self, page: int, background_tasks: BackgroundTasks, service: ParserInfoService = Depends(Provide[Container.service]), db: AsyncSession = Depends(get_async_session)):
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_titles = await service.get_titles(parser_id=self.parser_id, page=page)

        if is_expired and cached_titles:
            background_tasks.add_task(self.update_titles, page, service)

        titles = [self.get_schema(self.title_id_type)(**title) for title in cached_titles] if cached_titles else await self.update_titles(page=page, service=service)

        website_ids = [str(title.id_on_website) for title in titles]
        existing_titles = await TitlesCrud(db).get_titles_by_website_ids(website_ids=website_ids)
        existing_ids_set = {title.id_on_website for title in existing_titles}
        db_titles = []
        for parsed_title in titles:
            str_id = str(parsed_title.id_on_website)
            if str_id not in existing_ids_set:
                title = await TitlesCrud(db).create_title(parsed_title, self.parser_id)
            else:
                title = next(title for title in existing_titles if title.id_on_website == str_id)
            db_titles.append(title)
        return db_titles

    async def get_genres(self, page: int):
        pass

    async def get_genre(self, genre: str):
        pass

container = Container()
container.config.redis_host.from_env("REDIS_HOST", "localhost")
container.config.redis_password.from_env("REDIS_PASSWORD", "")
container.wire(modules=[__name__])