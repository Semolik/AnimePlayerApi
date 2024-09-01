from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from src.schemas.parsers import HistoryDay, TitleEpisode
from src.crud.base import BaseCRUD
from src.models.parsers import Episode, EpisodeProgress, CurrentEpisode, EpisodeSource, Title


class EpisodesCrud(BaseCRUD):

    async def get_episode_by_number(self, title_id: UUID, number: int, user_id: UUID) -> tuple[Episode, int | None]:
        query = select(Episode, EpisodeProgress.progress).join(EpisodeProgress, isouter=True).where(
            Episode.title_id == title_id, Episode.number == number, EpisodeProgress.user_id == user_id)
        return (await self.db.execute(query)).scalar()

    async def get_source(self, episode_id: UUID, name: str) -> EpisodeSource:
        query = select(EpisodeSource).where(
            EpisodeSource.episode_id == episode_id, EpisodeSource.name == name)
        return (await self.db.execute(query)).scalar()

    async def create_source(self, episode_id: UUID, link: str, name: str, quality: str | None, is_m3u8: bool) -> EpisodeSource:
        source = EpisodeSource(
            episode_id=episode_id, link=link, name=name, quality=quality, is_m3u8=is_m3u8)
        return await self.create(source)

    async def update_source(self, source: EpisodeSource, link: str) -> EpisodeSource:
        source.link = link
        return await self.update(source)

    async def get_episodes_by_title_id(self, title_id: UUID, user_id: UUID) -> list[tuple[Episode, int | None]]:
        query = select(Episode, EpisodeProgress.progress, EpisodeProgress.seconds).join(EpisodeProgress, isouter=True).where(
            Episode.title_id == title_id, EpisodeProgress.user_id == user_id).order_by(Episode.number)
        return (await self.db.execute(query)).all()

    async def get_next_episode(self, title_id: UUID, number: int) -> Episode:
        query = select(Episode).where(Episode.title_id ==
                                      title_id, Episode.number == number + 1)
        return (await self.db.execute(query)).scalar()

    async def get_last_watched_episode(self, title_id: UUID, user_id: UUID) -> Episode:
        query = select(Episode).join(EpisodeProgress, Episode.id == EpisodeProgress.episode_id).where(
            Episode.title_id == title_id, EpisodeProgress.user_id == user_id).order_by(EpisodeProgress.updated_at.desc())
        return (await self.db.execute(query)).scalar()

    async def create_episode(self, title_id: UUID, number: int, name: str, image_url: str | None = None) -> Episode:
        episode = Episode(title_id=title_id, number=number,
                          name=name, image_url=image_url)
        return await self.create(episode)

    async def update_episode(self, episode: Episode, name: str, image_url: str | None = None) -> Episode:
        episode.name = name
        episode.image_url = image_url
        return await self.update(episode)

    async def get_current_episodes(self, user_id: UUID, page: int = 1, per_page: int = 10) -> list[tuple[Episode, int | None, int | None, str]]:
        end = page * per_page
        start = end - per_page

        subquery = (
            select(
                Episode.title_id,
                func.max(Episode.number).label('max_number')
            )
            .join(CurrentEpisode, (CurrentEpisode.episode_id == Episode.id) & (CurrentEpisode.user_id == user_id))
            .group_by(Episode.title_id)
            .subquery()
        )

        query = (
            select(
                Episode,
                EpisodeProgress.progress,
                EpisodeProgress.seconds,
                Title.parser_id
            )
            .join(subquery, (Episode.title_id == subquery.c.title_id) & (Episode.number == subquery.c.max_number))
            .join(EpisodeProgress, EpisodeProgress.episode_id == Episode.id)
            .join(Title, Title.id == Episode.title_id)
            .order_by(EpisodeProgress.updated_at.desc())
            .options(selectinload(Episode.title), selectinload(Episode.links))
        )

        query = query.slice(start, end)
        query = await self.db.execute(query)
        return query.all()

    async def update_episode_duration(self, episode: Episode, duration: int | None) -> Episode:
        episode.duration = duration
        episode.duration_fetched = True
        return await self.update(episode)

    async def get_current_title_episode(self, title_id: UUID, user_id: UUID) -> CurrentEpisode:
        query = select(CurrentEpisode).join(Episode, Episode.id == CurrentEpisode.episode_id).join(
            Title, Title.id == Episode.title_id).where(Title.id == title_id, CurrentEpisode.user_id == user_id)
        return (await self.db.execute(query)).scalar()

    async def unset_current_title_episode(self, title_id: UUID, user_id: UUID):
        query = select(CurrentEpisode).join(Episode, Episode.id == CurrentEpisode.episode_id).where(
            Episode.title_id == title_id, CurrentEpisode.user_id == user_id)
        current_episode = (await self.db.execute(query)).scalar()
        if current_episode:
            return await self.delete(current_episode)

    async def get_by_id(self, episode_id: int) -> Episode:
        query = select(Episode).where(
            Episode.id == episode_id).options(selectinload(Episode.title))
        return (await self.db.execute(query)).scalar()

    async def create_current_episode(self, episode_id: UUID, user_id: UUID):
        current_episode = CurrentEpisode(
            episode_id=episode_id, user_id=user_id)
        return await self.create(current_episode)

    async def update_current_episode(self, current_episode: CurrentEpisode, episode_id: UUID):
        current_episode.episode_id = episode_id
        return await self.update(current_episode)

    async def get_episode_progress(self, episode_id: UUID, user_id: UUID) -> EpisodeProgress:
        query = select(EpisodeProgress).where(
            EpisodeProgress.episode_id == episode_id, EpisodeProgress.user_id == user_id)
        return (await self.db.execute(query)).scalar()

    async def set_episode_progress(self, episode_id: UUID, user_id: UUID, progress: int, seconds: int):
        episode_progress = await self.get_episode_progress(episode_id, user_id)
        if episode_progress:
            episode_progress.progress = progress
            episode_progress.seconds = seconds
            return await self.update(episode_progress)
        episode_progress = EpisodeProgress(
            episode_id=episode_id, user_id=user_id, progress=progress, seconds=seconds)
        return await self.create(episode_progress)

    async def get_history(self, user_id: UUID, page: int = 1, per_page: int = 10) -> list[HistoryDay]:
        end = page * per_page
        start = end - per_page

        query = (
            select(
                EpisodeProgress,
                Episode,
            )
            .join(Episode, Episode.id == EpisodeProgress.episode_id)
            .where(EpisodeProgress.user_id == user_id)
            .order_by(EpisodeProgress.updated_at.desc())
            .options(selectinload(Episode.title), selectinload(Episode.links))
            .slice(start, end)
        )
        query = await self.db.execute(query)
        episodes = query.all()
        history = {}
        for episode in episodes:
            date = episode[0].updated_at.date()
            if date not in history:
                history[date] = []
            if not episode[1].image_url:
                episode[1].image_url = episode[1].title.image_url
            episode = TitleEpisode.model_validate(
                episode[1], from_attributes=True)
            episode.progress = episode[0].progress
            episode.seconds = episode[0].seconds
            history[date].append(episode)
        return [HistoryDay(date=date, episodes=reversed(episodes)) for date, episodes in history.items()]
