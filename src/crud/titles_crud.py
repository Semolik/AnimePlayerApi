from sqlalchemy import select
from src.crud.base import BaseCRUD
from src.models.parsers import Title
from src.schemas.parsers import ParsedTitleShort, ParsedTitle

class TitlesCrud(BaseCRUD):

    async def get_titles_by_website_ids(self, website_ids: list[str]) -> list[Title]:
        query = select(Title).where(Title.id_on_website.in_(website_ids))
        return (await self.db.execute(query)).scalars().all()
    
    async def create_title(self, title: ParsedTitleShort, parser_id: str) -> Title:
        title = Title(
            id_on_website=title.id_on_website,
            parser_id=parser_id,
            name=title.name,
            page_fetched=False,
            image_url=title.image_url,
        )
        return await self.create(title)
    
    async def create_full_title(self, title: ParsedTitle, parser_id: str) -> Title:
        title = Title(
            id_on_website=title.id_on_website,
            parser_id=parser_id,
            name=title.name,
            page_fetched=True,
            image_url=title.image_url,
            description=title.description,
        )
        return await self.create(title)
    
    async def get_title_by_website_id(self, website_id: str) -> Title:
        query = select(Title).where(Title.id_on_website == website_id)
        return (await self.db.execute(query)).scalar()

    async def update_title(self, db_title: Title, title: ParsedTitle) -> Title:
        db_title.name = title.name
        db_title.image_url = title.image_url
        db_title.description = title.description
        db_title.page_fetched = True
        return await self.update(db_title)
    
    async def get_title_by_id(self, title_id: str) -> Title:
        query = select(Title).where(Title.id == title_id)
        return (await self.db.execute(query)).scalar()