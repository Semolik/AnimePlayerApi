from typing import Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class BaseCRUD:
    def __init__(self, db) -> None:
        self.db: AsyncSession = db

    async def get(self, id: Any, model):
        return await self.db.get(model, id)

    async def paginate(self, model, page: int = 1, per_page: int = 10, query_func=None, options=None):
        end = page * per_page
        start = end - per_page
        query = select(model)
        if query_func:
            query = query_func(query)
        query = query.slice(start, end)
        if options:
            query = query.options(*options)
        query = await self.db.execute(query)
        return query.scalars().all()

    async def page_count(self, model, per_page: int = 10):
        query = await self.db.execute(select(model))
        count = query.scalars().count()
        return count // per_page + 1

    async def update(self, model):
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def create(self,  model):
        self.db.add(model)
        await self.db.commit()
        return model

    async def delete(self, model):
        await self.db.delete(model)
        await self.db.commit()
