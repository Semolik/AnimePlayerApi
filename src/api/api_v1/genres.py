from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from src.crud.genres_crud import GenresCrud
from src.db.session import get_async_session, AsyncSession
from src.schemas.parsers import TitlesPage
from src.parsers import parsers_dict
api_router = APIRouter(prefix="/genres", tags=["genres"])


@api_router.get("/genres/{genre_id}", response_model=TitlesPage)
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
