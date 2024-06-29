import aiohttp
from src.schemas.parsers import Genre, ParsedGenre, ParsedTitle, ParsedTitleShort
from src.redis.services import CacheService
from src.utils.parsers import Parser, ParserFunctions
from fastapi import BackgroundTasks, HTTPException
from src.db.session import AsyncSession
from bs4 import BeautifulSoup
from src.crud.genres_crud import GenresCrud
from typing import List
WEBSITE_URL = "https://anidub.life"
LINK_SPLITTER = "~"

kinds = {
    "anime_tv": "tv",
    "anime_ona": "ona",
    "anime_ova": "ova",
    "anime_movie": "movie",
}


async def get_titles(page: int) -> list[ParsedTitleShort]:
    async with aiohttp.ClientSession() as session:
        url = WEBSITE_URL
        if page > 1:
            url += f'/page/{page}/'
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            return get_titles_from_page(soup)


def get_original_title(name: str) -> str:
    return name.split(" /")[0]


def get_en_title(name: str) -> str:
    first = name.split(" /")
    if len(first) == 1:
        return None
    second = first[1].split(" [")
    en_name = second[0].strip()
    if en_name.endswith('.'):
        en_name = en_name[:-1]
    return en_name


def series_from_title(name: str) -> str:
    first = name.split(" /")
    if len(first) == 1:
        return None
    second = first[1].split(" [")
    if len(second) == 1:
        return None
    return second[1][:-1]


def get_title_data(th_item: BeautifulSoup) -> ParsedTitleShort:
    th_in = th_item.select_one('.th-in')
    poster = th_in.select(
        '.th-img > img')[0].get('src').replace('thumbs/', '')
    poster = (poster if 'http' in poster else WEBSITE_URL+poster)
    id_on_website = '-'.join(
        th_in.get('href').split('/')[4].split('.')[0].split('-')[:-3])
    th_title = th_in.select_one('.th-title')
    name = get_original_title(th_title.text)
    en_name = get_en_title(th_title.text)
    series = series_from_title(th_title.text)
    return ParsedTitleShort(
        id_on_website=id_on_website,
        name=name,
        image_url=poster,
        en_name=en_name,
        additional_info=series,
        poster=poster
    )


def get_titles_from_page(soup: BeautifulSoup) -> list[ParsedTitleShort]:
    data = soup.select_one('#dle-content')
    if not data:
        raise HTTPException(
            status_code=500, detail="Can't get titles from page")
    parsed_titles = []
    titles = data.select('.th-item')
    for title in titles:
        parsed_titles.append(get_title_data(title))
    return parsed_titles


async def get_title(title_id: str) -> ParsedTitle:
    URL = f'{WEBSITE_URL}/_/{title_id}.html'
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            data = soup.select_one('.wrap > .wrap-main')
            if not data:
                raise HTTPException(
                    status_code=500, detail="Can't get title from page")
            fright = data.select_one('.fright')
            title_block = fright.select_one('h1')
            title_name = title_block.text
            name = get_original_title(title_name)
            en_name = get_en_title(title_name)
            series = series_from_title(title_name)
            fleft = data.select_one('.fleft')
            poster = fleft.select_one('.fposter > img').get('src')
            poster = (poster if 'http' in poster else WEBSITE_URL+poster)
            description = fleft.select_one('.fdesc')
            description = description.text if description else None
            flist = fright.select('.flist > li')

            links = fright.select('.fmeta > span > a')
            year = None
            for link in links:
                href = link.get('href')
                if not href:
                    continue
                if 'year' in href.split('/'):
                    year = link.text
                    break
            kind = None
            if links:
                kind_link = links[-1]
                if kind_link:
                    kind_name = kind_link.get('href').split('/')[-1]
                    kind = kinds.get(kind_name)
            genres_names = []
            if flist:
                for flist_item in flist:
                    block_name = flist_item.select_one('span')
                    if block_name and block_name.text == 'Жанр:':
                        genres_names = [genre.text
                                        for genre in flist_item.select('a')]
                        break
            recommended_titles = []
            recommendations = data.select(
                '.sect > .sect-content > .th-item')

            if recommendations:
                for recommendation in recommendations:
                    recommended_titles.append(get_title_data(recommendation))
            return ParsedTitle(
                id_on_website=title_id,
                name=name,
                en_name=en_name,
                series=series,
                image_url=poster,
                year=year,
                description=description,
                genres_names=genres_names,
                recommended_titles=recommended_titles,
                kind=kind
            )


async def get_genre(genre_website_id: str, page: int) -> list[ParsedTitleShort]:
    async with aiohttp.ClientSession() as session:
        url = f'{WEBSITE_URL}/xfsearch/genre/{genre_website_id}/'
        if page > 1:
            url += f'page/{page}/'
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            return get_titles_from_page(soup)

functions = ParserFunctions(
    get_titles=get_titles, get_title=get_title, get_genres=None, get_genre=get_genre)


class AnidubParser(Parser):
    async def get_genres(self, background_tasks: BackgroundTasks, db: AsyncSession) -> List[Genre]:
        genres = await GenresCrud(db).get_genres(parser_id=self.parser_id)
        return genres

    async def _prepare_genres_names(self, genres_names: List[str], db: AsyncSession, background_tasks: BackgroundTasks) -> List[Genre]:
        db_genres = []
        for genre_name in genres_names:
            db_genre = await GenresCrud(db).get_genre_by_website_id(website_id=genre_name)
            if not db_genre:
                db_genre = await GenresCrud(db).create_genre(genre=ParsedGenre(
                    name=genre_name, id_on_website=genre_name
                ), parser_id=self.parser_id)
            db_genres.append(db_genre)
        return db_genres


parser = AnidubParser(
    name="Anidub",
    id="anidub",
    functions=functions


)
