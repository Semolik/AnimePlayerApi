from typing import Literal
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import Genre, Title
from src.parsers import animevost

api_router = APIRouter(prefix="/parsers")

parsers = [animevost.parser]
parsers_dict = {parser.parser_id: parser for parser in parsers}
ParserId = Literal[tuple([parser.parser_id for parser in parsers])] # type: ignore


@api_router.get("/{parser_id}/titles", response_model=list[Title])
async def get_titles(parser_id: ParserId, background_tasks: BackgroundTasks, page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session)):
    parser = parsers_dict[parser_id]
    return await parser.get_titles(
        page=page,
        background_tasks=background_tasks,
        db=db
    )

@api_router.get("/{parser_id}/titles/{title_id}", response_model=Title)
async def get_title(parser_id: ParserId, background_tasks: BackgroundTasks, title_id: UUID, db: AsyncSession = Depends(get_async_session)):
    parser = parsers_dict[parser_id]
    return await parser.get_title(
        title_id=title_id,
        db=db,
        background_tasks=background_tasks
    )

@api_router.get("/{parser_id}/genres", response_model=list[Genre])
async def get_genres(parser_id: ParserId, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_async_session)):
    parser = parsers_dict[parser_id]
    return await parser.get_genres(background_tasks=background_tasks,db=db)

@api_router.get("/{parser_id}/genres/{genre_id}", response_model=list[Title])
async def get_genre(parser_id: ParserId, background_tasks: BackgroundTasks, genre_id: UUID, page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session)):
    parser = parsers_dict[parser_id]
    return await parser.get_genre(
        genre_id=genre_id,
        page=page,
        background_tasks=background_tasks,
        db=db
    )