import re
import aiohttp
from src.models.parsers import Episode
from src.utils.parsers import Parser, ParserFunctions
from src.schemas.parsers import LinkParsedTitle, ParsedEpisode, ParsedLink, ParsedTitle, ParsedTitleShort, ParsedGenre, ParsedTitlesPage, Episode as EpisodeSchema
from fastapi import HTTPException
from bs4 import BeautifulSoup
from src.redis.services import CacheService
from src.db.session import AsyncSession
from typing import List


API_URL = "https://api.animetop.info/v1"
WEBSITE_URL = "https://v5.vost.pw"

kinds = {
    "ТВ": "tv",
    "ТВ-спэшл": "tv_special",
    "OVA": "ova",
    "ONA": "ona",
    "Полнометражный фильм": "movie",
    "Короткометражный фильм": "movie",
}


def series_from_title(name):
    first = name.split(" /")
    if len(first) == 1:
        return None
    second = first[1].split(" [")
    return second[1][:-1]


def get_original_title(name):
    return name.split(" /")[0]


def get_en_title(name):
    first = name.split(" /")
    if len(first) == 1:
        return None
    second = first[1].split(" [")
    en_name = second[0].strip()
    if en_name.endswith('.'):
        en_name = en_name[:-1]
    return en_name


def get_pages_count(soup: BeautifulSoup) -> int:
    dle_content = soup.select_one('#dle-content')
    if not dle_content:
        raise HTTPException(
            status_code=404, detail="Page not found on animevost.")
    pagination = dle_content.select('div.block_2 > table > tr > td > a')
    return int(pagination[-1].text) if pagination else 1


async def get_titles(page: int) -> ParsedTitlesPage:
    async with aiohttp.ClientSession() as session:
        url = WEBSITE_URL
        if page > 1:
            url += f'/page/{page}/'
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            titles = get_titles_from_page(soup)
            if len(titles) == 0:
                raise HTTPException(
                    status_code=404, detail="No titles found on page.")
            pages = get_pages_count(soup)
            return ParsedTitlesPage(titles=titles, total_pages=pages)


async def get_title_page(full_title: str, title_id: int):
    try:
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
                    if get_id_from_url(story.select_one('div.shortstoryHead > h2 > a')['href']) == str(title_id):
                        return story
                return None
    except Exception as e:
        print("Error while getting related titles from animevost:", e)
        return None


async def get_title_related(story: BeautifulSoup) -> List[LinkParsedTitle]:

    return [
        LinkParsedTitle(
            id_on_website=get_id_from_url(a['href']),
            name=get_original_title(a.text),
            en_name=get_en_title(a.text),
        )
        for a in story.select('div.shortstoryContent > div.text_spoiler > ol > li > a')
    ]


async def get_title(title_id: str) -> ParsedTitle:
    if not title_id.isdigit():
        raise HTTPException(
            status_code=404, detail="Title ID for animevost must be a number.")
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{API_URL}/info', data={'id': int(title_id)}) as data:
            json = await data.json()
            data = json['data'][0]
            series = series_from_title(data['title'])
            match = re.match(r'^[^\[]+', data['title'])
            title_page = await get_title_page(match.group(), title_id) if match else None
            related_titles = await get_title_related(title_page) if title_page else []
            duration = None
            if title_page:
                info_tags = title_page.select(
                    'div.shortstoryContent > table > tr > td > p')
                for tag in info_tags:
                    strong = tag.select_one('strong')
                    if not strong:
                        continue
                    if "Количество серий: " == strong.text:
                        duration = re.search(r'\(([^)]+)', tag.text).group(1)
                        break
            async with session.post(f'{API_URL}/playlist', data={'id': int(title_id)}) as episodes_data:
                episodes_json = await episodes_data.json()

                def prepare_parse_episode(episode):
                    number = 0
                    search_result = re.search(r'\d+', episode['name'])
                    if search_result:
                        number = int(search_result.group())
                    return ParsedEpisode(
                        name=episode['name'],
                        number=number,
                        preview=episode['preview'],
                        links=[
                            ParsedLink(
                                name='HD',
                                link=episode['hd'],
                                quality=720
                            ),
                            ParsedLink(
                                name='SD',
                                link=episode['std'],
                                quality=480
                            ),
                        ]
                    )
                episodes_list = [
                    prepare_parse_episode(episode)
                    for episode in episodes_json
                ]
            return ParsedTitle(
                id_on_website=title_id,
                name=get_original_title(data['title']),
                en_name=get_en_title(data['title']),
                image_url=data['urlImagePreview'],
                additional_info=series,
                description=data['description'].replace('<br>', ''),
                series_info=series,
                episodes_list=episodes_list,
                related_titles=related_titles,
                year=data['year'],
                genres_names=data['genre'].split(', '),
                kind=kinds.get(data['type']),
                duration=duration
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
        try:
            result.append(ParsedTitleShort(
                related_titles=related_titles,
                id_on_website=get_id_from_url(a['href']),
                name=get_original_title(name),
                en_name=get_en_title(name),
                additional_info=series_from_title(name),
                image_url=WEBSITE_URL+title.select_one('img')['src']
            ))
        except Exception as e:
            print(f"Error while parsing title {name} on animevost: {e}")

    return result


async def get_genre(genre_website_id: str, page: int) -> ParsedTitlesPage:
    async with aiohttp.ClientSession() as session:
        url = f'{WEBSITE_URL}/zhanr/{genre_website_id}'
        if page > 1:
            url += f'/page/{page}/'
        async with session.post(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            titles = get_titles_from_page(soup)
            if len(titles) == 0:
                return ParsedTitlesPage(titles=[], total_pages=0)
            pages = get_pages_count(soup)
            return ParsedTitlesPage(titles=titles, total_pages=pages)

functions = ParserFunctions(
    get_titles=get_titles, get_title=get_title, get_genres=get_genres, get_genre=get_genre)


class AnimevostParser(Parser):

    async def prepare_episode(self, db_episode: Episode, parsed_episode: ParsedEpisode, progress: int, seconds: int, db: AsyncSession, service: CacheService) -> EpisodeSchema:
        return EpisodeSchema(
            id=db_episode.id,
            name=db_episode.name,
            links=parsed_episode.links,
            number=db_episode.number,
            image_url=parsed_episode.preview,
            progress=progress,
            seconds=seconds,
            duration=db_episode.duration,
        )


parser = AnimevostParser(
    name="Animevost",
    id="animevost",
    functions=functions,
    main_pages_count=2,
    order=1
)
