from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from src.crud.base import BaseCRUD
from src.models.parsers import Genre
from src.schemas.parsers import ParsedGenre


class GenresCrud(BaseCRUD):

    async def get_genre_by_website_id(self, website_id: str) -> Genre:
        query = select(Genre).where(Genre.id_on_website == website_id)
        return (await self.db.execute(query)).scalar()

    async def create_genre(self, genre: ParsedGenre, parser_id: str) -> Genre:
        genre = Genre(
            id_on_website=genre.id_on_website,
            parser_id=parser_id,
            name=genre.name,
        )
        return await self.create(genre)

    async def get_genres_by_website_ids(self, website_ids: list[str]) -> list[Genre]:
        query = select(Genre).where(Genre.id_on_website.in_(website_ids))
        return (await self.db.execute(query)).scalars().all()

    async def get_genre_by_id(self, genre_id: UUID) -> Genre:
        query = select(Genre).where(Genre.id == genre_id)
        return (await self.db.execute(query)).scalar()

    async def get_genres(self, parser_id: str) -> list[Genre]:
        query = select(Genre).where(Genre.parser_id == parser_id)
        return (await self.db.execute(query)).scalars().all()

    async def get_unique_genres(self) -> list[Genre]:
        query = (
            select(
                Genre.name,
                func.array_agg(func.json_build_object(
                    'id', Genre.id, 'parser_id', Genre.parser_id)).label('variants')
            )
            .group_by(Genre.name)
        )
        return (await self.db.execute(query)).all()
