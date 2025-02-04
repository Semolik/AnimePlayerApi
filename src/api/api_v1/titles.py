from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from src.crud.titles_crud import TitlesCrud
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import SearchTitle, TitleEpisodes, FavoriteTitle, Title
from src.parsers import parsers_dict
from src.users_controller import optional_current_user, current_active_user, current_superuser
from src.worker import get_episodes_duration
from src.utils.titles import TitlesService
api_router = APIRouter(prefix="/titles", tags=["titles"])


@api_router.get("/favorites", response_model=list[FavoriteTitle])
async def get_favorite_titles(page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    return await TitlesCrud(db).get_favorite_titles_by_user_id(page=page, user_id=current_user.id)


@api_router.post("/favorites/{title_id}", response_model=None, status_code=204)
async def favorite_title(title_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    favorite = await TitlesCrud(db).title_is_favorite(title_id=title_id, user_id=current_user.id)
    if not favorite:
        await TitlesCrud(db).create_favorite_title(title_id=title_id, user_id=current_user.id)


@api_router.delete("/favorites/{title_id}", response_model=None, status_code=204)
async def unfavorite_title(title_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    favorite = await TitlesCrud(db).get_favorite_title(title_id=title_id, user_id=current_user.id)
    if favorite:
        await TitlesCrud(db).delete(favorite)


@api_router.get("/search", response_model=list[SearchTitle])
async def search_titles(query: str, db: AsyncSession = Depends(get_async_session)):
    return await TitlesCrud(db).search_titles(query=query)


@api_router.get("/stats", response_model=dict)
async def get_titles_stats(db: AsyncSession = Depends(get_async_session), current_user=Depends(current_superuser)):
    return {
        'count': await TitlesCrud(db).get_titles_count()
    }


@api_router.get("/popular", response_model=list[SearchTitle])
async def get_popular_titles(db: AsyncSession = Depends(get_async_session)):
    return await TitlesService(db).get_popular_titles()


@api_router.get("/{title_id}", response_model=Title)
async def get_title(background_tasks: BackgroundTasks, title_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(optional_current_user)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    parser = parsers_dict[db_title.parser_id]
    title_obj = await parser.get_title(
        db_title=db_title,
        db=db,
        background_tasks=background_tasks,
        current_user=current_user
    )
    episodes = title_obj.episodes
    has_no_time = any(not episode.duration for episode in episodes)
    if has_no_time:
        get_episodes_duration.apply_async(
            args=[[episode.model_dump() for episode in episodes]]
        )
    return title_obj


@api_router.get("/{title_id}/episodes", response_model=TitleEpisodes)
async def get_episodes(title_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(optional_current_user)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    parser = parsers_dict[db_title.parser_id]
    episodes = await parser.get_title_episodes(
        db_title=db_title,
        db=db,
        current_user=current_user
    )
    return TitleEpisodes(episodes=episodes, title=db_title)
