from dataclasses import dataclass
from typing import Callable, List
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from dependency_injector.wiring import Provide
from fastapi.logger import logger
from src.crud.episodes_crud import EpisodesCrud
from src.crud.genres_crud import GenresCrud
from src.db.session import AsyncSession
from src.crud.titles_crud import TitlesCrud
from src.schemas.parsers import Genre, LinkParsedTitle, ParsedGenre, ParsedEpisode, ParsedTitle, ParsedTitleShort, ParsedTitlesPage, Episode, Title, TitleLink, TitleShort, ShikimoriTitle, TitlesPage
from src.redis.services import CacheService
from src.redis.containers import Container
from src.models.parsers import Title as TitleModel, Genre as GenreModel
from src.models.users import User as UserModel
from src.utils.shikimori import Shikimori
from src.core.config import settings
from abc import ABC, abstractmethod


@dataclass
class ParserFunctions:
    get_titles: Callable[[int], ParsedTitlesPage]
    get_title: Callable[[str], ParsedTitleShort]
    get_genres: Callable[[], List[ParsedGenre]]
    get_genre: Callable[[str, int], ParsedTitlesPage]


class Parser(ABC):
    def __init__(self, *, id: str, name: str, functions: ParserFunctions, main_pages_count: int = 1, order: int = 0):
        """
        :param id: The identifier to be used as the prefix for the API routes.
        :param name: The name to be used for the API router tags.
        :param titles_cache_period: The cache period in hours.
        :param genres_cache_period: The cache period in hours.
        :param functions: A ParserFunctions dataclass instance containing the parsing functions.
        :param title_id_type: The data type for the title ID, default is str.
        """
        self.name = name
        self.parser_id = id
        self.titles_cache_period = settings.titles_cache_hours
        self.genres_cache_period = settings.genres_cache_hours
        self.functions = functions
        self.main_pages_count = main_pages_count
        self.order = order

    def get_custom_router(self):
        pass

    async def get_title_data(self, db_title: TitleModel, service: CacheService) -> ParsedTitle:
        title_id = db_title.id
        is_expired, cached_title = await self._get_cached_title(title_id, service)
        if not cached_title or is_expired or not db_title.image_url:
            title_obj = await self._update_title_cache(db_title.id_on_website, title_id, service)
        else:
            title_obj = ParsedTitle(**cached_title)
        return title_obj

    async def get_title(self, db_title: TitleModel, background_tasks: BackgroundTasks, db: AsyncSession, current_user: UserModel, service: CacheService = Depends(Provide[Container.service])) -> Title:
        title_obj = await self.get_title_data(db_title=db_title, service=service)
        title_result_obj = await self._prepare_title(title_obj=title_obj, db_title=db_title, db=db, background_tasks=background_tasks, current_user=current_user, service=service)
        return title_result_obj

    async def get_title_episodes(self, db_title: TitleModel, db: AsyncSession, current_user: UserModel, service: CacheService = Depends(Provide[Container.service])) -> List[Episode]:
        title_obj = await self.get_title_data(db_title=db_title, service=service)
        return await self.prepare_episodes(title=title_obj, title_id=db_title.id, db=db, service=service, current_user=current_user)

    async def get_titles(self, page: int, background_tasks: BackgroundTasks, db: AsyncSession, service: CacheService = Depends(Provide[Container.service])) -> TitlesPage:
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_titles_page = await service.get_titles(parser_id=self.parser_id, page=page)
        if is_expired and cached_titles_page:
            background_tasks.add_task(self.update_titles, page, service)
        titles_page = cached_titles_page if cached_titles_page else await self.update_titles(page=page, service=service, raise_error=True)
        return await self._prepare_titles(titles_page=titles_page, db=db, background_tasks=background_tasks)

    async def get_main_titles(self, background_tasks: BackgroundTasks, db: AsyncSession, service: CacheService = Depends(Provide[Container.service])) -> TitlesPage:
        pages = []
        for i in range(1, self.main_pages_count+1):
            pages.append(await self.get_titles(page=i, background_tasks=background_tasks, db=db, service=service))
        return self.merge_pages(pages)

    def merge_pages(self, pages: List[TitlesPage]) -> TitlesPage:
        return TitlesPage(titles=[title for page in pages for title in page.titles],
                          total_pages=pages[0].total_pages)

    async def get_genres_data(self, service: CacheService, background_tasks: BackgroundTasks) -> List[ParsedGenre]:
        is_expired = await service.genres_expire_status(parser_id=self.parser_id)
        cached_genres = await service.get_genres(parser_id=self.parser_id)
        if is_expired and cached_genres:
            background_tasks.add_task(self.update_genres, service)
        genres_objs = cached_genres if cached_genres else await self.update_genres(service, raise_error=True)
        return genres_objs

    async def get_genres(self, background_tasks: BackgroundTasks, db: AsyncSession, service: CacheService = Depends(Provide[Container.service])) -> List[Genre]:
        genres_objs = await self.get_genres_data(service=service, background_tasks=background_tasks)
        return await self._prepare_genres(genres=genres_objs, db=db)

    async def get_genre(self, db_genre: GenreModel, page: int, background_tasks: BackgroundTasks, db: AsyncSession, service: CacheService = Depends(Provide[Container.service])):
        genre_id = db_genre.id
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_titles_page = await service.get_genre_titles(parser_id=self.parser_id, genre_id=genre_id, page=page)
        if is_expired and cached_titles_page:
            background_tasks.add_task(self.update_genre, genre_id=genre_id, page=page,
                                      service=service, genre_website_id=db_genre.id_on_website)
        titles_page = cached_titles_page if cached_titles_page else await self.update_genre(genre_id=genre_id, page=page, service=service, raise_error=True, genre_website_id=db_genre.id_on_website)
        return await self._prepare_titles(titles_page=titles_page, db=db, background_tasks=background_tasks)

    async def _get_cached_title(self, title_id: UUID, service: CacheService):
        is_expired = await service.expire_status(parser_id=self.parser_id)
        cached_title = await service.get_title(parser_id=self.parser_id, title_id=title_id)
        return is_expired, cached_title

    async def _update_title_cache(self, id_on_website: str, title_id: UUID, service: CacheService) -> ParsedTitle:
        title_obj = await self.functions.get_title(id_on_website)
        await service.set_title(title_id=title_id, title=title_obj.model_dump(), parser_id=self.parser_id)
        await self.update_expire_status(service=service)
        return title_obj

    async def _prepare_title_shikimori(self, title_obj: ParsedTitle, db_title: TitleModel, db: AsyncSession, service: CacheService, background_tasks: BackgroundTasks) -> tuple[TitleModel, ShikimoriTitle]:
        fail_status = await service.shikimori_fail_status(title_id=db_title.id)
        shikimori_title = None
        if not fail_status:
            try:
                if not db_title.shikimori_fetched:
                    shikimori_title = await Shikimori(service=service).get_title(title_obj)
                    db_title = await TitlesCrud(db).update_shikimori_info(db_title=db_title, shikimori_id=int(shikimori_title.data['id']) if shikimori_title else None)
                elif db_title.shikimori_id:
                    shikimori_title = await Shikimori(service=service).get_shikimori_title(title_id=db_title.shikimori_id, background_tasks=background_tasks)
            except Exception as e:
                logger.error(f'Failed to fetch shikimori info: {e}')
                fail_status = True
                await service.set_shikimori_fail(title_id=db_title.id)
        return db_title, shikimori_title, fail_status

    @abstractmethod
    async def prepare_episode(self, db_episode: Episode, parsed_episode: ParsedEpisode, progress: int, seconds: int, db: AsyncSession, service: CacheService) -> Episode:
        pass

    async def prepare_episodes(self, title: ParsedTitle, title_id: UUID, db: AsyncSession, service: CacheService, current_user: UserModel) -> List[Episode]:
        result = []
        user_id = current_user.id if current_user else None
        episodes = await EpisodesCrud(db).get_episodes_by_title_id(title_id=title_id, user_id=user_id)
        episodes_names = [episode[0].name for episode in episodes]
        for series_item in title.episodes_list:
            progress = 0
            seconds = 0
            try:
                episode_index = episodes_names.index(series_item.name)
                db_episode = episodes[episode_index][0]
                progress = episodes[episode_index][1] or 0
                seconds = episodes[episode_index][2] or 0
            except ValueError:
                db_episode = await EpisodesCrud(db).create_episode(name=series_item.name, title_id=title_id, number=series_item.number)
            result.append(await self.prepare_episode(db_episode=db_episode, parsed_episode=series_item, progress=progress, db=db, service=service, seconds=seconds))
        return result

    async def _prepare_title(self, title_obj: ParsedTitle, db_title: TitleModel, db: AsyncSession, background_tasks: BackgroundTasks, current_user: UserModel, service: CacheService) -> Title:
        if not db_title.image_url and title_obj.image_url:
            db_title = await TitlesCrud(db).update_title(db_title=db_title, title=title_obj)
        elif await self.title_data_changed(title_obj, db_title):
            background_tasks.add_task(
                self.update_title_in_db, title_id=db_title.id, db=db, title_data=title_obj)
        db_title, shikimori_title, fetch_failed = await self._prepare_title_shikimori(title_obj=title_obj, db_title=db_title, db=db, service=service, background_tasks=background_tasks)
        title_db_obj = Title.model_validate(db_title)
        for key, value in title_obj.model_dump().items():
            if hasattr(title_db_obj, key):
                setattr(title_db_obj, key, value)
        title_db_obj.episodes = await self.prepare_episodes(title=title_obj, title_id=db_title.id, db=db, service=service, current_user=current_user)
        title_db_obj.shikimori = shikimori_title
        title_db_obj.shikimori_failed = fetch_failed
        if not title_obj.duration:
            if shikimori_title:
                title_db_obj.duration = f"{shikimori_title.data['duration']} мин." if shikimori_title.data['duration'] else None
            if not title_db_obj.duration and title_db_obj.episodes:
                title_db_obj.duration = f'{title_db_obj.episodes[0].duration // 60} мин.' if title_db_obj.episodes[0].duration else None
        title_db_obj.related = await self._prepare_related_titles(title_id=db_title.id, related_titles=title_obj.related_titles, db=db)
        recommended_titles = await self._prepare_titles(
            titles_page=ParsedTitlesPage(titles=title_obj.recommended_titles, total_pages=0), db=db, background_tasks=background_tasks)
        title_db_obj.recommended = recommended_titles.titles
        title_db_obj.genres = await self._prepare_genres_names(
            genres_names=title_obj.genres_names, db=db, background_tasks=background_tasks)
        title_db_obj.on_other_parsers = await TitlesCrud(db).get_title_on_other_parsers(title=db_title)
        if current_user:
            title_db_obj.liked = await TitlesCrud(db).title_is_favorite(
                title_id=db_title.id, user_id=current_user.id)
            current_episode = await EpisodesCrud(db).get_current_title_episode(
                title_id=db_title.id, user_id=current_user.id)
            title_db_obj.current_episode = next(
                (episode for episode in title_db_obj.episodes if episode.id == current_episode.episode_id), None) if current_episode else None
        return title_db_obj

    async def update_titles(self, page: int, service: CacheService, raise_error: bool = False) -> List[ParsedTitleShort]:
        try:
            titles_page = await self.functions.get_titles(page)
            await self._cache_titles(titles_page=titles_page, page=page, service=service)
            return titles_page
        except HTTPException as e:
            if raise_error:
                raise e
        except Exception as e:
            logger.error(f'Failed to fetch titles: {e}')
            if raise_error:
                raise HTTPException(
                    status_code=500, detail='Failed to fetch titles.')

    async def _cache_titles(self, titles_page: ParsedTitlesPage, page: int, service: CacheService):
        await service.set_titles(titles_page=titles_page.model_dump(), page=page, parser_id=self.parser_id)
        await self.update_expire_status(service=service)

    async def update_title_in_db(self, title_id: UUID, db: AsyncSession, title_data: ParsedTitle = None, raise_error: bool = False) -> Title:
        db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
        await TitlesCrud(db).update_title(db_title=db_title, title=title_data)

    async def update_expire_status(self, service: CacheService = Depends(Provide[Container.service])):
        expired = await service.expire_status(parser_id=self.parser_id)
        if expired:
            await service.update_expire_status(parser_id=self.parser_id, hours=self.titles_cache_period)

    async def update_title(self, id_on_website: str, title_id: UUID, service: CacheService, db: AsyncSession, raise_error: bool = False) -> ParsedTitle:
        try:
            title: ParsedTitleShort = await self.functions.get_title(id_on_website)
            if title.related_titles:
                related_titles = await self._prepare_related_titles(title_id=title_id, related_titles=title.related_titles, db=db)
                title.related_titles = related_titles
            await service.set_title(title_id=title_id, title=title.model_dump(), parser_id=self.parser_id)
            await self.update_expire_status(service=service)
            return title
        except HTTPException as e:
            if raise_error:
                raise e
        except Exception as e:
            logger.error(f'Failed to fetch title: {e}')
            if raise_error:
                raise HTTPException(
                    status_code=500, detail='Failed to fetch title.')

    async def update_genres(self, service: CacheService, raise_error: bool = False) -> List[ParsedGenre]:
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
        except HTTPException as e:
            if raise_error:
                raise e
        except Exception as e:
            logger.error(f'Failed to fetch genres: {e}')
            if raise_error:
                raise HTTPException(
                    status_code=500, detail='Failed to fetch genres.')

    async def update_genre(self, genre_website_id: str, genre_id: UUID, page: int, service: CacheService, raise_error: bool = False) -> List[ParsedTitleShort]:
        try:
            titles_page = await self.functions.get_genre(genre_website_id, page)
            await service.set_genre_titles(parser_id=self.parser_id, genre_id=genre_id, page=page, titles_page=titles_page.model_dump())
            return titles_page
        except HTTPException as e:
            if raise_error:
                raise e
        except Exception as e:
            logger.error(f'Failed to fetch genre titles: {e}')
            if raise_error:
                raise HTTPException(
                    status_code=500, detail='Failed to fetch genre titles.')

    async def title_data_changed(self, title_data: ParsedTitleShort, db_title: Title) -> bool:
        for key, value in title_data.model_dump().items():
            if hasattr(db_title, key) and getattr(db_title, key) != value:
                return True
        return False

    async def _prepare_related_titles(self, title_id: UUID, related_titles: List[LinkParsedTitle], db: AsyncSession) -> List[TitleLink]:
        related_link = await TitlesCrud(db).get_related_link_by_title_id(title_id=title_id)
        if not related_link:
            related_link = await TitlesCrud(db).create_related_link()
        related_titles_objs = []
        for related_title in related_titles:
            existing_title = await TitlesCrud(db).get_title_by_website_id(website_id=related_title.id_on_website, parser_id=self.parser_id)
            if not existing_title:
                existing_title = await TitlesCrud(db).create_title(related_title, self.parser_id)
            if existing_title.id == title_id:
                continue
            related = await TitlesCrud(db).get_related_title(title_id=existing_title.id, link_id=related_link.id)
            if not related:
                related = await TitlesCrud(db).create_related_title(title_id=existing_title.id, link_id=related_link.id)
            related_titles_objs.append(
                TitleLink.model_validate(existing_title))
        return related_titles_objs

    async def _prepare_titles(self, titles_page: ParsedTitlesPage, db: AsyncSession, background_tasks: BackgroundTasks) -> TitlesPage:
        db_titles = []
        existing_titles = await TitlesCrud(db).get_titles_by_website_ids(website_ids=[title.id_on_website for title in titles_page.titles])
        existing_ids_set = {title.id_on_website for title in existing_titles}
        for parsed_title in titles_page.titles:
            if parsed_title.id_on_website not in existing_ids_set:
                title = await TitlesCrud(db).create_title(parsed_title, self.parser_id)
            else:
                title = next(
                    title for title in existing_titles if title.id_on_website == parsed_title.id_on_website)
                if await self.title_data_changed(parsed_title, title):
                    background_tasks.add_task(
                        self.update_title_in_db, title_id=title.id, db=db, title_data=parsed_title)
            title_obj = TitleShort.model_validate(title)
            title_obj.additional_info = parsed_title.additional_info
            title_obj.en_name = parsed_title.en_name
            db_titles.append(title_obj)
        return TitlesPage(titles=db_titles, total_pages=titles_page.total_pages)

    async def _prepare_genres_names(self, genres_names: List[str], db: AsyncSession, background_tasks: BackgroundTasks, service: CacheService = Depends(Provide[Container.service])) -> List[Genre]:
        all_genres = await self.get_genres_data(service=service, background_tasks=background_tasks)
        db_genres = []
        for genre_name in genres_names:
            genre = None
            for parsed_genre in all_genres:
                if parsed_genre.name.lower() == genre_name:
                    genre = parsed_genre
                    break
            if not genre:
                continue
            db_genre = await GenresCrud(db).get_genre_by_website_id(website_id=genre.id_on_website)
            if not db_genre:
                db_genre = await GenresCrud(db).create_genre(genre=genre, parser_id=self.parser_id)
            db_genres.append(db_genre)
        return db_genres

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
                if not genre:
                    continue
            db_genres.append(genre)
        return db_genres

    async def parser_expired(self, service: CacheService = Depends(Provide[Container.service])) -> bool:
        return await service.expire_status(parser_id=self.parser_id)

    async def get_service(self, service: CacheService = Depends(Provide[Container.service])) -> CacheService:
        return service

    async def get_parser_expires_in(self, service: CacheService = Depends(Provide[Container.service])) -> int:
        return await service.get_expires_in(parser_id=self.parser_id)


container = Container()
container.config.redis_host.from_value(settings.REDIS_HOST)
container.config.redis_password.from_value(settings.REDIS_PASSWORD)
container.wire(modules=[__name__])
