from sqlalchemy import select
from src.crud.base import BaseCRUD
from src.models.parsers import Title
from src.schemas.parsers import ParsedTitleShortStr, ParsedTitleShortInt

class TitlesCrud(BaseCRUD):

    async def get_titles_by_website_ids(self, website_ids: list[str]) -> list[Title]:
        query = select(Title).where(Title.id_on_website.in_(website_ids))
        return (await self.db.execute(query)).scalars().all()
    
    async def create_title(self, title: ParsedTitleShortStr | ParsedTitleShortInt, parser_id: str) -> Title:
        title = Title(
            id_on_website=str(title.id_on_website),
            parser_id=parser_id,
            name=title.name,
            page_fetched=False,
            image_url=title.image_url,
        )
        return await self.create(title)
    