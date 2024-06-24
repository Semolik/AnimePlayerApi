import re
import aiohttp
from src.utils.parsers import Parser, ParserFunctions
from src.schemas.parsers import LinkParsedTitle, ParsedTitle, ParsedTitleShort, ParsedGenre
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
        url = WEBSITE_URL
        if page > 1:
            url += f'/page/{page}/'
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            return get_titles_from_page(soup)


async def get_title_related(full_title: str, title_id: int) -> list[LinkParsedTitle]:
    print(full_title)
    async with aiohttp.ClientSession() as session:
        async with session.post(
                f'{WEBSITE_URL}/index.php?do=search',
                data={
                    'do': 'search', 'subaction': 'search',
                    'search_start': 0,
                    'full_search': 1,
                    'result_from': 1,
                    'story': full_title,
                    'all_word_seach': 1,
                    'titleonly': 0,
                    'searchuser': '',
                    'replyless': 0,
                    'replylimit': 0,
                    'searchdate': 0,
                    'beforeafter': 'after',
                    'sortby': 'date',
                    'resorder': 'desc',
                    'showposts': 0,
                    'catlist': [0],
                }
        ) as data:
            html = await data.text()
            soup = BeautifulSoup(html, 'html.parser')
            short_stories = soup.select('div.shortstory')
            for story in short_stories:
                a = story.select_one('div.shortstoryHead > h2 > a')
                if get_id_from_url(a['href']) == str(title_id):
                    return [
                        LinkParsedTitle(
                            id_on_website=get_id_from_url(a['href']),
                            name=get_original_title(a.text),
                        )
                        for a in story.select('div.shortstoryContent > div.text_spoiler > ol > li > a')
                    ]
            return []


async def get_title(title_id: str) -> ParsedTitle:
    if not title_id.isdigit():
        raise HTTPException(
            status_code=404, detail="Title ID for animevost must be a number.")
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{API_URL}/info', data={'id': int(title_id)}) as data:
            json = await data.json()
            data = json['data'][0]
            year = data['year']
            series = series_from_title(data['title'])
            match = re.match(r'^[^\[]+', data['title'])
            related_titles = await get_title_related(match.group(), title_id) if match else []
            return ParsedTitle(
                id_on_website=title_id,
                name=get_original_title(data['title']),
                image_url=data['urlImagePreview'],
                additional_info=series,
                description=data['description'],
                series=series,
                related_titles=related_titles,
                year=year
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


def get_titles_from_page(soup: BeautifulSoup) -> list[ParsedTitleShort]:
    titles = soup.find_all('div', class_='shortstory')
    result = []
    for title in titles:
        a = title.select_one('div.shortstoryHead > h2 > a')
        name = a.text
        related_titles = []
        text_spoiler = title.select_one('div.text_spoiler > ol > li > a')
        if text_spoiler:
            related_titles = [
                LinkParsedTitle(
                    id_on_website=get_id_from_url(a['href']),
                    name=get_original_title(a.text),
                    additional_info=a.next_sibling,
                )
                for a in text_spoiler.select('a')
            ]
        result.append(ParsedTitleShort(
            related_titles=related_titles,
            id_on_website=get_id_from_url(a['href']),
            name=get_original_title(name),
            additional_info=series_from_title(name),
            image_url=WEBSITE_URL+title.select_one('img')['src']
        ))
    return result[::-1]


async def get_genre(genre_website_id: str, page: int) -> list[ParsedTitleShort]:
    async with aiohttp.ClientSession() as session:
        url = f'{WEBSITE_URL}/zhanr/{genre_website_id}'
        if page > 1:
            url += f'/page/{page}/'
        async with session.post(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            return get_titles_from_page(soup)

functions = ParserFunctions(
    get_titles=get_titles, get_title=get_title, get_genres=get_genres, get_genre=get_genre)

parser = Parser(
    name="Animevost",
    id="animevost",
    functions=functions,
    titles_cache_period=12,
    genres_cache_period=24 * 7
)
