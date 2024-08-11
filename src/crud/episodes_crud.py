from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from src.crud.base import BaseCRUD
from src.models.parsers import Episode, EpisodeProgress, CurrentEpisode, Title


class EpisodesCrud(BaseCRUD):

    async def get_episode_by_number(self, title_id: UUID, number: int, user_id: UUID) -> tuple[Episode, int | None]:
        query = select(Episode, EpisodeProgress.progress).join(EpisodeProgress, isouter=True).where(
            Episode.title_id == title_id, Episode.number == number, EpisodeProgress.user_id == user_id)
        return (await self.db.execute(query)).scalar()

    async def get_episodes_by_title_id(self, title_id: UUID, user_id: UUID) -> list[tuple[Episode, int | None]]:
        query = select(Episode, EpisodeProgress.progress, EpisodeProgress.seconds).join(EpisodeProgress, isouter=True).where(
            Episode.title_id == title_id, EpisodeProgress.user_id == user_id).order_by(Episode.number)
        return (await self.db.execute(query)).all()

    async def create_episode(self, title_id: UUID, number: int, name: str):
        episode = Episode(title_id=title_id, number=number, name=name)
        return await self.create(episode)

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
            .options(selectinload(Episode.title))
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
        query = select(Episode).where(Episode.id == episode_id)
        return (await self.db.execute(query)).scalar()

    async def set_current_episode(self, episode_id: UUID, user_id: UUID):
        current_episode = CurrentEpisode(
            episode_id=episode_id, user_id=user_id)
        return await self.create(current_episode)

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
