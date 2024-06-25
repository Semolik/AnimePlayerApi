from typing import Literal
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from src.crud.titles_crud import TitlesCrud
from src.crud.genres_crud import GenresCrud
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import FavoriteTitle, Genre, Title, TitleShort
from src.parsers import animevost
from src.users_controller import optional_current_user, current_active_user
api_router = APIRouter(prefix="/parsers")

parsers = [animevost.parser]
parsers_dict = {parser.parser_id: parser for parser in parsers}

ParserId = Literal[tuple([parser.parser_id for parser in parsers])]  # nopep8 # type: ignore


@api_router.get("/{parser_id}/titles", response_model=list[TitleShort])
async def get_titles(parser_id: ParserId, background_tasks: BackgroundTasks, page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session)):
    parser = parsers_dict[parser_id]
    return await parser.get_titles(
        page=page,
        background_tasks=background_tasks,
        db=db
    )


@api_router.get("/{parser_id}/genres", response_model=list[Genre])
async def get_genres(parser_id: ParserId, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_async_session)):
    parser = parsers_dict[parser_id]
    return await parser.get_genres(background_tasks=background_tasks, db=db)


@api_router.get("/titles/favorites", response_model=list[FavoriteTitle])
async def get_favorite_titles(page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    return await TitlesCrud(db).get_favorite_titles_by_user_id(page=page, user_id=current_user.id)


@api_router.post("/titles/favorites/{title_id}", response_model=None, status_code=204)
async def favorite_title(title_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    favorite = await TitlesCrud(db).title_is_favorite(title_id=title_id, user_id=current_user.id)
    if not favorite:
        await TitlesCrud(db).create_favorite_title(title_id=title_id, user_id=current_user.id)


@api_router.delete("/titles/favorites/{title_id}", response_model=None, status_code=204)
async def unfavorite_title(title_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_active_user)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    favorite = await TitlesCrud(db).get_favorite_title(title_id=title_id, user_id=current_user.id)
    if favorite:
        await TitlesCrud(db).delete(favorite)


@api_router.get("/titles/{title_id}", response_model=Title)
async def get_title(background_tasks: BackgroundTasks, title_id: UUID, db: AsyncSession = Depends(get_async_session), current_user=Depends(optional_current_user)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    parser = parsers_dict[db_title.parser_id]
    return await parser.get_title(
        db_title=db_title,
        db=db,
        background_tasks=background_tasks,
        current_user=current_user
    )


@api_router.get("/genres/{genre_id}", response_model=list[TitleShort])
async def get_genre(background_tasks: BackgroundTasks, genre_id: UUID, page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session)):
    existing_genre = await GenresCrud(db).get_genre_by_id(genre_id=genre_id)
    if not existing_genre:
        raise HTTPException(status_code=404, detail="Genre not found.")
    parser = parsers_dict[existing_genre.parser_id]
    return await parser.get_genre(
        db_genre=existing_genre,
        page=page,
        background_tasks=background_tasks,
        db=db
    )
