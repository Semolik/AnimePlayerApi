from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from src.crud.episodes_crud import EpisodesCrud
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import Episode, HistoryDay, ParsedLink, TitleEpisode, TitleShort
from src.models.parsers import Episode as EpisodeModel
from src.models.users import User as UserModel
from src.parsers import parsers_dict
from src.users_controller import current_active_user
api_router = APIRouter(prefix="/episodes", tags=["episodes"])


@api_router.get("", response_model=list[TitleEpisode])
async def get_episodes(page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    episodes_info = await EpisodesCrud(db).get_current_episodes(user_id=current_user.id, page=page)
    episodes = []
    for episode in episodes_info:
        db_episode = episode[0]
        progress = episode[1] if episode[1] else 0
        seconds = episode[2] if episode[2] else 0
        episodes.append(
            await get_episode_info(db_episode=db_episode, db=db, current_user=current_user, episode_progress=progress, episode_seconds=seconds)
        )
    return episodes


async def get_episode_info(db_episode: EpisodeModel, db, current_user: UserModel, episode_progress: int, episode_seconds: int):
    if len(db_episode.links) == 0:
        prepared_episode = await prepare_episode_without_links(db_episode=db_episode, db=db, current_user=current_user)
        prepared_episode.progress = episode_progress
        prepared_episode.seconds = episode_seconds
        return TitleEpisode(
            **prepared_episode.model_dump(),
            title_id=db_episode.title_id,
            title=TitleShort.model_validate(
                db_episode.title, from_attributes=True),
        )
    else:
        prepared_episode = TitleEpisode.model_validate(
            db_episode, from_attributes=True)
        prepared_episode.progress = episode_progress
        prepared_episode.seconds = episode_seconds
        return prepared_episode


async def prepare_episode_without_links(db_episode: EpisodeModel, db, current_user: UserModel):
    parser = parsers_dict[db_episode.title.parser_id]
    service = await parser.get_service()
    title_data = await parser.get_title_data(
        db_title=db_episode.title,
        service=service,
    )
    title_episodes = await parser.prepare_episodes(
        title=title_data,
        title_id=db_episode.title_id,
        db=db,
        service=service,
        current_user=current_user
    )
    prepared_episode = next(
        (episode for episode in title_episodes if episode.number == db_episode.number), None)
    return prepared_episode


@api_router.get("/history", response_model=list[HistoryDay])
async def get_history(page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    return await EpisodesCrud(db).get_history(user_id=current_user.id, page=page)


@ api_router.get("/{episode_id}/next", response_model=TitleEpisode | None)
async def get_next_episode(episode_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_episode = await EpisodesCrud(db).get_by_id(episode_id)
    if not db_episode:
        raise HTTPException(status_code=404, detail="Episode not found.")
    next_episode = await EpisodesCrud(db).get_next_episode(
        title_id=db_episode.title_id, number=db_episode.number)
    if not next_episode:
        return None
    parser = parsers_dict[next_episode.title.parser_id]
    service = await parser.get_service()
    title_data = await parser.get_title_data(
        db_title=next_episode.title,
        service=service,
    )
    parsed_episode = next(
        (episode for episode in title_data.episodes_list if episode.number == next_episode.number), None)
    episode_progress = await EpisodesCrud(db).get_episode_progress(
        episode_id=next_episode.id, user_id=current_user.id)
    prepared_episode: Episode = await parser.prepare_episode(
        db_episode=next_episode,
        service=service,
        db=db,
        parsed_episode=parsed_episode,
        progress=episode_progress.progress if episode_progress else 0,
        seconds=episode_progress.seconds if episode_progress else 0
    )
    prepared_episode.image_url = title_data.image_url
    return TitleEpisode(
        **prepared_episode.model_dump(),
        title_id=next_episode.title_id,
        title=TitleShort.model_validate(
            next_episode.title, from_attributes=True),
    )


@ api_router.post("/{episode_id}/progress", response_model=None, status_code=204)
async def set_episode_progress(episode_id: UUID, progress: int = Query(..., ge=0, le=100), time: int = Query(..., ge=0), db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_episode = await EpisodesCrud(db).get_by_id(episode_id)
    if not db_episode:
        raise HTTPException(status_code=404, detail="Episode not found.")
    current_episode = await EpisodesCrud(db).get_current_title_episode(title_id=db_episode.title_id, user_id=current_user.id)
    if current_episode:
        await EpisodesCrud(db).update_current_episode(current_episode=current_episode, episode_id=db_episode.id)
    else:
        await EpisodesCrud(db).create_current_episode(episode_id=db_episode.id, user_id=current_user.id)
    if db_episode.duration and time > db_episode.duration:
        raise HTTPException(
            status_code=400, detail="Time can't be more than episode duration.")
    if progress > 95:
        next_episode = await EpisodesCrud(db).get_next_episode(
            title_id=db_episode.title_id, number=db_episode.number)
        if next_episode:
            await EpisodesCrud(db).update_current_episode(
                current_episode=current_episode, episode_id=next_episode.id)
    else:
        await EpisodesCrud(db).set_episode_progress(episode_id=db_episode.id, user_id=current_user.id, progress=progress, seconds=time)


@ api_router.delete("/{episode_id}/progress", response_model=None, status_code=204)
async def unset_episode_progress(episode_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_episode = await EpisodesCrud(db).get_by_id(episode_id)
    if not db_episode:
        raise HTTPException(status_code=404, detail="Episode not found.")
    await EpisodesCrud(db).unset_current_title_episode(title_id=db_episode.title_id, user_id=current_user.id)
