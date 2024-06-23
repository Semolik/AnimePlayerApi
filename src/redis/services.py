import json
from uuid import UUID
from aioredis import Redis

class ParserInfoService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
    
    async def expire_status(self, parser_id: str) -> bool:
        return not await self._redis.get(f"{parser_id}:expire")
    
    async def update_expire_status(self, parser_id: str, hours: int):
        await self._redis.set(f"{parser_id}:expire", 1, ex=hours*3600)
    
    async def get_titles(self, parser_id: str, page: int):
        data = await self._redis.get(f"{parser_id}:titles:{page}")
        if data:
            return json.loads(data)
    
    async def set_titles(self, parser_id: str, page: int, titles: dict):
        return await self._redis.set(f"{parser_id}:titles:{page}", json.dumps(titles))
    
    async def get_title(self, parser_id: str, title_id: UUID):
        data = await self._redis.get(f"{parser_id}:title:{title_id}")
        if data:
            return json.loads(data)
        
    async def set_title(self, parser_id: str, title_id: UUID, title: dict):
        return await self._redis.set(f"{parser_id}:title:{title_id}", json.dumps(title))

    async def delete_parser_data(self, parser_id: str):
        keys = await self._redis.keys(f"{parser_id}:*")
        if keys:
            await self._redis.delete(*keys)