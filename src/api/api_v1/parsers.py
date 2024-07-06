from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import Genre, ParserInfo,  TitlesPage
from src.parsers import parsers, parsers_dict


api_router = APIRouter(prefix="/parsers", tags=["parsers"])
ParserId = Literal[tuple([parser.parser_id for parser in parsers])]  # nopep8 # type: ignore

for parser in parsers:
    custom_router = parser.get_custom_router()
    if custom_router:
        api_router.include_router(
            custom_router, prefix=f"/{parser.parser_id}", tags=[parser.name])


@api_router.get("", response_model=list[ParserInfo])
async def get_parsers(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_async_session)):
    parsers_info = []
    for parser in parsers:
        last_titles = await parsers_dict[parser.parser_id].get_titles(
            page=1,
            background_tasks=background_tasks,
            db=db
        )
        parsers_info.append(ParserInfo(id=parser.parser_id,
                            name=parser.name, last_titles=last_titles))
    return parsers_info


@api_router.get("/{parser_id}/titles", response_model=TitlesPage)
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
