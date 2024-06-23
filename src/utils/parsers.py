from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from fastapi.logger import logger
from src.crud.genres_crud import GenresCrud
from src.db.session import get_async_session, AsyncSession
from src.crud.titles_crud import TitlesCrud
from src.schemas.parsers import Genre, ParsedGenre, ParsedTitle, ParsedTitleShort, Title, TitleShort
from src.redis.services import ParserInfoService
from src.redis.containers import Container
from src.models.parsers import Title as TitleModel, Genre as GenreModel


@dataclass
class ParserFunctions:
    get_titles: Callable[[int], List[ParsedTitleShort]]
    get_title: Callable[[str], ParsedTitleShort]
    get_genres: Callable[[], List[ParsedGenre]]
    get_genre: Callable[[str, int], None]


class Parser:
    def __init__(self, *, id: str, name: str, titles_cache_period: int, genres_cache_period: int, functions: ParserFunctions) -> None:
        """
        :param id: The identifier to be used as the prefix for the API routes.
        :param name: The name to be used for the API router tags.
        :param titles_cache_period: The cache period in hours.
        :param genres_cache_period: The cache period in hours.
        :param functions: A ParserFunctions dataclass instance containing the parsing functions.
        :param title_id_type: The data type for the title ID, default is str.
        """

        self.parser_id = id
        self.titles_cache_period = titles_cache_period
        self.genres_cache_period = genres_cache_period
        self.functions = functions

    async def get_title(self, db_title: TitleModel, background_tasks: BackgroundTasks, db: AsyncSession, service: ParserInfoService = Depends(Provide[Container.service])):
        title_id = db_title.id
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_title = await service.get_title(parser_id=self.parser_id, title_id=title_id)
        title_obj = ParsedTitleShort(**cached_title) if cached_title else await self.update_title(id_on_website=db_title.id_on_website, service=service, raise_error=True, title_id=title_id)
        if is_expired and cached_title:
            background_tasks.add_task(
                self.update_title_in_db, id_on_website=db_title.id_on_website, title_id=title_id, db=db, service=service)
        title_db_obj = Title.model_validate(db_title)
        for key, value in title_obj.model_dump().items():
            if hasattr(title_db_obj, key):
                setattr(title_db_obj, key, value)
        return title_db_obj

    async def update_titles(self, page: int, service: ParserInfoService, raise_error: bool = False) -> List[ParsedTitleShort]:
        try:
            titles = await self.functions.get_titles(page)
            await service.set_titles(titles=[title.model_dump() for title in titles], page=page, parser_id=self.parser_id)
            await self.update_expire_status(service=service)
            return titles
        except Exception as e:
            logger.error(f'Failed to fetch titles: {e}')
            if raise_error:
                raise e

    async def update_title_in_db(self, id_on_website: str, title_id: UUID, db: AsyncSession, service: ParserInfoService, raise_error: bool = False) -> Title:
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
            await service.update_expire_status(parser_id=self.parser_id, hours=self.titles_cache_period)

    async def update_title(self, id_on_website: str, title_id: UUID, service: ParserInfoService, raise_error: bool = False) -> ParsedTitle:
        try:
            title = await self.functions.get_title(id_on_website)
            await service.set_title(title_id=title_id, title=title.model_dump(), parser_id=self.parser_id)
            return title
        except Exception as e:
            logger.error(f'Failed to fetch title: {e}')
            if raise_error:
                raise e

    async def update_genres(self, service: ParserInfoService, raise_error: bool = False) -> List[str]:
        try:
            genres = await self.functions.get_genres()
            await service.set_genres(genres=[
                genre.model_dump() for genre in genres
            ], parser_id=self.parser_id)
            await service.update_genres_expire_status(
                parser_id=self.parser_id,
                hours=self.genres_cache_period
            )
            return genres
        except Exception as e:
            logger.error(f'Failed to fetch genres: {e}')
            if raise_error:
                raise e

    @inject
    async def get_titles(self, page: int, background_tasks: BackgroundTasks, db: AsyncSession, service: ParserInfoService = Depends(Provide[Container.service])) -> List[Title]:
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_titles = await service.get_titles(parser_id=self.parser_id, page=page)

        if is_expired and cached_titles:
            background_tasks.add_task(self.update_titles, page, service)

        titles = cached_titles if cached_titles else await self.update_titles(page=page, service=service)
        return await self._prepare_titles(titles=titles, db=db, background_tasks=background_tasks)

    @inject
    async def get_genres(self, background_tasks: BackgroundTasks, db: AsyncSession, service: ParserInfoService = Depends(Provide[Container.service])) -> List[Genre]:
        genres_expired = await service.genres_expire_status(parser_id=self.parser_id)
        cached_genres = await service.get_genres(parser_id=self.parser_id)

        if genres_expired and cached_genres:
            background_tasks.add_task(self.update_genres, service)

        genres_objs = cached_genres if cached_genres else await self.update_genres(service, raise_error=True)
        return await self._prepare_genres(genres=genres_objs, db=db)

    async def update_genre(self, genre_website_id: str, genre_id: UUID, page: int, service: ParserInfoService, raise_error: bool = False) -> List[ParsedTitleShort]:
        try:
            titles = await self.functions.get_genre(genre_website_id, page)
            await service.set_genre_titles(parser_id=self.parser_id, genre_id=genre_id, page=page, titles=[title.model_dump() for title in titles])
            return titles
        except Exception as e:
            logger.error(f'Failed to fetch genre titles: {e}')
            if raise_error:
                raise e

    async def update_title_in_db(self, title_data: ParsedTitleShort, db: AsyncSession, title_id: UUID) -> Title:
        existing_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
        return await TitlesCrud(db).update_title(existing_title, title_data)

    async def title_data_changed(self, title_data: ParsedTitleShort, db_title: Title) -> bool:
        for key, value in title_data.model_dump().items():
            if hasattr(db_title, key) and getattr(db_title, key) != value:
                return True
        return False

    async def _prepare_titles(self, titles: List[ParsedTitleShort], db: AsyncSession, background_tasks: BackgroundTasks) -> List[Title]:
        db_titles = []
        existing_titles = await TitlesCrud(db).get_titles_by_website_ids(website_ids=[title.id_on_website for title in titles])
        existing_ids_set = {title.id_on_website for title in existing_titles}
        for parsed_title in titles:
            if parsed_title.id_on_website not in existing_ids_set:
                title = await TitlesCrud(db).create_title(parsed_title, self.parser_id)
            else:
                title = next(
                    title for title in existing_titles if title.id_on_website == parsed_title.id_on_website)
                if await self.title_data_changed(parsed_title, title):
                    background_tasks.add_task(
                        self.update_title_in_db, title_data=parsed_title, db=db, title_id=title.id)
            title_obj = TitleShort.model_validate(title)
            title_obj.additional_info = parsed_title.additional_info
            db_titles.append(title_obj)
        return db_titles

    async def _prepare_genres(self, genres: List[ParsedGenre], db: AsyncSession) -> List[Genre]:
        existing_genres = await GenresCrud(db).get_genres_by_website_ids(website_ids=[genre.id_on_website for genre in genres])
        existing_ids_set = {genre.id_on_website for genre in existing_genres}
        db_genres = []
        for parsed_genre in genres:
            if parsed_genre.id_on_website not in existing_ids_set:
                genre = await GenresCrud(db).create_genre(parsed_genre, self.parser_id)
            else:
                genre = next(
                    genre for genre in existing_genres if genre.id_on_website == parsed_genre.id_on_website)
            db_genres.append(genre)
        return db_genres

    async def get_genre(self, db_genre: GenreModel, page: int, background_tasks: BackgroundTasks, db: AsyncSession, service: ParserInfoService = Depends(Provide[Container.service])):
        genre_id = db_genre.id
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_titles = await service.get_genre_titles(parser_id=self.parser_id, genre_id=genre_id, page=page)
        if is_expired and cached_titles:
            background_tasks.add_task(self.update_genre, genre_id=genre_id, page=page,
                                      service=service, genre_website_id=db_genre.id_on_website)
        titles = cached_titles if cached_titles else await self.update_genre(genre_id=genre_id, page=page, service=service, raise_error=True, genre_website_id=db_genre.id_on_website)
        return await self._prepare_titles(titles=titles, db=db, background_tasks=background_tasks)


container = Container()
container.config.redis_host.from_env("REDIS_HOST", "localhost")
container.config.redis_password.from_env("REDIS_PASSWORD", "")
container.wire(modules=[__name__])
