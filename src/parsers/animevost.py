import aiohttp
from src.utils.parsers import Parser, ParserFunctions
from src.schemas.parsers import ParsedTitle, ParsedTitleShort
from fastapi import HTTPException
API_URL = "https://api.animetop.info/v1"

def series_from_title(name):
    first = name.split(" /")
    second = first[1].split(" [")
    return second[1][:-1]


async def get_titles(page: int) -> list[ParsedTitleShort]:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/last', params={'page': page, 'quantity': 20}) as data:
            json = await data.json()
            return [
                ParsedTitleShort(
                    id_on_website=str(title['id']),
                    name=title['title'].split(' /')[0],
                    image_url=title['urlImagePreview'],
                    additional_info=series_from_title(title['title'])
                )
                for title in json['data']
            ]

async def get_title(title_id: str):
    print(title_id)
    if not title_id.isdigit():
        raise HTTPException(status_code=404, detail="Title ID for animevost must be a number.")
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{API_URL}/info', data={'id': int(title_id)}) as data:
            json = await data.json()
            data = json['data'][0]
            series = series_from_title(data['title'])
            return ParsedTitle(
                id_on_website=title_id,
                name=data['title'],
                image_url=data['urlImagePreview'],
                additional_info=series,
                description=data['description'],
                series=series
            )
    

functions = ParserFunctions(get_titles=get_titles, get_title=get_title)

parser = Parser(
    name="Animevost",
    id="animevost",
    functions=functions,
    cache_period=12,
)