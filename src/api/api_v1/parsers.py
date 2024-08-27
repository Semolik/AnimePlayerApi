
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from src.crud.genres_crud import GenresCrud
from src.crud.titles_crud import TitlesCrud
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import Genre, MainPage, ParserInfo,  TitlesPage
from src.parsers import parsers, parsers_dict, ParserId
from src.worker import prepare_all_parser_titles_wrapper
from src.users_controller import current_superuser


api_router = APIRouter(prefix="/parsers", tags=["parsers"])

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


@api_router.get("/{parser_id}/resolve-old-id/{title_id}", response_model=UUID)
async def resolve_old_id(parser_id: ParserId, title_id: int, db: AsyncSession = Depends(get_async_session)):
    db_title = await TitlesCrud(db).get_title_by_website_id(website_id=title_id, parser_id=parser_id)
    if not db_title:
        title_obj = await parsers_dict[parser_id].functions.get_title(str(title_id))
        if not title_obj:
            raise HTTPException(status_code=404, detail="Title not found.")
        db_title = await TitlesCrud(db).create_title(title_obj, parser_id)
    return db_title.id


@api_router.get("/{parser_id}/resolve-old-genre", response_model=UUID)
async def resolve_old_id(parser_id: ParserId, genre_name: str, db: AsyncSession = Depends(get_async_session)):
    db_genre = await GenresCrud(db).get_genre_by_website_id(website_id=genre_name, parser_id=parser_id)
    if not db_genre:
        raise HTTPException(status_code=404, detail="Genre not found.")
    return db_genre.id


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


@api_router.post("/{parser_id}/prepare-all-titles")
async def prepare_all_titles(parser_id: ParserId, db: AsyncSession = Depends(get_async_session), current_user=Depends(current_superuser)):
    prepare_all_parser_titles_wrapper.apply_async((parser_id, ))
    return {"message": "Preparing titles started."}
