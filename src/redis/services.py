from datetime import datetime
import json
from uuid import UUID
from aioredis import Redis

from src.schemas.parsers import ParsedGenre, ParsedTitleShort, ParsedTitlesPage, ShikimoriTitle


class CacheService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def genres_expire_status(self, parser_id: str) -> bool:
        return not await self._redis.get(f"{parser_id}:genres:expire")

    async def update_genres_expire_status(self, parser_id: str, hours: int):
        await self._redis.set(f"{parser_id}:genres:expire", 1, ex=hours*3600)

    async def expire_status(self, parser_id: str) -> bool:
        return not await self._redis.get(f"{parser_id}:expire")

    async def update_expire_status(self, parser_id: str, hours: int):
        await self._redis.set(f"{parser_id}:expire", 1, ex=hours*3600)

    async def get_expires_in(self, parser_id: str) -> int:
        seconds = await self._redis.ttl(f"{parser_id}:expire")
        if seconds < 0:
            return 0
        return seconds

    async def get_genre_titles(self, parser_id: str, genre_id: UUID, page: int) -> ParsedTitlesPage:
        data = await self._redis.get(f"{parser_id}:titles:{genre_id}:{page}")
        if data:
            data = json.loads(data)
            return ParsedTitlesPage(titles=[ParsedTitleShort(**title) for title in data['titles']], total_pages=data['total_pages'])

    async def get_genres(self, parser_id: str):
        data = await self._redis.get(f"{parser_id}:genres")
        if data:
            return [ParsedGenre(**genre) for genre in json.loads(data)]

    async def set_genres(self, parser_id: str, genres: dict):
        return await self._redis.set(f"{parser_id}:genres", json.dumps(genres))

    async def set_genre_titles(self, parser_id: str, genre_id: UUID, page: int, titles_page: dict):
        return await self._redis.set(f"{parser_id}:titles:{genre_id}:{page}", json.dumps(titles_page))

    async def get_titles(self, parser_id: str, page: int) -> ParsedTitlesPage:
        data = await self._redis.get(f"{parser_id}:titles:{page}")
        if data:
            data = json.loads(data)
            return ParsedTitlesPage(titles=[ParsedTitleShort(**title) for title in data['titles']], total_pages=data['total_pages'])

    async def set_titles(self, parser_id: str, page: int, titles_page: dict):
        return await self._redis.set(f"{parser_id}:titles:{page}", json.dumps(titles_page))

    async def get_title(self, parser_id: str, title_id: UUID):
        data = await self._redis.get(f"{parser_id}:title:{title_id}")
        if data:
            return json.loads(data)

    async def set_title(self, parser_id: str, title_id: UUID, title: dict):
        return await self._redis.set(f"{parser_id}:title:{title_id}", json.dumps(title))

    async def delete_parser_data(self, parser_id: str):
        keys = await self._redis.keys(f"{parser_id}:titles:*")
        if keys:
            await self._redis.delete(*keys)

    async def get_shikimori_title(self, title_id: UUID):
        cached = await self._redis.get(f"shikimori:{title_id}")
        if cached:
            return ShikimoriTitle(**json.loads(cached))

    async def set_shikimori_title(self, title_id: UUID, title: dict):
        title_data = ShikimoriTitle(last_fetch=datetime.now(), data=title)
        obj = title_data.model_dump()
        obj['last_fetch'] = obj['last_fetch'].isoformat()
        await self._redis.set(f"shikimori:{title_id}", json.dumps(obj))
        return title_data

    async def set_shikimori_fail(self, title_id: UUID):
        await self._redis.set(f"shikimori:{title_id}:fail", 1, ex=60*5)

    async def shikimori_fail_status(self, title_id: UUID) -> bool:
        return bool(await self._redis.get(f"shikimori:{title_id}:fail"))

    async def get_link_by_hash(self, hash: str):
        return await self._redis.get(f"link:{hash}")

    async def set_link_content(self, hash: str, content: str):
        return await self._redis.set(f"link:{hash}:content", content)

    async def get_link_content(self, hash: str):
        return await self._redis.get(f"link:{hash}:content")

    async def set_link_by_hash(self, hash: str, link: str):
        return await self._redis.set(f"link:{hash}", link)

    async def get_popular_ongoings(self, page: int):
        data = await self._redis.get(f"popular_ongoings:{page}")
        if data:
            return json.loads(data)

    async def set_popular_ongoings(self, page: int, data: dict):
        return await self._redis.set(f"popular_ongoings:{page}", json.dumps(data), ex=60*60*24)
