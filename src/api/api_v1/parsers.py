from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import Genre, MainPage, ParserInfo,  TitlesPage
from src.parsers import parsers, parsers_dict


api_router = APIRouter(prefix="/parsers", tags=["parsers"])
ParserId = Literal[tuple([parser.parser_id for parser in parsers])]  # nopep8 # type: ignore

for parser in parsers:
    custom_router = parser.get_custom_router()
    if custom_router:
        api_router.include_router(
            custom_router, prefix=f"/{parser.parser_id}", tags=[parser.name])


@api_router.get("", response_model=list[ParserInfo])
async def get_parsers():
    parsers_info = []
    for parser in parsers:
        parsers_info.append(ParserInfo(
            id=parser.parser_id, name=parser.name, pages_on_main=parser.main_pages_count))
    return parsers_info


@api_router.get("/{parser_id}/titles", response_model=TitlesPage)
async def get_titles(parser_id: ParserId, background_tasks: BackgroundTasks, page: int = Query(1, ge=1), db: AsyncSession = Depends(get_async_session)):  # type: ignore
    parser = parsers_dict[parser_id]
    return await parser.get_titles(
        page=page,
        background_tasks=background_tasks,
        db=db
    )


@api_router.get("/{parser_id}/titles/main", response_model=MainPage)
async def get_main_titles(parser_id: ParserId, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_async_session)):  # type: ignore
    parser = parsers_dict[parser_id]
    page = await parser.get_main_titles(background_tasks=background_tasks, db=db)
    page_obj = MainPage.model_validate(page, from_attributes=True)
    page_obj.pages_on_main = parser.main_pages_count
    return page_obj


@api_router.get("/{parser_id}/genres", response_model=list[Genre])
async def get_genres(parser_id: ParserId, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_async_session)):  # type: ignore
    parser = parsers_dict[parser_id]
    return await parser.get_genres(background_tasks=background_tasks, db=db)
