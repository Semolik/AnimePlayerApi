from typing import Literal
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from src.crud.titles_crud import TitlesCrud
from src.crud.genres_crud import GenresCrud
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import Genre, Title, TitleShort
from src.parsers import animevost

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


@api_router.get("/titles/{title_id}", response_model=Title)
async def get_title(background_tasks: BackgroundTasks, title_id: UUID, db: AsyncSession = Depends(get_async_session)):
    db_title = await TitlesCrud(db).get_title_by_id(title_id=title_id)
    if not db_title:
        raise HTTPException(status_code=404, detail="Title not found.")
    parser = parsers_dict[db_title.parser_id]
    return await parser.get_title(
        db_title=db_title,
        db=db,
        background_tasks=background_tasks
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
