import aiohttp
from src.utils.parsers import Parser, ParserFunctions
from src.schemas.parsers import ParsedTitle, ParsedTitleShort, ParsedGenre
from fastapi import HTTPException
from bs4 import BeautifulSoup


API_URL = "https://api.animetop.info/v1"
WEBSITE_URL = "https://v2.vost.pw"

def series_from_title(name):
    first = name.split(" /")
    second = first[1].split(" [")
    return second[1][:-1]

def get_original_title(name):
    return name.split(" /")[0]

async def get_titles(page: int) -> list[ParsedTitleShort]:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{API_URL}/last', params={'page': page, 'quantity': 20}) as data:
            json = await data.json()
            return [
                ParsedTitleShort(
                    id_on_website=str(title['id']),
                    name=get_original_title(title['title']),
                    image_url=title['urlImagePreview'],
                    additional_info=series_from_title(title['title'])
                )
                for title in json['data']
            ]

async def get_title(title_id: str) -> ParsedTitle:
    if not title_id.isdigit():
        raise HTTPException(status_code=404, detail="Title ID for animevost must be a number.")
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{API_URL}/info', data={'id': int(title_id)}) as data:
            json = await data.json()
            data = json['data'][0]
            series = series_from_title(data['title'])
            return ParsedTitle(
                id_on_website=title_id,
                name=get_original_title(data['title']),
                image_url=data['urlImagePreview'],
                additional_info=series,
                description=data['description'],
                series=series
            )

async def get_genres() -> list[ParsedGenre]:
    async with aiohttp.ClientSession() as session:
        async with session.get(WEBSITE_URL) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            menus = soup.select('ul#topnav > li')
            genres_links = menus[1].select('div > span > a')
            return [
                ParsedGenre(
                    name=genre.text,
                    id_on_website=genre['href'].split('/')[-2]
                )
                for genre in genres_links
            ]
        
def get_id_from_url(url: str) -> str:
    return url.split('/')[-1].split('-')[0]
        
async def get_genre(genre_website_id: str, page: int) -> list[ParsedTitleShort]:
    async with aiohttp.ClientSession() as session:
        url = f'{WEBSITE_URL}/zhanr/{genre_website_id}'
        if page > 1:
            url += f'/page/{page}/'
        async with session.post(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            titles = soup.find_all('div', class_='shortstory')
            result = []
            for title in titles:
                a = title.select_one('div.shortstoryHead > h2 > a')
                name = a.text
                result.append(ParsedTitleShort(
                    id_on_website=get_id_from_url(a['href']),
                    name=get_original_title(name),
                    additional_info=series_from_title(name),
                    image_url=WEBSITE_URL+title.select_one('img')['src']
                ))
            return result

functions = ParserFunctions(get_titles=get_titles, get_title=get_title, get_genres=get_genres, get_genre=get_genre)

parser = Parser(
    name="Animevost",
    id="animevost",
    functions=functions,
    titles_cache_period=12,
    genres_cache_period=24 * 7
)