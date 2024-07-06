from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from src.crud.episodes_crud import EpisodesCrud
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import Episode, ParsedTitle, TitleEpisode
from src.parsers import parsers_dict
from src.users_controller import current_active_user
api_router = APIRouter(prefix="/episodes", tags=["episodes"])


@api_router.get("", response_model=list[TitleEpisode])
async def get_episodes(page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    episodes_info = await EpisodesCrud(db).get_current_episodes(user_id=current_user.id, page=page)
    episodes = []
    for episode in episodes_info:
        parser = parsers_dict[episode[2]]
        service = await parser.get_service()
        title_data: ParsedTitle = await parser.get_title_data(
            db_title=episode[0].title,
            service=service,
        )
        parsed_episode = next(
            (episode for episode in title_data.episodes_list if episode.number == episode.number), None)

        prepared_episode: Episode = await parser.prepare_episode(
            db_episode=episode[0],
            progress=episode[1],
            service=service,
            db=db,
            parsed_episode=parsed_episode)
        prepared_episode.image_url = title_data.image_url
        episodes.append(
            TitleEpisode(
                **prepared_episode.model_dump(),
                title_id=episode[0].title_id,
            )
        )
    return episodes


@api_router.post("/{episode_id}/progress", response_model=None, status_code=204)
async def set_episode_progress(episode_id: UUID, progress: int = Query(..., ge=0, le=100), db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_episode = await EpisodesCrud(db).get_by_id(episode_id)
    if not db_episode:
        raise HTTPException(status_code=404, detail="Episode not found.")
    current_episode = await EpisodesCrud(db).get_current_title_episode(title_id=db_episode.title_id, user_id=current_user.id)
    if current_episode:
        await EpisodesCrud(db).delete(current_episode)
    await EpisodesCrud(db).set_current_episode(episode_id=db_episode.id, user_id=current_user.id)
    await EpisodesCrud(db).set_episode_progress(episode_id=db_episode.id, user_id=current_user.id, progress=progress)


@api_router.delete("/{episode_id}/progress", response_model=None, status_code=204)
async def unset_episode_progress(episode_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_episode = await EpisodesCrud(db).get_by_id(episode_id)
    if not db_episode:
        raise HTTPException(status_code=404, detail="Episode not found.")
    await EpisodesCrud(db).unset_current_title_episode(title_id=db_episode.title_id, user_id=current_user.id)
