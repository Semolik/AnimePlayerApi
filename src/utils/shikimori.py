from datetime import datetime, timedelta
import json
from fastapi import BackgroundTasks
from src.schemas.parsers import ParsedTitle, ShikimoriTitle
from src.redis.services import CacheService
import aiohttp
API_URL = "https://shikimori.one/api/graphql"
anime_schema = """
{
    id
    malId
    name
    russian
    licenseNameRu
    english
    synonyms
    kind
    rating
    score
    status
    episodes
    episodesAired
    duration
    airedOn { year month day date }
    url
    season

    poster { id originalUrl mainUrl }

    genres { id name russian kind }
    characterRoles {
      id
      rolesRu
      rolesEn
      character { id name poster { id } }
    }
    screenshots { id originalUrl x166Url x332Url }
    description
  }
}
"""


class Shikimori:
    def __init__(self, service: CacheService) -> None:
        self.service = service

    async def get_title(self, title: ParsedTitle) -> ShikimoriTitle:
        async with aiohttp.ClientSession() as session:
            name = json.dumps(title.en_name or title.name)
            name = name[1:-1]
            query = "{" + f'animes(search: "{name}", limit: 1' + \
                (f', kind: "{title.kind}"' if title.kind else '') + \
                ')' + anime_schema + "}"
            async with session.post(API_URL, json={
                "query": query
            }) as response:
                data = await response.json()
                if not data.get('data'):
                    return
                title_info = data['data']['animes']
                if len(title_info) > 0:
                    return await self.service.set_shikimori_title(title_info[0]['id'], title_info[0])

    async def update_shikimori_title(self, title_id: int):
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json={
                "query": "{" + f'animes(ids: "{title_id}")' + anime_schema + "}"
            }) as response:
                data = await response.json()
                title_json = data['data']['animes'][0]
        title = await self.service.set_shikimori_title(title_id, title_json)
        return title

    async def get_shikimori_title(self, title_id: int, background_tasks: BackgroundTasks) -> ShikimoriTitle:
        cached = await self.service.get_shikimori_title(title_id)
        if not cached:
            title = await self.update_shikimori_title(title_id)
        else:
            title = cached
            if title.last_fetch < datetime.now() - timedelta(days=7):
                background_tasks.add_task(
                    self.update_shikimori_title, title_id)
        return title
