import aiohttp
from src.utils.parsers import Parser, ParserFunctions
from src.schemas.parsers import ParsedTitleShortInt

API_URL = "https://api.animetop.info/v1/"

def series_from_title(name):
    first = name.split(" /")
    second = first[1].split(" [")
    return second[1][:-1]


async def get_titles(page: int) -> list[ParsedTitleShortInt]:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/last', params={'page': page, 'quantity': 20}) as data:
            json = await data.json()
            return [
                ParsedTitleShortInt(
                    id_on_website=title['id'],
                    name=title['title'].split(' /')[0],
                    image_url=title['urlImagePreview'],
                    additional_info=series_from_title(title['title'])
                )
                for title in json['data']
            ]
functions = ParserFunctions(get_titles=get_titles)

parser = Parser(
    name="Animevost",
    id="animevost",
    functions=functions,
    cache_period=12,
    title_id_type=int
)