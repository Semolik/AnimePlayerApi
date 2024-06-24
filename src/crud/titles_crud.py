from uuid import UUID
from sqlalchemy import select
from src.crud.base import BaseCRUD
from src.models.parsers import Title, RelatedLink, RelatedTitle
from src.schemas.parsers import ParsedTitleShort, ParsedTitle


class TitlesCrud(BaseCRUD):

    async def get_titles_by_website_ids(self, website_ids: list[str]) -> list[Title]:
        query = select(Title).where(Title.id_on_website.in_(website_ids))
        return (await self.db.execute(query)).scalars().all()

    async def get_related_titles_by_title_id(self, title_id: UUID) -> list[RelatedTitle]:
        related_link = await self.get_related_link_by_title_id(title_id)
        if not related_link:
            return []
        query = select(Title).join(RelatedTitle, Title.id == RelatedTitle.title_id).where(
            RelatedTitle.link_id == related_link.id and RelatedTitle.title_id != title_id)
        return (await self.db.execute(query)).scalars().all()

    async def create_title(self, title: ParsedTitleShort, parser_id: str) -> Title:
        title = Title(
            id_on_website=title.id_on_website,
            parser_id=parser_id,
            name=title.name,
            page_fetched=False,
            image_url=title.image_url if hasattr(title, 'image_url') else None,
        )
        return await self.create(title)

    async def get_related_link_by_title_id(self, title_id: UUID) -> RelatedLink:
        query = select(RelatedLink).join(RelatedTitle, RelatedLink.id ==
                                         RelatedTitle.link_id).where(RelatedTitle.title_id == title_id)
        return (await self.db.execute(query)).scalar()

    async def get_related_title(self, title_id: UUID, link_id: UUID) -> RelatedTitle:
        query = select(RelatedTitle).where(RelatedTitle.title_id ==
                                           title_id, RelatedTitle.link_id == link_id)
        return (await self.db.execute(query)).scalar()

    async def create_related_link(self) -> RelatedLink:
        return await self.create(RelatedLink())

    async def create_related_title(self, title_id: UUID, link_id: UUID) -> RelatedTitle:
        related_title = RelatedTitle(title_id=title_id, link_id=link_id)
        return await self.create(related_title)

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

    async def update_title(self, db_title: Title, title: ParsedTitle | ParsedTitleShort) -> Title:
        db_title.name = title.name
        db_title.image_url = title.image_url
        db_title.page_fetched = True

        if isinstance(title, ParsedTitle):
            db_title.description = title.description

        return await self.update(db_title)

    async def get_title_by_id(self, title_id: UUID) -> Title:
        query = select(Title).where(Title.id == title_id)
        return (await self.db.execute(query)).scalar()
